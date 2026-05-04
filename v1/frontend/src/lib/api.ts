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
  init?: RequestInit & { token?: string; auth?: boolean; _retry?: boolean }
): Promise<Response> {
  // When the body is FormData, omit Content-Type so the browser can set the
  // correct multipart boundary automatically (e.g. POST /v1/me/signature).
  const isFormData = init?.body instanceof FormData;
  const headers: Record<string, string> = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
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
  init?: RequestInit & { token?: string; auth?: boolean; _retry?: boolean }
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

  // 204 No Content — no body to parse (e.g. DELETE /v1/me/signature).
  if (res.status === 204) {
    return undefined as unknown as T;
  }

  const json = (await res.json()) as ApiResponse<T>;
  if (!res.ok || "error" in json) {
    const err =
      "error" in json ? json.error : { code: "UNKNOWN", message: res.statusText };
    throw new ApiClientError(err.code, err.message, err.details);
  }
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
  identity_verified_at: string | null;
  is_minor?: boolean;
  birth_year?: number | null;
  country_code?: string | null;
  onboarded_at?: string | null;
};

/**
 * Exchange a real Google ID token (from GIS popup credential response)
 * for Domo access/refresh tokens.
 */
export async function loginWithGoogleIdToken(id_token: string): Promise<ApiUser> {
  const data = await apiFetch<{
    tokens: { access_token: string; refresh_token: string };
    user: ApiUser;
  }>("/auth/sns/google", {
    method: "POST",
    body: JSON.stringify({ id_token }),
  });
  tokenStore.set(data.tokens.access_token, data.tokens.refresh_token);
  return data.user;
}

/**
 * @deprecated Dev-only fallback that forges a "mock:<email>" ID token.
 * Backend rejects this when GOOGLE_CLIENT_ID is configured. Kept only
 * for legacy callers (admin app uses the same pattern but is being
 * migrated to credential auth). Do not use in new code.
 */
export async function loginWithMockEmail(email: string): Promise<ApiUser> {
  return loginWithGoogleIdToken(`mock:${email}`);
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
  school: string | null;
  department: string | null;
  graduation_year: number | null;
  is_enrolled: boolean;
  genre_tags: string[] | null;
  portfolio_urls: string[] | null;
  intro_video_url: string | null;
  enrollment_proof_url: string | null;
  representative_works: RepresentativeWork[] | null;
  exhibitions: HistoryEntry[] | null;
  awards: HistoryEntry[] | null;
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
export type RepresentativeWork = {
  title: string;
  description?: string;
  image_url: string;
  dimensions?: string;
  medium?: string;
  year?: number;
};

export type HistoryEntry = {
  title: string;
  year?: number;
  description?: string;
};

export type ApplyArtistInput = {
  school: string;
  department: string;
  graduation_year: number;
  is_enrolled: boolean;
  genre_tags: string[];
  statement: string;
  enrollment_proof_url: string;
  representative_works: RepresentativeWork[];
  portfolio_urls?: string[];
  intro_video_url?: string;
  exhibitions?: HistoryEntry[];
  awards?: HistoryEntry[];
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

// ─── School search + edu email verification ─────────────────────────────

export type SchoolSearchResult = {
  id: string;
  name_ko: string;
  name_en: string;
  email_domain: string;
  country_code: string;
};

export async function searchSchools(q: string): Promise<SchoolSearchResult[]> {
  return apiFetch<SchoolSearchResult[]>(
    `/artists/schools/search?q=${encodeURIComponent(q)}`,
    { auth: false }
  );
}

export async function sendEduVerification(edu_email: string) {
  return apiFetch<{ message: string; school_name: string }>(
    "/artists/verify-edu/send",
    { method: "POST", body: JSON.stringify({ edu_email }) }
  );
}

export async function confirmEduVerification(edu_email: string, code: string) {
  return apiFetch<{ verified: boolean; edu_email: string }>(
    "/artists/verify-edu/confirm",
    { method: "POST", body: JSON.stringify({ edu_email, code }) }
  );
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
  is_making_video?: boolean;
  external_source?: string | null;
  external_id?: string | null;
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
  location_name?: string | null;
  location_lat?: number | null;
  location_lng?: number | null;
  scheduled_at?: string | null;
  recommendation_reason?: string | null;
  // publish-controls PDCA #8 — Backend _serialize_post() already includes these (Step 1.7)
  visibility?: Visibility;
  comments_enabled?: boolean;
  // artist-tier-release PDCA #10
  early_access_until?: string | null;
  early_access_tier?: EarlyAccessTier | null;
  is_tier_locked?: boolean;
  // auction-promotion-suite PDCA #11 — feed countdown (OQ-10=B, OQ-D-1=A)
  active_auction_end_at?: string | null;
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

// ─── Activity Tracking ──────────────────────────────────────────────────

export async function trackActivity(
  event_type: string,
  target_type: string,
  target_id: string,
  duration_sec?: number
) {
  try {
    await apiFetch("/activity/track", {
      method: "POST",
      body: JSON.stringify({ event_type, target_type, target_id, duration_sec }),
      auth: false,
    });
  } catch {
    // Non-blocking, ignore errors
  }
}

// ─── Currency ───────────────────────────────────────────────────────────

export async function getExchangeRate(target: string): Promise<{ rate: number }> {
  return apiFetch<{ rate: number }>(
    `/activity/exchange-rate?target=${target}`,
    { auth: false }
  );
}

// ─── Translation ────────────────────────────────────────────────────────

export type PostTranslation = {
  post_id: string;
  language: string;
  title: string | null;
  content: string | null;
  cached: boolean;
};

export async function fetchPostTranslation(
  postId: string,
  lang: string
): Promise<PostTranslation> {
  return apiFetch<PostTranslation>(
    `/posts/${postId}/translate?lang=${lang}`,
    { auth: false }
  );
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
  // auction-promotion-suite PDCA #11 — share card cache fields
  share_card_url?: string | null;
  share_card_generated_at?: string | null;
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

// auction-promotion-suite PDCA #11 — share card generation
export type AuctionShareCardResponse = {
  auction_id: string;
  share_card_url: string;
  generated_at: string;
  cached: boolean;
};

export async function generateAuctionShareCard(
  auctionId: string
): Promise<AuctionShareCardResponse> {
  return apiFetch<AuctionShareCardResponse>(
    `/auctions/${encodeURIComponent(auctionId)}/share-card`,
    { method: "POST" }
  );
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
  preferred_genres?: string[];
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

// editor-media-ux PDCA #4 — OQ-D-3 = B (XHR-based real upload progress).
export interface UploadProgressEvent {
  loaded: number;
  total: number;
  percent: number; // 0-100
}

/**
 * Upload a media file with real-time progress reporting via XMLHttpRequest.
 *
 * `fetch` cannot expose upload progress (the ReadableStream on the response
 * side is download-only), so this XHR-based function is the canonical entry
 * point. The legacy `uploadMediaFile` is kept as a thin no-callback wrapper
 * so existing call sites work unchanged.
 *
 * 401 token-refresh is intentionally not handled here — callers that need
 * refresh-on-401 should use the `apiFetch`-based path. In practice, upload
 * endpoints are called immediately after a user action where the access
 * token is fresh, so this simplification is acceptable for MVP.
 */
export async function uploadMediaFileWithProgress(
  file: File,
  isMakingVideo = false,
  onProgress?: (e: UploadProgressEvent) => void
): Promise<UploadedMedia> {
  const token = tokenStore.get();
  if (!token) throw new ApiClientError("UNAUTHORIZED", "Login required");

  return new Promise<UploadedMedia>((resolve, reject) => {
    const form = new FormData();
    form.append("file", file);
    form.append("is_making_video", String(isMakingVideo));

    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/media/upload`);
    xhr.setRequestHeader("Authorization", `Bearer ${token}`);

    if (onProgress) {
      xhr.upload.onprogress = (e) => {
        if (!e.lengthComputable) return;
        onProgress({
          loaded: e.loaded,
          total: e.total,
          percent: Math.round((e.loaded / e.total) * 100),
        });
      };
    }

    xhr.onload = () => {
      let json: unknown;
      try {
        json = JSON.parse(xhr.responseText);
      } catch {
        reject(new ApiClientError("UNKNOWN", "응답 파싱 실패"));
        return;
      }
      const obj = json as Record<string, unknown>;
      if (xhr.status >= 200 && xhr.status < 300 && !("error" in obj)) {
        resolve(obj.data as UploadedMedia);
        return;
      }
      const err =
        "error" in obj
          ? (obj.error as { code: string; message: string; details?: Record<string, unknown> })
          : { code: "UNKNOWN", message: xhr.statusText || `HTTP ${xhr.status}` };
      reject(new ApiClientError(err.code, err.message, err.details));
    };

    xhr.onerror = () =>
      reject(new ApiClientError("NETWORK_ERROR", "네트워크 오류"));
    xhr.ontimeout = () =>
      reject(new ApiClientError("UPLOAD_TIMEOUT", "업로드 시간 초과"));

    xhr.send(form);
  });
}

/**
 * Backwards-compatible wrapper around `uploadMediaFileWithProgress` —
 * existing callers that don't need progress callbacks keep their signature.
 */
export async function uploadMediaFile(
  file: File,
  isMakingVideo = false
): Promise<UploadedMedia> {
  return uploadMediaFileWithProgress(file, isMakingVideo);
}

/**
 * editor-media-ux PDCA #4 — Caption editing endpoint.
 *
 * Owner-only. Permitted after publication; blocked by the backend with
 * `AUCTION_ACTIVE_MEDIA_LOCKED` (409) when the host post has an active
 * auction (OQ-D-1 = A).
 */
export interface PatchMediaBody {
  caption?: string;
}

export async function patchMedia(
  mediaId: string,
  body: PatchMediaBody
): Promise<UploadedMedia> {
  return apiFetch<UploadedMedia>(`/media/${encodeURIComponent(mediaId)}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

// ─── editor-image-studio PDCA #6-image — CropMeta types (1:1 with backend) ─

/** Pixel-space crop rectangle. Coords are post-rotate source pixels. */
export interface CropRect { x: number; y: number; w: number; h: number; }

export interface MosaicRegion {
  x: number; y: number; w: number; h: number;
  strength: 10 | 20 | 40;
}

export interface WatermarkPosition { x: number; y: number; }

export interface WatermarkMeta {
  source: "text" | "signature";
  text?: string;
  position: WatermarkPosition;
  size?: number;
  opacity: number;
}

export interface CropMeta {
  version: 1;
  rotation: 0 | 90 | 180 | 270;
  crop?: CropRect;
  mosaic_regions: MosaicRegion[];
  watermark?: WatermarkMeta;
}

// Discriminated union for the request body's ops list

export interface RotateOp { type: "rotate"; degrees: 90 | 180 | 270; }

export interface CropOp {
  type: "crop"; x: number; y: number; w: number; h: number;
  ratio?: "1:1" | "4:3" | "16:9" | "free" | "original";
}

export interface MosaicOp { type: "mosaic"; regions: MosaicRegion[]; }

export interface WatermarkOp {
  type: "watermark";
  source: "text" | "signature";
  text?: string;
  position: WatermarkPosition;
  size?: number;
  opacity: number;
}

export type MediaTransformOp = RotateOp | CropOp | MosaicOp | WatermarkOp;

export interface MediaTransformResponse {
  id: string;
  url: string;
  thumbnail_url: string | null;
  thumb_small_url: string | null;
  thumb_medium_url: string | null;
  thumb_large_url: string | null;
  width: number | null;
  height: number | null;
  crop_meta: CropMeta;
}

/**
 * Apply non-destructive image edits.
 *
 * Owner-only. Permitted after publication; blocked by the backend with
 * `AUCTION_ACTIVE_MEDIA_LOCKED` (409) when the host post has an active
 * auction (OQ-8 = C, mirrors PATCH /media/{id} caption flow).
 */
export async function patchMediaTransform(
  mediaId: string,
  ops: MediaTransformOp[]
): Promise<MediaTransformResponse> {
  return apiFetch<MediaTransformResponse>(
    `/media/${encodeURIComponent(mediaId)}/transform`,
    { method: "POST", body: JSON.stringify({ ops }) }
  );
}

// ─── editor-image-studio — Signature endpoints (OQ-D-3 = B, OQ-D-B = C) ────

export interface SignatureResponse { signature_url: string | null; }

export async function getMySignature(): Promise<SignatureResponse> {
  return apiFetch<SignatureResponse>("/me/signature", { method: "GET" });
}

export async function uploadMySignature(file: File): Promise<SignatureResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return apiFetch<SignatureResponse>("/me/signature", {
    method: "POST",
    body: formData,
  });
}

export async function deleteMySignature(): Promise<void> {
  // 204 No Content — apiFetch handles empty body via the res.status === 204 guard.
  await apiFetch<void>("/me/signature", { method: "DELETE" });
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
  // editor-media-ux PDCA #4 — optional caption (max 280 chars, validated
  // server-side via Pydantic). undefined for legacy localStorage drafts.
  caption?: string;
  // Client-only identifier used by @dnd-kit's SortableContext. MUST be
  // stripped from the publish payload (POST /v1/posts) — backend Pydantic
  // schema does not declare this field.
  _clientId?: string;
  // editor-image-studio PDCA #6-image — non-destructive edit metadata.
  // undefined for legacy drafts and unedited media. Set by the backend
  // POST /v1/media/{id}/transform response and persisted in localStorage.
  crop_meta?: CropMeta;
  // editor-image-studio PDCA #6-image Step 8 — backend MediaAsset.id.
  // Populated from MediaAssetView.id when restoring from a published post or
  // from patchMediaTransform response. Undefined for freshly-uploaded draft
  // media (no MediaAsset row exists yet — upload creates a temp blob, the row
  // is created on publish). MUST be stripped from the publish payload.
  id?: string;
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

export async function createPost(input: CreatePostInput & { from_draft_id?: string }) {
  return apiFetch<PostView>("/posts", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

// ─── Draft ──────────────────────────────────────────────────────────
// editor-draft-autosave PDCA — server-side persistence for editor drafts.
// Backend: api/drafts.py (POST/GET/DELETE /v1/posts/drafts)

export type DraftMedia = CreatePostMedia & {
  id?: string;
  order_index?: number;
};

export type DraftProduct = {
  is_auction?: boolean;
  is_buy_now?: boolean;
  buy_now_price?: number | string | null;
  currency?: string;
  dimensions?: string | null;
  medium?: string | null;
  year?: number | null;
  is_sold?: boolean;
};

export type Draft = {
  id: string;
  type: "general" | "product";
  title: string | null;
  content: string | null;
  genre: string | null;
  tags: string[] | null;
  language: string;
  media: DraftMedia[];
  product: DraftProduct | null;
  scheduled_at: string | null;
  location_name: string | null;
  location_lat: number | null;
  location_lng: number | null;
  created_at: string;
  updated_at: string; // Q-5 timestamp comparison anchor
};

export type DraftPayload = {
  draft_id?: string;
  type: "general" | "product";
  title?: string | null;
  content?: string | null;
  genre?: string | null;
  tags?: string[] | null;
  language?: string;
  media?: CreatePostMedia[];
  product?: DraftProduct | null;
  scheduled_at?: string | null;
  location_name?: string | null;
  location_lat?: number | null;
  location_lng?: number | null;
  // publish-controls PDCA #8 — persisted in draft for restore continuity
  visibility?: Visibility;
  comments_enabled?: boolean;
  series_ids?: string[];
  // artist-tier-release PDCA #10 — persisted for restore continuity
  early_access_duration?: EarlyAccessDuration | null;
  early_access_tier?: EarlyAccessTier | null;
};

/** List drafts owned by the current user (most recent first).
 *
 * Backend response shape: `{ data: Draft[], total, limit, offset }`.
 * `apiFetch` unwraps `.data`. `total/limit/offset` are not exposed because
 * NFR-4 limits per-user drafts to 20 — no pagination UI needed for v1.
 */
export async function listDrafts(
  limit = 20,
  offset = 0
): Promise<Draft[]> {
  return apiFetch<Draft[]>(
    `/posts/drafts?limit=${limit}&offset=${offset}`
  );
}

/** Fetch a single draft (404 if not owned). */
export async function getDraft(id: string): Promise<Draft> {
  return apiFetch<Draft>(`/posts/drafts/${encodeURIComponent(id)}`);
}

/**
 * Upsert a draft. If `payload.draft_id` is set, updates that draft;
 * otherwise creates a new one. Backend may auto-delete the oldest draft
 * when the per-user limit (20) is hit; that does not raise an error.
 */
export async function saveDraft(payload: DraftPayload): Promise<Draft> {
  return apiFetch<Draft>("/posts/drafts", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/** Delete a draft (idempotent — silent on 404). */
export async function deleteDraft(id: string): Promise<void> {
  await apiFetch<{ deleted: boolean; id: string }>(
    `/posts/drafts/${encodeURIComponent(id)}`,
    { method: "DELETE" }
  );
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

// ─── publish-controls PDCA #8 — Visibility + Series + Publish types ──────

export type Visibility = "public" | "followers_only" | "unlisted";

// ─── artist-tier-release PDCA #10 — Early Access types ───────────────────

export type EarlyAccessTier = "subscriber" | "sponsor" | "follower";
export type EarlyAccessDuration = 1 | 6 | 24 | 72 | 168; // hours

export interface Series {
  id: string;
  author_id: string;
  title: string;
  description?: string | null;
  cover_url?: string | null;
  created_at: string;
  updated_at: string;
  post_count?: number;
}

export interface SeriesCreate {
  title: string;
  description?: string | null;
  cover_url?: string | null;
}

export interface SeriesPatch {
  title?: string;
  description?: string | null;
  cover_url?: string | null;
}

export interface SeriesWithPosts {
  id: string;
  author_id: string;
  title: string;
  description?: string | null;
  cover_url?: string | null;
  created_at: string;
  updated_at: string;
  post_count: number;
  posts: { id: string; title: string | null }[];
}

export interface PostPublishRequest {
  publish_at?: string | null;
  visibility?: Visibility;
  comments_enabled?: boolean;
  series_ids?: string[];
  // artist-tier-release PDCA #10
  early_access_duration?: EarlyAccessDuration | null;
  early_access_tier?: EarlyAccessTier | null;
}

export interface PostPublishResponse {
  id: string;
  status: "published" | "scheduled" | "pending_review";
  visibility: Visibility;
  comments_enabled: boolean;
  scheduled_at: string | null;
  series_count: number;
  updated_at: string;
  // artist-tier-release PDCA #10
  early_access_until?: string | null;
  early_access_tier?: EarlyAccessTier | null;
}

// ─── publish-controls — API client functions (8) ──────────────────────────

export async function listMySeries(): Promise<Series[]> {
  return apiFetch<Series[]>("/series");
}

export async function listSeriesByAuthor(authorId: string): Promise<Series[]> {
  return apiFetch<Series[]>(`/series?author_id=${encodeURIComponent(authorId)}`);
}

export async function createSeries(body: SeriesCreate): Promise<Series> {
  return apiFetch<Series>("/series", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function patchSeries(id: string, body: SeriesPatch): Promise<Series> {
  return apiFetch<Series>(`/series/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function deleteSeries(id: string): Promise<void> {
  await apiFetch<void>(`/series/${encodeURIComponent(id)}`, { method: "DELETE" });
}

export async function getSeriesWithPosts(id: string): Promise<SeriesWithPosts> {
  return apiFetch<SeriesWithPosts>(`/series/${encodeURIComponent(id)}`);
}

export async function setPostSeriesIds(
  postId: string,
  seriesIds: string[]
): Promise<{ post_id: string; series_count: number }> {
  return apiFetch(`/posts/${encodeURIComponent(postId)}/series`, {
    method: "POST",
    body: JSON.stringify({ series_ids: seriesIds }),
  });
}

export async function publishPost(
  postId: string,
  body: PostPublishRequest
): Promise<PostPublishResponse> {
  return apiFetch<PostPublishResponse>(
    `/posts/${encodeURIComponent(postId)}/publish`,
    { method: "POST", body: JSON.stringify(body) }
  );
}
