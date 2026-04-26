// Domo API client (Phase 0~1)
// Reference: docs/02-design/design.md §3.1 — standard response format

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:3710/v1";

// ─── Token storage (Phase 1: localStorage; 2차에 httpOnly cookie 전환) ─────
const TOKEN_KEY = "domo_access_token";
const REFRESH_KEY = "domo_refresh_token";

// Global event name so that sidebars/headers can react to login/logout
// without needing a React context provider in the tree.
export const AUTH_CHANGED_EVENT = "domo-auth-changed";

function _dispatchAuthChanged() {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event(AUTH_CHANGED_EVENT));
}

export const tokenStore = {
  get(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(TOKEN_KEY);
  },
  getRefresh(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(REFRESH_KEY);
  },
  set(access: string, refresh: string) {
    if (typeof window === "undefined") return;
    localStorage.setItem(TOKEN_KEY, access);
    localStorage.setItem(REFRESH_KEY, refresh);
    _dispatchAuthChanged();
  },
  clear() {
    if (typeof window === "undefined") return;
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    _dispatchAuthChanged();
  },
};

// Single-flight refresh mutex — prevents parallel 401s from creating multiple refresh calls
let refreshInFlight: Promise<boolean> | null = null;

async function tryRefreshAccessToken(): Promise<boolean> {
  if (refreshInFlight) return refreshInFlight;
  const rt = tokenStore.getRefresh();
  if (!rt) return false;

  refreshInFlight = (async () => {
    try {
      const res = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: rt }),
      });
      const json = await res.json();
      if (!res.ok || "error" in json) {
        tokenStore.clear();
        return false;
      }
      tokenStore.set(json.data.access_token, json.data.refresh_token);
      return true;
    } catch {
      tokenStore.clear();
      return false;
    } finally {
      // Reset so next 401 can trigger a new refresh
      setTimeout(() => {
        refreshInFlight = null;
      }, 0);
    }
  })();

  return refreshInFlight;
}

export type ApiSuccess<T> = { data: T };
export type ApiError = {
  error: { code: string; message: string; details?: Record<string, unknown> };
};
export type ApiResponse<T> = ApiSuccess<T> | ApiError;

async function _fetchOnce(
  path: string,
  init?: RequestInit & { token?: string; auth?: boolean; _retry?: boolean; raw?: boolean }
): Promise<Response> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string>),
  };
  const token =
    init?.token ?? (init?.auth !== false ? tokenStore.get() : null);
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return fetch(`${API_BASE}${path}`, { ...init, headers });
}

export async function apiFetch<T>(
  path: string,
  init?: RequestInit & { token?: string; auth?: boolean; raw?: boolean; _retry?: boolean }
): Promise<T> {
  let res = await _fetchOnce(path, init);

  // Auto-refresh on 401 (one retry only, excludes refresh endpoint itself)
  const isAuthEndpoint = path.startsWith("/auth/refresh") || path.startsWith("/auth/sns/");
  if (
    res.status === 401 &&
    !init?._retry &&
    !isAuthEndpoint &&
    init?.auth !== false &&
    !init?.token &&
    tokenStore.getRefresh()
  ) {
    const ok = await tryRefreshAccessToken();
    if (ok) {
      res = await _fetchOnce(path, { ...init, _retry: true });
    }
  }

  const json = (await res.json()) as ApiResponse<T>;
  if (!res.ok || "error" in json) {
    const err =
      "error" in json ? json.error : { code: "UNKNOWN", message: res.statusText };
    throw new ApiClientError(err.code, err.message, err.details);
  }
  // raw: return the full envelope (e.g. when the response includes both `data` and `pagination`)
  if (init?.raw) return json as unknown as T;
  return (json as ApiSuccess<T>).data;
}

// ─── Auth helpers ────────────────────────────────────────────────────────
export type ApiUser = {
  id: string;
  email: string;
  role: "user" | "artist" | "admin";
  status: string;
  display_name: string;
  avatar_url: string | null;
  language: string;
  warning_count: number;
  // Admin-only 2FA enrollment status (undefined for non-admin)
  totp_enabled_at?: string | null;
  passkey_count?: number;
  second_factor_enrolled?: boolean;
};

export async function loginWithMockEmail(email: string): Promise<ApiUser> {
  const data = await apiFetch<{
    tokens: { access_token: string; refresh_token: string };
    user: ApiUser;
  }>("/auth/sns/google", {
    method: "POST",
    body: JSON.stringify({ id_token: `mock:${email}` }),
  });
  tokenStore.set(data.tokens.access_token, data.tokens.refresh_token);
  return data.user;
}

// ─── Admin credential auth (password + TOTP 2FA) ─────────────────────────
export type AdminLoginStep1Response =
  | {
      totp_required: true;
      challenge_token: string;
    }
  | {
      totp_required: false;
      totp_setup_required: boolean;
      tokens: { access_token: string; refresh_token: string };
      user: ApiUser;
    };

export async function adminLoginStep1(
  email: string,
  password: string
): Promise<AdminLoginStep1Response> {
  const data = await apiFetch<AdminLoginStep1Response>("/auth/admin/login", {
    method: "POST",
    auth: false,
    body: JSON.stringify({ email, password }),
  });
  // First-time admin (no TOTP yet) — tokens already issued
  if (data.totp_required === false) {
    tokenStore.set(data.tokens.access_token, data.tokens.refresh_token);
  }
  return data;
}

export type AdminVerifyResult = {
  user: ApiUser;
  auth_method: "totp" | "recovery_code";
  recovery_codes_remaining: number;
};

export async function adminLoginVerifyTotp(
  challenge_token: string,
  totp_code: string
): Promise<AdminVerifyResult> {
  return _adminVerify({ challenge_token, totp_code });
}

export async function adminLoginVerifyRecoveryCode(
  challenge_token: string,
  recovery_code: string
): Promise<AdminVerifyResult> {
  return _adminVerify({ challenge_token, recovery_code });
}

async function _adminVerify(body: Record<string, string>): Promise<AdminVerifyResult> {
  const data = await apiFetch<{
    tokens: { access_token: string; refresh_token: string };
    user: ApiUser;
    auth_method: "totp" | "recovery_code";
    recovery_codes_remaining: number;
  }>("/auth/admin/login/verify", {
    method: "POST",
    auth: false,
    body: JSON.stringify(body),
  });
  tokenStore.set(data.tokens.access_token, data.tokens.refresh_token);
  return {
    user: data.user,
    auth_method: data.auth_method,
    recovery_codes_remaining: data.recovery_codes_remaining,
  };
}

export type AdminTotpSetup = {
  secret: string;
  otpauth_uri: string;
  issuer: string;
};

export async function adminTotpSetup(): Promise<AdminTotpSetup> {
  return apiFetch<AdminTotpSetup>("/auth/admin/totp/setup", { method: "GET" });
}

export type AdminTotpEnableResult = {
  enabled: true;
  enabled_at: string;
  recovery_codes: string[];
  recovery_codes_warning: string;
};

export async function adminTotpEnable(
  totp_code: string
): Promise<AdminTotpEnableResult> {
  return apiFetch<AdminTotpEnableResult>("/auth/admin/totp/enable", {
    method: "POST",
    body: JSON.stringify({ totp_code }),
  });
}

export type RecoveryCodeStatus = {
  total: number;
  used: number;
  remaining: number;
  warning_low: boolean;
};

export async function adminRecoveryCodesStatus(): Promise<RecoveryCodeStatus> {
  return apiFetch("/auth/admin/recovery-codes/status");
}

export async function adminRecoveryCodesRegenerate(
  password: string
): Promise<{ recovery_codes: string[]; recovery_codes_warning: string }> {
  return apiFetch("/auth/admin/recovery-codes/regenerate", {
    method: "POST",
    body: JSON.stringify({ password }),
  });
}

// ─── Admin WebAuthn / Passkey ────────────────────────────────────────────
export type WebauthnCredentialView = {
  id: string;
  credential_id: string;
  nickname: string | null;
  transports: string | null;
  backed_up: boolean;
  created_at: string;
  last_used_at: string | null;
};

export async function webauthnListCredentials(): Promise<WebauthnCredentialView[]> {
  return apiFetch<WebauthnCredentialView[]>("/auth/admin/webauthn/credentials");
}

export async function webauthnRevokeCredential(id: string): Promise<{ ok: true }> {
  return apiFetch(`/auth/admin/webauthn/credentials/${id}`, { method: "DELETE" });
}

export async function webauthnRegisterBegin(
  nickname?: string
): Promise<{ challenge_token: string; options: string }> {
  return apiFetch("/auth/admin/webauthn/register/begin", {
    method: "POST",
    body: JSON.stringify({ nickname }),
  });
}

export async function webauthnRegisterFinish(
  challenge_token: string,
  credential: unknown,
  nickname?: string
): Promise<{ id: string; credential_id: string; nickname: string | null }> {
  return apiFetch("/auth/admin/webauthn/register/finish", {
    method: "POST",
    body: JSON.stringify({ challenge_token, credential, nickname }),
  });
}

export async function webauthnAuthenticateBegin(
  email: string
): Promise<{ challenge_token: string; options: string }> {
  return apiFetch("/auth/admin/webauthn/authenticate/begin", {
    method: "POST",
    auth: false,
    body: JSON.stringify({ email }),
  });
}

export async function webauthnAuthenticateFinish(
  challenge_token: string,
  assertion: unknown
): Promise<{ user: ApiUser; auth_method: "webauthn" }> {
  const data = await apiFetch<{
    tokens: { access_token: string; refresh_token: string };
    user: ApiUser;
    auth_method: "webauthn";
  }>("/auth/admin/webauthn/authenticate/finish", {
    method: "POST",
    auth: false,
    body: JSON.stringify({ challenge_token, assertion }),
  });
  tokenStore.set(data.tokens.access_token, data.tokens.refresh_token);
  return { user: data.user, auth_method: data.auth_method };
}

export async function adminTotpDisable(
  password: string
): Promise<{ enabled: false }> {
  return apiFetch("/auth/admin/totp/disable", {
    method: "POST",
    body: JSON.stringify({ password }),
  });
}

export async function fetchMe(): Promise<ApiUser> {
  return apiFetch<ApiUser>("/auth/me");
}

export async function logout(): Promise<void> {
  const rt = tokenStore.getRefresh();
  if (rt) {
    try {
      await apiFetch("/auth/logout", {
        method: "POST",
        body: JSON.stringify({ refresh_token: rt }),
      });
    } catch {
      // ignore — we clear client state anyway
    }
  }
  tokenStore.clear();
}

// ─── Admin helpers ───────────────────────────────────────────────────────
export type ArtistApplication = {
  id: string;
  user_id: string;
  portfolio_urls: string[] | null;
  school: string | null;
  intro_video_url: string | null;
  statement: string | null;
  status: string;
  review_note: string | null;
  reviewed_at: string | null;
  created_at: string;
};

export async function listApplications(status = "pending"): Promise<ArtistApplication[]> {
  return apiFetch<ArtistApplication[]>(
    `/admin/artists/applications?status=${status}`
  );
}

export async function approveApplication(id: string, note?: string) {
  return apiFetch<ArtistApplication>(`/admin/artists/applications/${id}/approve`, {
    method: "POST",
    body: JSON.stringify({ note: note ?? null }),
  });
}

export async function rejectApplication(id: string, note?: string) {
  return apiFetch<ArtistApplication>(`/admin/artists/applications/${id}/reject`, {
    method: "POST",
    body: JSON.stringify({ note: note ?? null }),
  });
}

// ─── Artist apply ────────────────────────────────────────────────────────
export type ApplyArtistInput = {
  school?: string;
  intro_video_url?: string;
  portfolio_urls?: string[];
  statement?: string;
};

export async function applyArtist(input: ApplyArtistInput) {
  return apiFetch<ArtistApplication>("/artists/apply", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function fetchMyApplications() {
  return apiFetch<ArtistApplication[]>("/artists/apply/me");
}

// ─── Posts / Feed / Comments ─────────────────────────────────────────────
export type PostAuthorView = {
  id: string;
  display_name: string;
  avatar_url: string | null;
  role: string;
};

export type MediaAssetView = {
  id: string;
  type: "image" | "video" | "external_embed";
  url: string;
  thumbnail_url: string | null;
  width: number | null;
  height: number | null;
  order_index: number;
};

export type ProductPostView = {
  is_auction: boolean;
  is_buy_now: boolean;
  buy_now_price: string | null;
  currency: string;
  dimensions: string | null;
  medium: string | null;
  year: number | null;
  is_sold: boolean;
};

export type PostView = {
  id: string;
  author: PostAuthorView;
  type: "general" | "product";
  title: string | null;
  content: string | null;
  genre: string | null;
  tags: string[] | null;
  language: string;
  like_count: number;
  comment_count: number;
  view_count: number;
  bluebird_count: number;
  status: string;
  digital_art_check: string;
  created_at: string;
  media: MediaAssetView[];
  product: ProductPostView | null;
};

export type CommentView = {
  id: string;
  post_id: string;
  author: PostAuthorView;
  content: string;
  status: string;
  created_at: string;
};

export async function fetchExplore(params?: {
  genre?: string;
  type?: string;
  sort?: "latest" | "popular";
  limit?: number;
}): Promise<PostView[]> {
  const qs = new URLSearchParams();
  if (params?.genre) qs.set("genre", params.genre);
  if (params?.type) qs.set("type", params.type);
  if (params?.sort) qs.set("sort", params.sort);
  qs.set("limit", String(params?.limit ?? 20));
  return apiFetch<PostView[]>(`/posts/explore?${qs.toString()}`, { auth: false });
}

export async function fetchHomeFeed(limit = 20): Promise<PostView[]> {
  return apiFetch<PostView[]>(`/posts/feed?limit=${limit}`);
}

export async function fetchFollowingFeed(limit = 20): Promise<PostView[]> {
  return apiFetch<PostView[]>(
    `/posts/feed?limit=${limit}&following_only=true`
  );
}

// ─── Search ─────────────────────────────────────────────────────

export type UserSearchResult = {
  id: string;
  display_name: string;
  avatar_url: string | null;
  bio: string | null;
  role: string;
  follower_count: number;
};

export async function searchUsers(
  q: string,
  opts?: { role?: string; limit?: number }
): Promise<UserSearchResult[]> {
  const qs = new URLSearchParams({ q });
  if (opts?.role) qs.set("role", opts.role);
  qs.set("limit", String(opts?.limit ?? 20));
  return apiFetch<UserSearchResult[]>(`/users/search?${qs}`, { auth: false });
}

export async function searchPosts(
  q: string,
  opts?: {
    type?: string;
    genre?: string;
    sort?: "latest" | "popular" | "ending_soon";
    limit?: number;
  }
): Promise<PostView[]> {
  const qs = new URLSearchParams({ q });
  if (opts?.type) qs.set("type", opts.type);
  if (opts?.genre) qs.set("genre", opts.genre);
  if (opts?.sort) qs.set("sort", opts.sort);
  qs.set("limit", String(opts?.limit ?? 20));
  return apiFetch<PostView[]>(`/posts/search?${qs}`, { auth: false });
}

export async function fetchPost(id: string): Promise<PostView> {
  return apiFetch<PostView>(`/posts/${id}`, { auth: false });
}

export async function fetchComments(postId: string): Promise<CommentView[]> {
  return apiFetch<CommentView[]>(`/posts/${postId}/comments`, { auth: false });
}

export async function createComment(postId: string, content: string) {
  return apiFetch<CommentView>(`/posts/${postId}/comments`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

export async function likePost(postId: string) {
  return apiFetch<{ ok: boolean; like_count?: number }>(
    `/posts/${postId}/like`,
    { method: "POST" }
  );
}

export async function unlikePost(postId: string) {
  return apiFetch<{ ok: boolean; like_count?: number }>(
    `/posts/${postId}/like`,
    { method: "DELETE" }
  );
}

// ─── Sponsorships (Phase 2) ──────────────────────────────────────────────
export type SponsorshipView = {
  id: string;
  sponsor_id: string | null;
  artist_id: string;
  post_id: string | null;
  bluebird_count: number;
  amount: string;
  currency: string;
  is_anonymous: boolean;
  visibility: "public" | "artist_only" | "private";
  message: string | null;
  status: string;
  created_at: string;
};

export type CreateSponsorshipResponse = {
  sponsorship: SponsorshipView;
  payment_intent: {
    id: string;
    client_secret: string;
    amount: string;
    currency: string;
    status: string;
  };
};

export type CreateSponsorshipInput = {
  artist_id: string;
  post_id?: string | null;
  bluebird_count: number;
  is_anonymous?: boolean;
  visibility?: "public" | "artist_only" | "private";
  message?: string;
};

export async function createSponsorship(input: CreateSponsorshipInput) {
  return apiFetch<CreateSponsorshipResponse>("/sponsorships", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function confirmSponsorship(id: string) {
  return apiFetch<SponsorshipView>(`/sponsorships/${id}/confirm`, {
    method: "POST",
  });
}

export async function fetchMySponsorships() {
  return apiFetch<SponsorshipView[]>("/sponsorships/mine");
}

// ─── Subscriptions (Phase 2) ─────────────────────────────────────────────
export type SubscriptionView = {
  id: string;
  sponsor_id: string;
  artist_id: string;
  monthly_bluebird: number;
  monthly_amount: string;
  currency: string;
  status: string;
  cancel_at_period_end: boolean;
  current_period_end: string | null;
  cancelled_at: string | null;
  created_at: string;
};

export async function createSubscription(input: {
  artist_id: string;
  monthly_bluebird: number;
}) {
  return apiFetch<SubscriptionView>("/subscriptions", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function cancelSubscription(id: string) {
  return apiFetch<SubscriptionView>(`/subscriptions/${id}`, {
    method: "DELETE",
  });
}

export async function fetchMySubscriptions() {
  return apiFetch<SubscriptionView[]>("/subscriptions/mine");
}

// ─── Auctions (Phase 2 Week 9) ───────────────────────────────────────────
export type AuctionView = {
  id: string;
  product_post_id: string;
  seller_id: string;
  start_price: string;
  min_increment: string;
  current_price: string;
  current_winner: string | null;
  currency: string;
  start_at: string;
  end_at: string;
  status: "scheduled" | "active" | "ended" | "cancelled" | "settled";
  bid_count: number;
  payment_deadline: string | null;
  created_at: string;
};

export type BidView = {
  id: string;
  auction_id: string;
  bidder_id: string;
  amount: string;
  status: "active" | "outbid" | "won" | "cancelled";
  created_at: string;
};

export async function fetchAuction(id: string): Promise<AuctionView> {
  return apiFetch<AuctionView>(`/auctions/${id}`, { auth: false });
}

export async function fetchAuctionBids(id: string): Promise<BidView[]> {
  return apiFetch<BidView[]>(`/auctions/${id}/bids`, { auth: false });
}

export async function fetchAuctions(params?: {
  status?: string;
  seller_id?: string;
  limit?: number;
}): Promise<AuctionView[]> {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
  if (params?.seller_id) qs.set("seller_id", params.seller_id);
  qs.set("limit", String(params?.limit ?? 20));
  return apiFetch<AuctionView[]>(`/auctions?${qs.toString()}`, { auth: false });
}

export async function placeBid(auctionId: string, amount: number) {
  return apiFetch<{ bid: BidView; auction: AuctionView }>(
    `/auctions/${auctionId}/bids`,
    {
      method: "POST",
      body: JSON.stringify({ amount }),
    }
  );
}

export async function createAuction(input: {
  product_post_id: string;
  start_price: number;
  min_increment: number;
  duration_hours: number;
}) {
  return apiFetch<AuctionView>("/auctions", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

// ─── Orders & Buy-now (Phase 2 Week 10) ──────────────────────────────────
export type OrderView = {
  id: string;
  buyer_id: string;
  seller_id: string;
  product_post_id: string;
  source: "auction" | "buy_now";
  auction_id: string | null;
  amount: string;
  currency: string;
  platform_fee: string;
  status: string;
  payment_intent_id: string | null;
  payment_due_at: string | null;
  paid_at: string | null;
  created_at: string;
};

export async function buyNow(productPostId: string) {
  return apiFetch<{
    order: OrderView;
    payment_intent: {
      id: string;
      client_secret: string;
      amount: string;
      currency: string;
      status: string;
    };
    cancelled_auctions: string[];
  }>(`/products/${productPostId}/buy-now`, { method: "POST" });
}

export async function payOrder(orderId: string) {
  return apiFetch<OrderView>(`/orders/${orderId}/pay`, { method: "POST" });
}

export async function cancelOrder(orderId: string) {
  return apiFetch<OrderView>(`/orders/${orderId}/cancel`, { method: "POST" });
}

export async function fetchMyOrders(role: "buyer" | "seller" = "buyer") {
  return apiFetch<OrderView[]>(`/orders/mine?role=${role}`);
}

// ─── Moderation (Phase 3 Week 11) ────────────────────────────────────────
export type ReportTargetType = "post" | "comment" | "user";

export type ReportView = {
  id: string;
  reporter_id: string;
  target_type: ReportTargetType;
  target_id: string;
  reason: string;
  description: string | null;
  status: string;
  handled_by: string | null;
  handled_at: string | null;
  created_at: string;
};

export type WarningView = {
  id: string;
  user_id: string;
  reason: string;
  report_id: string | null;
  issued_by: string | null;
  is_active: boolean;
  appealed: boolean;
  appeal_note: string | null;
  cancelled_at: string | null;
  created_at: string;
};

export async function createReport(input: {
  target_type: ReportTargetType;
  target_id: string;
  reason: string;
  description?: string;
}) {
  return apiFetch<ReportView>("/abuse-reports", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function fetchMyWarnings() {
  return apiFetch<WarningView[]>("/warnings/mine");
}

export async function appealWarning(id: string, note: string) {
  return apiFetch<WarningView>(`/warnings/${id}/appeal`, {
    method: "POST",
    body: JSON.stringify({ note }),
  });
}

// Admin
export async function adminListReports(status = "pending") {
  return apiFetch<ReportView[]>(`/admin/reports?status=${status}`);
}

export async function adminResolveReport(
  id: string,
  action: "issue_warning" | "dismiss",
  note?: string
) {
  return apiFetch<ReportView>(`/admin/reports/${id}/resolve`, {
    method: "POST",
    body: JSON.stringify({ action, note }),
  });
}

export async function adminListAppeals() {
  return apiFetch<WarningView[]>("/admin/appeals");
}

export async function adminCancelWarning(id: string) {
  return apiFetch<WarningView>(`/admin/warnings/${id}/cancel`, {
    method: "POST",
  });
}

export async function adminRejectAppeal(id: string) {
  return apiFetch<WarningView>(`/admin/warnings/${id}/reject-appeal`, {
    method: "POST",
  });
}

// ─── Admin Dashboard (Phase 3 Week 12) ───────────────────────────────────
export type DashboardStats = {
  window_days: number;
  users: {
    total: number;
    artists: number;
    suspended: number;
    new_in_window: number;
  };
  content: {
    total_posts: number;
    published: number;
    pending_review: number;
    new_in_window: number;
  };
  auctions: { active: number; ended: number };
  moderation: { pending_reports: number };
  sponsorship: { completed_total: number; active_subscriptions: number };
};

export type DashboardRevenue = {
  window_days: number;
  currency: string;
  gmv_total: string;
  platform_fee_total: string;
  by_source: {
    sponsorship: { amount: string; count: number };
    subscription_monthly_run_rate: { amount: string; active_count: number };
    auction: { amount: string; platform_fee: string };
    buy_now: { amount: string; platform_fee: string };
  };
};

export async function fetchDashboardStats(days = 30) {
  return apiFetch<DashboardStats>(`/admin/dashboard/stats?days=${days}`);
}

export async function fetchDashboardRevenue(days = 30) {
  return apiFetch<DashboardRevenue>(`/admin/dashboard/revenue?days=${days}`);
}

// System Settings
export type SystemSettingView = {
  key: string;
  value: Record<string, unknown>;
  updated_at: string | null;
};

export async function fetchSystemSettings() {
  return apiFetch<SystemSettingView[]>("/admin/settings");
}

export async function updateSystemSetting(
  key: string,
  value: Record<string, unknown>
) {
  return apiFetch<SystemSettingView>(`/admin/settings/${key}`, {
    method: "PATCH",
    body: JSON.stringify({ value }),
  });
}

// ─── Notifications (Phase 3 Week 13) ─────────────────────────────────────
export type NotificationView = {
  id: string;
  user_id: string;
  type: string;
  title: string | null;
  body: string | null;
  link: string | null;
  is_read: boolean;
  created_at: string | null;
};

export async function fetchNotifications(unreadOnly = false, limit = 30) {
  const qs = new URLSearchParams();
  if (unreadOnly) qs.set("unread_only", "true");
  qs.set("limit", String(limit));
  return apiFetch<NotificationView[]>(`/notifications?${qs.toString()}`);
}

export async function fetchUnreadCount() {
  return apiFetch<{ count: number }>("/notifications/unread-count");
}

export async function markNotificationRead(id: string) {
  return apiFetch<NotificationView>(`/notifications/${id}/read`, {
    method: "PATCH",
  });
}

export async function markAllNotificationsRead() {
  return apiFetch<{ updated: number }>("/notifications/read-all", {
    method: "POST",
  });
}

// ─── Received sponsorships (GAP-S1) ──────────────────────────────────────
export type ReceivedSponsorshipView = {
  id: string;
  sponsor_id: string | null;
  post_id: string | null;
  bluebird_count: number;
  amount: string;
  currency: string;
  is_anonymous: boolean;
  visibility: "public" | "artist_only" | "private";
  message: string | null;
  created_at: string;
};

export async function fetchReceivedSponsorships(userId: string, limit = 20) {
  return apiFetch<ReceivedSponsorshipView[]>(
    `/users/${userId}/sponsorships?limit=${limit}`,
    { auth: false }
  );
}

// ─── User profile ────────────────────────────────────────────────────────
export type UserProfileView = {
  id: string;
  display_name: string;
  avatar_url: string | null;
  bio: string | null;
  role: string;
  country_code: string | null;
  language: string;
  follower_count: number;
  following_count: number;
  artist_profile: {
    school: string | null;
    intro_video_url: string | null;
    portfolio_urls: string[] | null;
    statement: string | null;
    badge_level: string;
    verified_at: string | null;
  } | null;
};

export async function fetchUserProfile(userId: string) {
  return apiFetch<UserProfileView>(`/users/${userId}`, { auth: false });
}

// ─── GDPR / Legal (Phase 4 M3) ───────────────────────────────────────────
export type PolicyVersion = {
  version: string;
  effective_date: string;
};

export type LegalVersions = {
  privacy_policy: PolicyVersion;
  terms: PolicyVersion;
};

export async function fetchLegalVersions() {
  return apiFetch<LegalVersions>("/legal/versions", { auth: false });
}

export async function acceptPolicies(input: {
  privacy_policy_version: string;
  terms_version: string;
}) {
  return apiFetch<{
    privacy_policy_version: string;
    terms_version: string;
    accepted_at: string;
  }>("/me/accept-policies", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function exportMyData(): Promise<Blob> {
  const token = tokenStore.get();
  if (!token) throw new ApiClientError("UNAUTHORIZED", "Login required");
  const res = await fetch(`${API_BASE}/me/export`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const json = await res.json().catch(() => ({}));
    const err =
      "error" in json
        ? json.error
        : { code: "UNKNOWN", message: res.statusText };
    throw new ApiClientError(err.code, err.message, err.details);
  }
  return res.blob();
}

export async function requestAccountDeletion() {
  return apiFetch<{
    deleted_at: string;
    deletion_scheduled_for: string;
    grace_period_days: number;
  }>("/me/delete", {
    method: "POST",
    body: JSON.stringify({ confirm: "DELETE MY ACCOUNT" }),
  });
}

export async function cancelAccountDeletion() {
  return apiFetch<{ ok: boolean }>("/me/delete/cancel", {
    method: "POST",
  });
}

// ─── M5 Onboarding + Guardian ────────────────────────────────────────────
export type OnboardingResult = {
  is_minor: boolean;
  guardian_required: boolean;
  onboarded: boolean;
};

export async function completeOnboarding(input: {
  birth_year: number;
  country_code: string;
}) {
  return apiFetch<OnboardingResult>("/me/onboarding", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function requestGuardianConsent(input: {
  guardian_email: string;
  guardian_name?: string;
}) {
  return apiFetch<{
    id: string;
    guardian_email: string;
    expires_at: string;
    status: string;
  }>("/me/guardian/request", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export type GuardianConsentInfo = {
  id: string;
  minor: {
    display_name: string;
    email: string;
    birth_year: number;
    country_code: string;
  } | null;
  guardian_email: string;
  guardian_name: string | null;
  consented_at: string | null;
  withdrawn_at: string | null;
  expires_at: string;
};

export async function fetchGuardianConsent(token: string) {
  return apiFetch<GuardianConsentInfo>(`/guardian/consent/${token}`, {
    auth: false,
  });
}

export async function approveGuardianConsent(token: string) {
  return apiFetch<{ id: string; consented_at: string; status: string }>(
    `/guardian/consent/${token}/approve`,
    { method: "POST", auth: false }
  );
}

export async function withdrawGuardianConsent(token: string) {
  return apiFetch<{ id: string; withdrawn_at: string; status: string }>(
    `/guardian/consent/${token}/withdraw`,
    { method: "POST", auth: false }
  );
}

// ─── Media upload (Phase 3 Week 14) ──────────────────────────────────────
export type UploadedMedia = {
  type: "image" | "video" | "external_embed";
  url: string;
  thumbnail_url?: string | null;
  size_bytes?: number;
  external_source?: string | null;
  external_id?: string | null;
  is_making_video?: boolean;
};

export async function uploadMediaFile(
  file: File,
  isMakingVideo = false
): Promise<UploadedMedia> {
  const token = tokenStore.get();
  if (!token) throw new ApiClientError("UNAUTHORIZED", "Login required");

  const form = new FormData();
  form.append("file", file);
  form.append("is_making_video", String(isMakingVideo));

  const res = await fetch(`${API_BASE}/media/upload`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  const json = await res.json();
  if (!res.ok || "error" in json) {
    const err =
      "error" in json
        ? json.error
        : { code: "UNKNOWN", message: res.statusText };
    throw new ApiClientError(err.code, err.message, err.details);
  }
  return json.data as UploadedMedia;
}

export async function registerExternalMedia(url: string, isMakingVideo = false) {
  return apiFetch<UploadedMedia>("/media/external", {
    method: "POST",
    body: JSON.stringify({ url, is_making_video: isMakingVideo }),
  });
}

// ─── Post create ─────────────────────────────────────────────────────────
export type CreatePostMedia = {
  type: "image" | "video" | "external_embed";
  url: string;
  thumbnail_url?: string | null;
  width?: number;
  height?: number;
  duration_sec?: number;
  size_bytes?: number;
  external_source?: string | null;
  external_id?: string | null;
  is_making_video?: boolean;
};

// ─── oEmbed + Tags ──────────────────────────────────────────────────────

export type OEmbedData = {
  provider: string;
  title: string;
  thumbnail_url: string | null;
  author_name: string | null;
  url: string;
};

export async function fetchOEmbed(url: string): Promise<OEmbedData> {
  return apiFetch<OEmbedData>(
    `/media/oembed?url=${encodeURIComponent(url)}`,
    { auth: false }
  );
}

export async function fetchTagSuggestions(
  prefix: string,
  limit = 10
): Promise<string[]> {
  return apiFetch<string[]>(
    `/posts/tags/suggest?q=${encodeURIComponent(prefix)}&limit=${limit}`,
    { auth: false }
  );
}

// ─── Post create ─────────────────────────────────────────────────────────

export type CreatePostInput = {
  type: "general" | "product";
  title?: string;
  content?: string;
  genre?: string;
  tags?: string[];
  language?: string;
  scheduled_at?: string;
  location_name?: string;
  location_lat?: number;
  location_lng?: number;
  media: CreatePostMedia[];
  product?: {
    is_auction?: boolean;
    is_buy_now?: boolean;
    buy_now_price?: number;
    currency?: string;
    dimensions?: string;
    medium?: string;
    year?: number;
  };
};

export async function createPost(input: CreatePostInput) {
  return apiFetch<PostView>("/posts", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export class ApiClientError extends Error {
  constructor(
    public code: string,
    message: string,
    public details?: Record<string, unknown>
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}
