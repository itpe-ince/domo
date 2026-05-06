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
  /** B'-1: user's preferred display currency (USD/KRW/EUR/JPY). Default "USD". */
  preferred_currency?: string;
  /** Phase 9 L-E: cognitive simple mode flag */
  cognitive_simple_mode?: boolean;
  /** Phase 9 L-E: accessibility preferences JSON */
  accessibility_preferences?: Record<string, unknown>;
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
  // G'-10: cents integer (e.g. 5000 = $50.00 / ₩5000). Use formatPriceCents() to display.
  buy_now_price: number | null;
  // B'-1: native currency the artist priced buy_now in (USD/KRW/EUR/JPY). Default USD.
  buy_now_currency: string;
  // auction currency (KRW default for backward compat)
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
  // K-3 ai-artwork-caption — Phase 9
  ai_caption?: string | null;
  ai_caption_locale_translations?: Record<string, string>;
  ai_caption_generated_at?: string | null;
  caption_override?: string | null;
  effective_caption?: string;
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

/**
 * A-4 Explore Revamp — unified tab-aware explore endpoint.
 *
 * Tabs:
 *  - trending: like/comment count DESC 24h (PostHog flag 'feed-algorithm-v2'
 *              activates algo=v1 personalized re-rank on the server side)
 *  - new:      created_at DESC
 *  - region:   user-region filter (country group)
 *  - genre:    genre filter
 *  - pricing:  auction active OR buy_now_available
 *
 * Falls back to the existing /posts/explore endpoint with appropriate params
 * until a dedicated /v1/explore endpoint is introduced in a later phase.
 */
export async function fetchExplorePosts(params: {
  tab: "trending" | "new" | "region" | "genre" | "pricing";
  region?: string;
  genre?: string;
  cursor?: string;
  limit?: number;
}): Promise<PostView[]> {
  const qs = new URLSearchParams();
  qs.set("limit", String(params.limit ?? 20));

  switch (params.tab) {
    case "trending":
      qs.set("sort", "popular");
      break;
    case "new":
      qs.set("sort", "latest");
      break;
    case "region":
      qs.set("sort", "latest");
      if (params.region) qs.set("region", params.region);
      break;
    case "genre":
      qs.set("sort", "latest");
      if (params.genre) qs.set("genre", params.genre);
      break;
    case "pricing":
      qs.set("sort", "latest");
      qs.set("type", "product");
      break;
  }

  if (params.cursor) qs.set("cursor", params.cursor);

  return apiFetch<PostView[]>(`/posts/explore?${qs.toString()}`, { auth: false });
}

// CO-1 PR-4: "v2" 추가 — K-8 Feature Flag 분기에서 algo="v2" 사용 시 타입 안전성 확보
export type FeedAlgo = "default" | "v1" | "v2" | "auto";

export type FeedPagination = {
  next_cursor: string | null;
  has_more: boolean;
};

export type FeedResponse = {
  data: PostView[];
  pagination: FeedPagination;
};

/**
 * Fetch personalized home feed.
 *
 * Backend response shape: { "data": PostView[], "pagination": FeedPagination }
 * apiFetch<T> extracts .data from { "data": T }, so we use a raw fetch here
 * to preserve both data + pagination from the top-level response object.
 *
 * @param algo  "default" = legacy chronological mix (70% following + 30% trending).
 *              "v1"      = A-3 personalized (score-ranked, cursor pagination).
 *              Controlled by PostHog feature flag 'feed-algorithm-v2'.
 * @param limit Number of posts per page (1–100).
 * @param cursor Opaque pagination cursor from previous response.pagination.next_cursor.
 */
export async function fetchHomeFeed(
  limit = 20,
  algo: FeedAlgo = "default",
  cursor?: string,
): Promise<FeedResponse> {
  const qs = new URLSearchParams({ limit: String(limit), algo });
  if (cursor) qs.set("cursor", cursor);

  const token = tokenStore.get();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/posts/feed?${qs.toString()}`, { headers });

  // Auto-refresh on 401
  if (res.status === 401 && token) {
    const ok = await tryRefreshAccessToken();
    if (ok) {
      const newToken = tokenStore.get();
      if (newToken) headers["Authorization"] = `Bearer ${newToken}`;
      const retried = await fetch(`${API_BASE}/posts/feed?${qs.toString()}`, { headers });
      const json = await retried.json() as { data?: PostView[]; pagination?: FeedPagination };
      return {
        data: json.data ?? [],
        pagination: json.pagination ?? { next_cursor: null, has_more: false },
      };
    }
  }

  const json = await res.json() as { data?: PostView[]; pagination?: FeedPagination };
  return {
    data: json.data ?? [],
    pagination: json.pagination ?? { next_cursor: null, has_more: false },
  };
}

export async function fetchFollowingFeed(limit = 20): Promise<PostView[]> {
  const res = await apiFetch<FeedResponse | PostView[]>(
    `/posts/feed?limit=${limit}&following_only=true`
  );
  if (Array.isArray(res)) return res;
  return (res as FeedResponse).data;
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
    // G'-10: cents integer (matching backend price_min/price_max query params)
    price_min?: number;
    price_max?: number;
    limit?: number;
  }
): Promise<PostView[]> {
  const qs = new URLSearchParams({ q });
  if (opts?.type) qs.set("type", opts.type);
  if (opts?.genre) qs.set("genre", opts.genre);
  if (opts?.sort) qs.set("sort", opts.sort);
  if (opts?.price_min != null) qs.set("price_min", String(opts.price_min));
  if (opts?.price_max != null) qs.set("price_max", String(opts.price_max));
  qs.set("limit", String(opts?.limit ?? 20));
  return apiFetch<PostView[]>(`/posts/search?${qs}`, { auth: false });
}

// ─── Search v2 (A-5) ────────────────────────────────────────────────────────

export type SearchV2Filters = {
  type?: "artists" | "artworks" | "posts" | "all";
  sort?: "relevance" | "latest" | "popular";
  price_min?: number;
  price_max?: number;
  region?: string;
  tier_only?: boolean;
  active?: boolean;
  cursor?: string;
  limit?: number;
};

export type SearchV2ArtistResult = {
  type: "artist";
  id: string;
  display_name: string;
  avatar_url: string | null;
  bio: string | null;
  role: string;
  country: string | null;
  follower_count: number;
};

export type SearchV2Results = {
  artists: SearchV2ArtistResult[];
  artworks: PostView[];
  posts: PostView[];
};

export type SearchV2Response = {
  data: SearchV2Results;
  pagination: { next_cursor: string | null; has_more: boolean };
};

export async function searchV2(
  q: string,
  opts?: SearchV2Filters
): Promise<SearchV2Response> {
  const qs = new URLSearchParams({ q });
  if (opts?.type) qs.set("type", opts.type);
  if (opts?.sort) qs.set("sort", opts.sort);
  if (opts?.price_min != null) qs.set("price_min", String(opts.price_min));
  if (opts?.price_max != null) qs.set("price_max", String(opts.price_max));
  if (opts?.region) qs.set("region", opts.region);
  if (opts?.tier_only) qs.set("tier_only", "true");
  if (opts?.active) qs.set("active", "true");
  if (opts?.cursor) qs.set("cursor", opts.cursor);
  qs.set("limit", String(opts?.limit ?? 20));
  return apiFetch<SearchV2Response>(`/search?${qs}`, { auth: false });
}

// ─── Search History (A-5) ────────────────────────────────────────────────────

export type SearchHistoryEntry = {
  id: string;
  query: string;
  result_count: number;
  searched_at: string;
};

export type PopularSearchItem = {
  query: string;
  count: number;
};

export async function fetchSearchHistory(
  limit = 10
): Promise<SearchHistoryEntry[]> {
  const res = await apiFetch<{ data: SearchHistoryEntry[] }>(
    `/me/search/history?limit=${limit}`
  );
  return res.data;
}

export async function deleteSearchHistoryEntry(id: string): Promise<void> {
  await apiFetch(`/me/search/history/${id}`, { method: "DELETE" });
}

export async function clearSearchHistory(): Promise<void> {
  await apiFetch("/me/search/history", { method: "DELETE" });
}

export async function fetchPopularSearches(
  limit = 10
): Promise<PopularSearchItem[]> {
  const res = await apiFetch<{ data: PopularSearchItem[] }>(
    `/search/popular?limit=${limit}`,
    { auth: false }
  );
  return res.data;
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

// ─── K-5 도슨트 API — llm-docent-artwork ────────────────────────────────

export type DocentView = {
  post_id: string;
  artist_docent_text: string | null;
  ai_docent_text: string | null;
  ai_docent_opted_out: boolean;
  ai_docent_generated_at: string | null;
  locale_docent: string | null;
  locale: string;
};

export type DocentGenerateResult = {
  ai_docent_text: string | null;
  ai_docent_model_version: string | null;
  ai_docent_generated_at: string | null;
  ai_docent_translations: Record<string, string>;
  message?: string;
};

/** GET /posts/{id}/docent — 공개 조회 (인증 불필요) */
export async function fetchDocent(
  postId: string,
  locale: string = "ko"
): Promise<DocentView> {
  return apiFetch<DocentView>(`/posts/${postId}/docent?locale=${locale}`, {
    auth: false,
  });
}

/** POST /posts/{id}/docent/generate — AI 도슨트 생성 (작가 전용) */
export async function generateDocent(postId: string): Promise<DocentGenerateResult> {
  return apiFetch<DocentGenerateResult>(`/posts/${postId}/docent/generate`, {
    method: "POST",
  });
}

/** PATCH /posts/{id}/docent — 작가 직접 해설 작성 */
export async function patchArtistDocent(
  postId: string,
  artistDocentText: string | null
): Promise<{ artist_docent_text: string | null; updated_at: string }> {
  return apiFetch(`/posts/${postId}/docent`, {
    method: "PATCH",
    body: JSON.stringify({ artist_docent_text: artistDocentText }),
  });
}

/** PATCH /posts/{id}/docent/opt-out — AI 도슨트 비활성화 토글 */
export async function patchDocentOptOut(
  postId: string,
  optedOut: boolean
): Promise<{ ai_docent_opted_out: boolean; message: string }> {
  return apiFetch(`/posts/${postId}/docent/opt-out`, {
    method: "PATCH",
    body: JSON.stringify({ opted_out: optedOut }),
  });
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
  // D'-2 / A-8 booster: cancellation reason for conditional WinbackBanner message
  cancellation_reason?: "too_expensive" | "changed_mind" | "not_satisfied" | "other" | null;
  // B'-4: auto-renewal toggle
  auto_renew_enabled: boolean;
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

// B-5: cancel reason + feedback body (backward-compat — reason optional)
export type CancelSubscriptionInput = {
  reason?: "too_expensive" | "changed_mind" | "not_satisfied" | "other";
  feedback?: string;
  immediate?: boolean;
};

export async function cancelSubscription(
  id: string,
  input?: CancelSubscriptionInput
) {
  return apiFetch<SubscriptionView>(`/subscriptions/${id}`, {
    method: "DELETE",
    body: input ? JSON.stringify(input) : undefined,
  });
}

export async function fetchMySubscriptions() {
  return apiFetch<SubscriptionView[]>("/subscriptions/mine");
}

// ─── B'-4: Auto-renewal endpoints ───────────────────────────────────────────

export type RenewSubscriptionResponse = SubscriptionView & {
  renewed_at: string;
  message: string;
};

/**
 * POST /v1/subscriptions/{id}/renew
 * Manually triggers renewal for a subscription:
 *   - active + cancel_at_period_end → reverts cancellation flag
 *   - cancelled → creates new Stripe subscription
 *   - past_due  → triggers retry (Stripe handles automatically)
 *   - active (normal) → idempotent 200
 */
export async function renewSubscription(id: string) {
  return apiFetch<RenewSubscriptionResponse>(`/subscriptions/${id}/renew`, {
    method: "POST",
  });
}

/**
 * PATCH /v1/subscriptions/{id}/auto-renew
 * Enables or disables auto-renewal monitoring for the subscription.
 * When disabled, user must manually renew via renewSubscription().
 */
export async function toggleAutoRenew(
  id: string,
  auto_renew_enabled: boolean
) {
  return apiFetch<SubscriptionView>(`/subscriptions/${id}/auto-renew`, {
    method: "PATCH",
    body: JSON.stringify({ auto_renew_enabled }),
  });
}

// ─── B-5 + D'-2: Churn list (artist dashboard) ──────────────────────────────

export type CancellationReason =
  | "too_expensive"
  | "changed_mind"
  | "not_satisfied"
  | "other";

export type ChurnItem = {
  user_id: string;
  username: string;
  avatar_url: string | null;
  cancelled_at: string; // ISO8601
  cancellation_reason: CancellationReason | null;
  cancellation_feedback_preview: string | null; // max 100 chars
  tier: "subscriber" | "sponsor";
  lifetime_amount_cents: number;
};

export type ChurnListResponse = {
  data: ChurnItem[];
};

export async function fetchChurnList(limit = 20): Promise<ChurnItem[]> {
  const res = await apiFetch<ChurnListResponse>(
    `/me/patronage/churn?limit=${limit}`
  );
  return res.data ?? [];
}

// ─── Payments (B-1 Blue Bird SetupIntent) ────────────────────────────────

export type SetupIntentResponse = {
  client_secret: string;
  customer_id: string;
  setup_intent_id: string;
};

export async function createSetupIntent(
  metadata?: Record<string, string>
): Promise<SetupIntentResponse> {
  return apiFetch<SetupIntentResponse>("/payments/setup-intent", {
    method: "POST",
    body: JSON.stringify({ metadata: metadata ?? null }),
  });
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

export type NotificationFilter = "all" | "unread" | "auction" | "sponsorship" | "engagement" | "system";

export async function fetchNotifications(unreadOnly = false, limit = 30) {
  const qs = new URLSearchParams();
  if (unreadOnly) qs.set("unread_only", "true");
  qs.set("limit", String(limit));
  return apiFetch<NotificationView[]>(`/notifications?${qs.toString()}`);
}

export async function fetchNotificationsByFilter(
  filter: NotificationFilter,
  limit = 50
) {
  const qs = new URLSearchParams();
  qs.set("limit", String(limit));
  if (filter === "unread") {
    qs.set("unread_only", "true");
  } else if (filter !== "all") {
    qs.set("types", filter);
  }
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

export async function markReadByType(types: string) {
  const qs = new URLSearchParams({ types });
  return apiFetch<{ updated: number; types: string[] }>(
    `/notifications/mark-read-by-type?${qs.toString()}`,
    { method: "POST" }
  );
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
 *
 * upload-retry-ui (D-2): `onAbortRef` receives the `xhr.abort` method so the
 * caller can cancel mid-flight without holding a reference to the XHR itself.
 */
export async function uploadMediaFileWithProgress(
  file: File,
  isMakingVideo = false,
  onProgress?: (e: UploadProgressEvent) => void,
  onAbortRef?: (abortFn: () => void) => void
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

    // Expose abort so the caller can cancel the upload (upload-retry-ui D-2).
    if (onAbortRef) {
      onAbortRef(() => xhr.abort());
    }

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
      // Attach the HTTP status so error-message mappers can branch on it.
      const clientErr = new ApiClientError(err.code, err.message, err.details);
      (clientErr as ApiClientError & { httpStatus?: number }).httpStatus = xhr.status;
      reject(clientErr);
    };

    xhr.onerror = () =>
      reject(new ApiClientError("NETWORK_ERROR", "네트워크 오류"));
    xhr.ontimeout = () =>
      reject(new ApiClientError("UPLOAD_TIMEOUT", "업로드 시간 초과"));
    xhr.onabort = () =>
      reject(new ApiClientError("UPLOAD_CANCELLED", "업로드 취소됨"));

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
    // G'-10: send dollar float (e.g. 50.0); backend ProductPostIn.dollars_to_cents
    // validator converts to cents before persistence.
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
  // G'-10: draft product stores cents integer from DB. UI shows dollars.
  buy_now_price?: number | null;
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

// ─── D'-1 sponsor validity settings ──────────────────────────────────────

export type SponsorValidityDays = 1 | 7 | 30 | 90 | 365 | null;

export interface SponsorSettingsView {
  sponsor_validity_days: SponsorValidityDays;
}

export async function fetchSponsorSettings(): Promise<SponsorSettingsView> {
  return apiFetch<SponsorSettingsView>("/me/sponsor-settings");
}

export async function patchSponsorSettings(
  sponsor_validity_days: SponsorValidityDays
): Promise<SponsorSettingsView> {
  return apiFetch<SponsorSettingsView>("/me/sponsor-settings", {
    method: "PATCH",
    body: JSON.stringify({ sponsor_validity_days }),
  });
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

// ─── Artist patronage dashboard (B-2) ────────────────────────────────────────

export type TierDistribution = {
  subscriber: number;
  sponsor: number;
  follower: number;
};

export type PatronageSummary = {
  total_supporters: number;
  total_sponsors: number;
  total_subscribers: number;
  lifetime_revenue_usd_cents: number;
  current_month_revenue_usd_cents: number;
  previous_month_revenue_usd_cents: number;
  active_subscriptions: number;
  churned_last_30d: number;
  tier_distribution: TierDistribution;
  currency: string;
};

export type SupporterItem = {
  user_id: string;
  username: string;
  avatar_url: string | null;
  tier: "sponsor" | "subscriber" | "follower";
  since: string;
  lifetime_amount_cents: number;
  monthly_amount_cents: number;
  subscription_status: "active" | "cancelled" | "past_due" | null;
};

export type SupportersResponse = {
  data: SupporterItem[];
  next_cursor: string | null;
  has_more: boolean;
};

export type RevenueDataPoint = {
  date: string;
  amount_cents: number;
  currency: string;
};

export type RevenueResponse = {
  data: RevenueDataPoint[];
  from_date: string;
  to_date: string;
  granularity: "daily" | "monthly";
};

export type PayoutRequestInput = {
  amount_cents: number;
  currency: string;
  method: "bank_transfer" | "stripe";
};

export type PayoutRequestResult = {
  id: string;
  amount_cents: number;
  currency: string;
  method: string;
  status: string;
  created_at: string;
};

export async function fetchPatronageSummary(): Promise<PatronageSummary> {
  return apiFetch<PatronageSummary>("/me/patronage/summary");
}

export async function fetchSupporters(params?: {
  cursor?: string;
  limit?: number;
  filter?: "active" | "churned" | "all";
}): Promise<SupportersResponse> {
  const qs = new URLSearchParams();
  if (params?.cursor) qs.set("cursor", params.cursor);
  if (params?.limit) qs.set("limit", String(params.limit));
  if (params?.filter) qs.set("filter", params.filter);
  return apiFetch<SupportersResponse>(`/me/patronage/supporters?${qs.toString()}`);
}

export async function fetchPatronageRevenue(params?: {
  from?: string;
  to?: string;
  granularity?: "daily" | "monthly";
}): Promise<RevenueResponse> {
  const qs = new URLSearchParams();
  if (params?.from) qs.set("from", params.from);
  if (params?.to) qs.set("to", params.to);
  if (params?.granularity) qs.set("granularity", params.granularity);
  return apiFetch<RevenueResponse>(`/me/patronage/revenue?${qs.toString()}`);
}

export async function requestPayout(
  input: PayoutRequestInput
): Promise<PayoutRequestResult> {
  return apiFetch<PayoutRequestResult>("/me/patronage/payout-request", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

// ─── B'-5: Patronage analytics (PostHog proxy / self-aggregated) ──────────────

export type PatronageAnalyticsResponse = {
  cohort_retention: Array<{ week: string; d1: number; d7: number; d30: number }>;
  coupon_redemption: {
    issued: number;
    applied: number;
    cancel_reverted: number;
    expired: number;
  };
  newsletter: Array<{
    issue: string;
    sent: number;
    opened: number;
    clicked: number;
    open_rate: number;
    click_rate: number;
  }>;
  conversion_funnel: {
    post_click: number;
    sponsor_start: number;
    sponsor_success: number;
    active_30d: number;
  };
  dm_engagement: {
    first_message_rate: number;
    avg_response_minutes: number;
    total_threads: number;
  };
  is_mock: boolean;
};

/**
 * GET /v1/me/patronage/analytics
 *
 * Returns aggregated analytics data for the authenticated artist.
 * Backend caches with Redis (1h TTL) and falls back to mock data
 * when PostHog API key is not configured.
 */
export async function fetchPatronageAnalytics(): Promise<PatronageAnalyticsResponse> {
  return apiFetch<PatronageAnalyticsResponse>("/me/patronage/analytics");
}

// ─── Tier benefits (B-4) ──────────────────────────────────────────────────

export type TierBenefitsItem = {
  tier: "subscriber" | "sponsor" | "follower";
  benefits: string[];
  welcome_message: string | null;
  is_platform_default: boolean;
  /** i18n key for platform default text — only present when is_platform_default=true */
  platform_default_key: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type AllTierBenefits = {
  subscriber: TierBenefitsItem;
  sponsor: TierBenefitsItem;
  follower: TierBenefitsItem;
};

export type TierBenefitsUpsertInput = {
  benefits: string[];
  welcome_message?: string | null;
};

/** Fetch the authenticated artist's tier benefits for all 3 tiers. */
export async function fetchMyTierBenefits(): Promise<AllTierBenefits> {
  return apiFetch<AllTierBenefits>("/me/tier-benefits");
}

/** Upsert benefits for a specific tier (artist only). */
export async function putMyTierBenefits(
  tier: "subscriber" | "sponsor" | "follower",
  input: TierBenefitsUpsertInput
): Promise<TierBenefitsItem> {
  return apiFetch<TierBenefitsItem>(`/me/tier-benefits/${tier}`, {
    method: "PUT",
    body: JSON.stringify(input),
  });
}

/** Remove artist override for a tier — reverts to platform default. */
export async function deleteMyTierBenefits(
  tier: "subscriber" | "sponsor" | "follower"
): Promise<void> {
  await apiFetch<void>(`/me/tier-benefits/${tier}`, { method: "DELETE" });
}

/** Fetch any artist's tier benefits (public, no auth required). */
export async function fetchUserTierBenefits(
  userId: string
): Promise<AllTierBenefits> {
  return apiFetch<AllTierBenefits>(`/users/${encodeURIComponent(userId)}/tier-benefits`, {
    auth: false,
  });
}

// ─── D'-3 Coupon types + API ──────────────────────────────────────────────

export type CouponDiscountType = "percent" | "amount";
export type CouponDuration = "once" | "forever" | "repeating";

/** Coupon descriptor returned by admin endpoints (mirrors backend CouponOut). */
export type CouponView = {
  id: string;
  code: string | null;
  discount_type: CouponDiscountType;
  discount_value: number;
  duration: CouponDuration;
  duration_in_months: number | null;
  valid_until: string | null; // ISO8601
  max_redemptions: number | null;
  times_redeemed: number;
  active: boolean;
};

/** Applied coupon row (mirrors backend AppliedCouponOut). */
export type AppliedCouponView = {
  id: string;
  user_id: string;
  subscription_id: string | null;
  stripe_coupon_id: string;
  coupon_code: string | null;
  discount_type: CouponDiscountType;
  discount_value: number;
  duration: CouponDuration;
  duration_in_months: number | null;
  valid_until: string | null;
  applied_at: string;
  redeemed_at: string | null;
};

export type AdminCreateCouponInput = {
  code: string;
  discount_type: CouponDiscountType;
  discount_value: number;
  duration: CouponDuration;
  duration_in_months?: number | null;
  valid_until?: string | null; // ISO8601 or null
  max_redemptions?: number | null;
};

// Admin: create coupon
export async function adminCreateCoupon(
  input: AdminCreateCouponInput
): Promise<CouponView> {
  return apiFetch<CouponView>("/admin/coupons", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

// Admin: list coupons
export async function adminListCoupons(params?: {
  limit?: number;
  starting_after?: string;
}): Promise<CouponView[]> {
  const qs = new URLSearchParams();
  if (params?.limit) qs.set("limit", String(params.limit));
  if (params?.starting_after) qs.set("starting_after", params.starting_after);
  return apiFetch<CouponView[]>(`/admin/coupons?${qs.toString()}`);
}

// Admin: delete coupon
export async function adminDeleteCoupon(couponId: string): Promise<void> {
  await apiFetch<void>(`/admin/coupons/${encodeURIComponent(couponId)}`, {
    method: "DELETE",
  });
}

// User: apply coupon to own subscription
export async function applyMyCoupon(input: {
  coupon_code: string;
  subscription_id?: string | null;
}): Promise<AppliedCouponView> {
  return apiFetch<AppliedCouponView>("/me/coupons/apply", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

// User: list own applied coupons
export async function fetchMyCoupons(limit = 20): Promise<AppliedCouponView[]> {
  return apiFetch<AppliedCouponView[]>(`/me/coupons?limit=${limit}`);
}

// ─── G'-2: winback coupon ────────────────────────────────────────────────────

export type WinbackReason =
  | "too_expensive"
  | "changed_mind"
  | "not_satisfied"
  | "other";

export type WinbackCouponResponse = {
  coupon_applied: boolean;
  cancel_reverted: boolean;
  dm_link: string | null;
  applied_coupon: AppliedCouponView;
};

/**
 * POST /v1/subscriptions/{id}/winback-coupon
 *
 * Applies a reason-based winback coupon to the subscription and reverts
 * any pending cancellation (cancel_at_period_end → false).
 *
 * Rate limit: 1/day/subscription enforced by backend.
 */
export async function applyWinbackCoupon(
  subscriptionId: string,
  reason: WinbackReason,
  feedback?: string
): Promise<WinbackCouponResponse> {
  return apiFetch<WinbackCouponResponse>(
    `/subscriptions/${subscriptionId}/winback-coupon`,
    {
      method: "POST",
      body: JSON.stringify({
        reason,
        ...(feedback ? { feedback } : {}),
      }),
    }
  );
}

// ─── Onboarding — A-2 recommended artists ───────────────────────────────

/** Slim artist card returned by GET /onboarding/recommended-artists. */
export type RecommendedArtist = {
  user_id: string;
  username: string;
  avatar_url: string | null;
  bio_short: string | null;
  tier_default: string;
  recent_works_count: number;
};

/**
 * Fetch recommended artists for the growth-funnel onboarding wizard.
 * Backend selects top artists by follower count; result is shuffled per
 * request to provide visual variety across sessions.
 * Auth is optional — endpoint accepts anonymous requests as well.
 */
export async function fetchRecommendedArtists(
  limit = 5
): Promise<RecommendedArtist[]> {
  return apiFetch<RecommendedArtist[]>(
    `/onboarding/recommended-artists?limit=${limit}`,
    { auth: false }
  );
}

/**
 * Follow an artist by user_id.
 * Returns void on 200/204.
 */
export async function followArtist(artistUserId: string): Promise<void> {
  await apiFetch<void>(`/users/${encodeURIComponent(artistUserId)}/follow`, {
    method: "POST",
  });
}

/**
 * Unfollow an artist.
 */
export async function unfollowArtist(artistUserId: string): Promise<void> {
  await apiFetch<void>(`/users/${encodeURIComponent(artistUserId)}/follow`, {
    method: "DELETE",
  });
}

// ─── Artist Index (A-6) ─────────────────────────────────────────────────────

/** Single entry in the global artist ranking list. */
export type ArtistIndexEntry = {
  user_id: string;
  username: string;
  avatar_url: string | null;
  country: string | null;
  primary_genre: string | null;
  score: number;
  rank: number;
  tier_badge: "top_10" | "top_100" | "top_1000" | null;
  // G'-8: region/genre sub-rankings
  rank_region: number | null;
  rank_genre: number | null;
};

/** Response from GET /v1/artists/index */
export type ArtistIndexListResponse = {
  data: ArtistIndexEntry[];
  next_cursor: string | null;
  total: number | null;
};

/** Response from GET /v1/artists/{user_id}/index */
export type ArtistRankingResponse = {
  score: number;
  rank: number;
  rank_region: number | null;
  rank_genre: number | null;
  primary_genre: string | null;
  tier_badge: "top_10" | "top_100" | "top_1000" | null;
  last_calculated_at: string | null;
};

/**
 * Fetch the global artist ranking list (public, no auth required).
 * Supports region/genre filters and cursor pagination.
 *
 * The backend returns a double-wrapped envelope:
 *   { "data": { "data": [entries...], "next_cursor": "...", "total": null } }
 * apiFetch<T> unwraps one level ("data" key), yielding ArtistIndexListResponse
 * which itself has { data: ArtistIndexEntry[], next_cursor: string|null, total: number|null }.
 */
export async function fetchArtistIndex(params?: {
  region?: string;
  genre?: string;
  limit?: number;
  cursor?: string;
}): Promise<ArtistIndexListResponse> {
  const qs = new URLSearchParams();
  if (params?.region) qs.set("region", params.region);
  if (params?.genre) qs.set("genre", params.genre);
  if (params?.limit) qs.set("limit", String(params.limit));
  if (params?.cursor) qs.set("cursor", params.cursor);
  return apiFetch<ArtistIndexListResponse>(
    `/artists/index?${qs.toString()}`,
    { auth: false }
  );
}

// ─── G'-7 Featured Artist ────────────────────────────────────────────────────

/** Public view of the current featured artist (from /featured/artist/current). */
export type ArtistFeaturedView = {
  user_id: string;
  username: string;
  avatar_url: string | null;
  bio: string | null;
  country: string | null;
  primary_genre: string | null;
  tier_badge: "top_10" | "top_100" | "top_1000" | null;
  rank: number | null;
  score: number | null;
  curation_note: string | null;
  month: string; // "YYYY-MM"
  is_curated: boolean;
};

/** Admin: serialized featured artist row. */
export type FeaturedArtistOut = {
  id: string;
  artist_id: string;
  month: string; // "YYYY-MM-DD" (always first of month)
  curation_note: string | null;
  is_active: boolean;
  created_at: string;
  created_by_admin_id: string;
};

/** Fetch the current month's featured artist (public, graceful 404 → null). */
export async function fetchFeaturedArtist(): Promise<ArtistFeaturedView | null> {
  try {
    return await apiFetch<ArtistFeaturedView>("/featured/artist/current", {
      auth: false,
    });
  } catch (e) {
    if (e instanceof ApiClientError && e.code === "NO_FEATURED_ARTIST") {
      return null;
    }
    throw e;
  }
}

/** Admin: create or replace the featured artist for a month. */
export async function adminCreateFeaturedArtist(body: {
  artist_id: string;
  month: string; // "YYYY-MM-01"
  curation_note?: string;
}): Promise<FeaturedArtistOut> {
  return apiFetch<FeaturedArtistOut>("/admin/featured-artists", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

/** Admin: list featured artist history. */
export async function adminListFeaturedArtists(params?: {
  month?: string; // "YYYY-MM"
  limit?: number;
}): Promise<FeaturedArtistOut[]> {
  const qs = new URLSearchParams();
  if (params?.month) qs.set("month", params.month);
  if (params?.limit) qs.set("limit", String(params.limit));
  return apiFetch<FeaturedArtistOut[]>(
    `/admin/featured-artists?${qs.toString()}`
  );
}

/** Admin: soft-delete (deactivate) a featured artist entry. */
export async function adminDeleteFeaturedArtist(id: string): Promise<void> {
  return apiFetch<void>(`/admin/featured-artists/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}

/**
 * Fetch ranking data for a single artist by user_id.
 * Returns null if the artist hasn't been ranked yet (404).
 */
export async function fetchArtistRanking(userId: string): Promise<ArtistRankingResponse | null> {
  try {
    return await apiFetch<ArtistRankingResponse>(`/artists/${encodeURIComponent(userId)}/index`, {
      auth: false,
    });
  } catch (e) {
    if (e instanceof ApiClientError && (e.code === "NOT_FOUND" || e.code === "NOT_RANKED")) {
      return null;
    }
    throw e;
  }
}

// ─── C-1: Artist Interviews ───────────────────────────────────────────────────

export type ArtistInterviewOut = {
  id: string;
  artist_id: string;
  locale: string;
  title: string;
  body_markdown: string;
  status: string;
  llm_model: string | null;
  reviewed_by_admin_id: string | null;
  reviewed_at: string | null;
  review_note: string | null;
  artist_consent_at: string | null;
  created_at: string;
  updated_at: string;
};

export type ArtistInterviewPublicOut = {
  id: string;
  artist_id: string;
  locale: string;
  title: string;
  body_markdown: string;
  published_at: string;
};

/** Admin: trigger LLM interview generation for an artist. */
export async function adminGenerateInterview(body: {
  artist_id: string;
  locale: string;
}): Promise<ArtistInterviewOut> {
  return apiFetch<ArtistInterviewOut>("/admin/artist-interviews/generate", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

/** Admin: list interviews with optional status/artist filter. */
export async function adminListInterviews(params?: {
  status?: string;
  artist_id?: string;
  limit?: number;
}): Promise<ArtistInterviewOut[]> {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
  if (params?.artist_id) qs.set("artist_id", params.artist_id);
  if (params?.limit) qs.set("limit", String(params.limit));
  return apiFetch<ArtistInterviewOut[]>(
    `/admin/artist-interviews?${qs.toString()}`
  );
}

/** Admin: approve or reject an interview + optional edits. */
export async function adminPatchInterview(
  id: string,
  body: {
    status?: "approved" | "rejected";
    title?: string;
    body_markdown?: string;
    review_note?: string;
  }
): Promise<ArtistInterviewOut> {
  return apiFetch<ArtistInterviewOut>(
    `/admin/artist-interviews/${encodeURIComponent(id)}`,
    {
      method: "PATCH",
      body: JSON.stringify(body),
    }
  );
}

/** Admin: publish an approved + consented interview. */
export async function adminPublishInterview(
  id: string
): Promise<ArtistInterviewOut> {
  return apiFetch<ArtistInterviewOut>(
    `/admin/artist-interviews/${encodeURIComponent(id)}/publish`,
    { method: "POST" }
  );
}

/** Artist (me): list own interviews. */
export async function fetchMyInterviews(): Promise<ArtistInterviewOut[]> {
  return apiFetch<ArtistInterviewOut[]>("/me/interviews");
}

/** Artist (me): provide GDPR consent for interview publication. */
export async function consentInterview(
  id: string
): Promise<ArtistInterviewOut> {
  return apiFetch<ArtistInterviewOut>(
    `/me/interviews/${encodeURIComponent(id)}/consent`,
    { method: "POST" }
  );
}

/** Artist (me): reject interview publication. */
export async function rejectInterviewPublication(
  id: string
): Promise<ArtistInterviewOut> {
  return apiFetch<ArtistInterviewOut>(
    `/me/interviews/${encodeURIComponent(id)}/reject`,
    { method: "POST" }
  );
}

/** Public: fetch published interviews for an artist. */
export async function fetchArtistInterviews(
  userId: string,
  locale?: string
): Promise<ArtistInterviewPublicOut[]> {
  const qs = locale ? `?locale=${encodeURIComponent(locale)}` : "";
  return apiFetch<ArtistInterviewPublicOut[]>(
    `/users/${encodeURIComponent(userId)}/interviews${qs}`,
    { auth: false }
  );
}

// ─── C-3: Bio multi-language ──────────────────────────────────────────────────

export type BioTranslationOut = {
  user_id: string;
  locale: string;
  bio: string;
  is_machine_translated: boolean;
  last_edited_at: string;
  last_translated_at: string | null;
};

export type BioTranslateResponse = {
  translations: Record<string, string>; // locale → translated text
};

/** Artist (me): get all locale bios. */
export async function fetchMyBioTranslations(): Promise<BioTranslationOut[]> {
  return apiFetch<BioTranslationOut[]>("/me/bio");
}

/** Artist (me): trigger LLM auto-translate bio to all 5 locales. */
export async function translateMyBio(
  sourceLocale: string = "ko"
): Promise<BioTranslateResponse> {
  return apiFetch<BioTranslateResponse>(
    `/me/bio/translate?source_locale=${encodeURIComponent(sourceLocale)}`,
    { method: "POST" }
  );
}

/** Artist (me): manually edit bio for one locale. */
export async function patchMyBioLocale(
  locale: string,
  bio: string
): Promise<BioTranslationOut> {
  return apiFetch<BioTranslationOut>(`/me/bio/${encodeURIComponent(locale)}`, {
    method: "PATCH",
    body: JSON.stringify({ bio }),
  });
}

/** Public: fetch artist bio for a specific locale (falls back to ko). */
export async function fetchUserBio(
  userId: string,
  locale?: string
): Promise<{ user_id: string; locale: string; bio: string | null; is_machine_translated: boolean }> {
  const qs = locale ? `?locale=${encodeURIComponent(locale)}` : "";
  return apiFetch<{ user_id: string; locale: string; bio: string | null; is_machine_translated: boolean }>(
    `/users/${encodeURIComponent(userId)}/bio${qs}`,
    { auth: false }
  );
}

// ─── C-2: Press kit ──────────────────────────────────────────────────────────

export type PressKitOut = {
  id: string;
  artist_id: string;
  locale: string;
  storage_key: string;
  download_url: string;
  file_size_bytes: number;
  page_count: number;
  interview_id: string | null;
  is_public: boolean;
  expires_at: string;
  created_at: string;
};

/** Admin: trigger press kit PDF generation for an artist. */
export async function adminGeneratePressKit(params: {
  user_id: string;
  locale?: string;
  force?: boolean;
}): Promise<PressKitOut> {
  const qs = new URLSearchParams();
  if (params.locale) qs.set("locale", params.locale);
  if (params.force) qs.set("force", "true");
  const query = qs.toString() ? `?${qs.toString()}` : "";
  return apiFetch<PressKitOut>(
    `/admin/artists/${encodeURIComponent(params.user_id)}/press-kit/generate${query}`,
    { method: "POST" }
  );
}

/** Admin: list press kit generation history for an artist. */
export async function adminListPressKits(params: {
  user_id: string;
  limit?: number;
}): Promise<PressKitOut[]> {
  const qs = params.limit ? `?limit=${params.limit}` : "";
  return apiFetch<PressKitOut[]>(
    `/admin/artists/${encodeURIComponent(params.user_id)}/press-kit/history${qs}`
  );
}

/** Public: fetch artist's public press kit (is_public=true, not expired). */
export async function fetchUserPressKit(
  userId: string,
  locale?: string
): Promise<PressKitOut> {
  const qs = locale ? `?locale=${encodeURIComponent(locale)}` : "";
  return apiFetch<PressKitOut>(
    `/users/${encodeURIComponent(userId)}/press-kit${qs}`,
    { auth: false }
  );
}

/** Artist (me): fetch own press kit info. */
export async function fetchMyPressKit(locale?: string): Promise<PressKitOut> {
  const qs = locale ? `?locale=${encodeURIComponent(locale)}` : "";
  return apiFetch<PressKitOut>(`/me/press-kit${qs}`);
}

// ─── C-4 Media Coverage ───────────────────────────────────────────────────────

export type CoverageType = "article" | "youtube" | "radio" | "podcast" | "tv";

export type MediaCoverageOut = {
  id: string;
  title: string;
  coverage_type: CoverageType;
  source_name: string;
  external_url: string;
  thumbnail_url: string | null;
  published_at: string; // ISO date "YYYY-MM-DD"
  artist_id: string | null;
  description: string | null;
  locale: string;
  is_published: boolean;
  is_featured: boolean;
  created_by_admin_id: string;
  created_at: string;
  updated_at: string;
};

export type AdminCreateMediaCoverageBody = {
  title: string;
  coverage_type: CoverageType;
  source_name: string;
  external_url: string;
  thumbnail_url?: string | null;
  published_at: string; // "YYYY-MM-DD"
  artist_id?: string | null;
  description?: string | null;
  locale: string;
  is_published?: boolean;
  is_featured?: boolean;
};

export type AdminPatchMediaCoverageBody = Partial<{
  title: string;
  description: string | null;
  thumbnail_url: string | null;
  is_published: boolean;
  is_featured: boolean;
  source_name: string;
  coverage_type: CoverageType;
  external_url: string;
  published_at: string;
  locale: string;
  artist_id: string | null;
}>;

export type MediaCoverageListResponse = {
  data: MediaCoverageOut[];
  next_cursor: string | null;
};

/** Admin: create a new media coverage entry. */
export async function adminCreateMediaCoverage(
  body: AdminCreateMediaCoverageBody
): Promise<MediaCoverageOut> {
  return apiFetch<MediaCoverageOut>("/admin/media-coverage", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

/** Admin: list media coverage entries. */
export async function adminListMediaCoverage(params?: {
  type?: string;
  locale?: string;
  is_published?: boolean;
  limit?: number;
  cursor?: string;
}): Promise<MediaCoverageListResponse> {
  const qs = new URLSearchParams();
  if (params?.type) qs.set("type", params.type);
  if (params?.locale) qs.set("locale", params.locale);
  if (params?.is_published !== undefined)
    qs.set("is_published", String(params.is_published));
  if (params?.limit) qs.set("limit", String(params.limit));
  if (params?.cursor) qs.set("cursor", params.cursor);
  const query = qs.toString() ? `?${qs.toString()}` : "";
  return apiFetch<MediaCoverageListResponse>(`/admin/media-coverage${query}`);
}

/** Admin: update a media coverage entry. */
export async function adminPatchMediaCoverage(
  id: string,
  body: AdminPatchMediaCoverageBody
): Promise<MediaCoverageOut> {
  return apiFetch<MediaCoverageOut>(`/admin/media-coverage/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

/** Admin: delete a media coverage entry. */
export async function adminDeleteMediaCoverage(id: string): Promise<void> {
  return apiFetch<void>(`/admin/media-coverage/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}

/** Public: list published media coverage. */
export async function fetchMediaCoverage(params?: {
  type?: string;
  locale?: string;
  artist_id?: string;
  limit?: number;
  cursor?: string;
}): Promise<MediaCoverageListResponse> {
  const qs = new URLSearchParams();
  if (params?.type) qs.set("type", params.type);
  if (params?.locale) qs.set("locale", params.locale);
  if (params?.artist_id) qs.set("artist_id", params.artist_id);
  if (params?.limit) qs.set("limit", String(params.limit));
  if (params?.cursor) qs.set("cursor", params.cursor);
  const query = qs.toString() ? `?${qs.toString()}` : "";
  return apiFetch<MediaCoverageListResponse>(`/media-coverage${query}`, {
    auth: false,
  });
}

/** Public: fetch featured media coverage (storyhub hero grid). */
export async function fetchFeaturedMediaCoverage(
  locale: string = "ko",
  limit: number = 3
): Promise<MediaCoverageOut[]> {
  const qs = new URLSearchParams({ locale, limit: String(limit) });
  return apiFetch<MediaCoverageOut[]>(`/media-coverage/featured?${qs.toString()}`, {
    auth: false,
  });
}

// ─── C-5 Newsletter ───────────────────────────────────────────────────────────

export type NewsletterIssueOut = {
  id: string;
  issue_date: string; // "YYYY-MM-DD"
  subject: string;
  body_markdown: string;
  body_html: string;
  locale: string;
  featured_artist_id: string | null;
  new_top_artists: string[];
  new_posts_highlight: string[];
  media_coverage_ids: string[];
  status: "draft" | "sending" | "sent" | "failed";
  sent_count: number;
  failed_count: number;
  sent_at: string | null;
  created_by_admin_id: string;
  created_at: string;
  updated_at: string;
};

export type NewsletterPreferencesOut = {
  user_id: string;
  is_subscribed: boolean;
  frequency: "weekly" | "biweekly" | "monthly" | "never";
  preferred_locale: string;
  last_sent_at: string | null;
  created_at: string;
  updated_at: string;
};

/** Admin: auto-compose a newsletter draft from live data. */
export async function adminComposeNewsletterIssue(params: {
  issue_date: string; // "YYYY-MM-DD"
  locale: string;
}): Promise<NewsletterIssueOut> {
  const qs = new URLSearchParams({
    issue_date: params.issue_date,
    locale: params.locale,
  });
  return apiFetch<NewsletterIssueOut>(
    `/admin/newsletter/issues/compose?${qs.toString()}`,
    { method: "POST" }
  );
}

/** Admin: list newsletter issues. */
export async function adminListNewsletterIssues(params?: {
  status?: string;
  locale?: string;
  limit?: number;
}): Promise<NewsletterIssueOut[]> {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
  if (params?.locale) qs.set("locale", params.locale);
  if (params?.limit) qs.set("limit", String(params.limit));
  return apiFetch<NewsletterIssueOut[]>(
    `/admin/newsletter/issues?${qs.toString()}`
  );
}

/** Admin: edit a newsletter issue body/subject/status. */
export async function adminPatchNewsletterIssue(
  id: string,
  body: { subject?: string; body_markdown?: string; status?: string }
): Promise<NewsletterIssueOut> {
  return apiFetch<NewsletterIssueOut>(
    `/admin/newsletter/issues/${encodeURIComponent(id)}`,
    { method: "PATCH", body: JSON.stringify(body) }
  );
}

/** Admin: transition a draft newsletter issue to sending. */
export async function adminSendNewsletterIssue(
  id: string
): Promise<NewsletterIssueOut> {
  return apiFetch<NewsletterIssueOut>(
    `/admin/newsletter/issues/${encodeURIComponent(id)}/send`,
    { method: "POST" }
  );
}

/** User (me): fetch own newsletter preferences. */
export async function fetchMyNewsletterPreferences(): Promise<NewsletterPreferencesOut> {
  return apiFetch<NewsletterPreferencesOut>("/me/newsletter/preferences");
}

/** User (me): update newsletter preferences (opt-in/out, frequency, locale). */
export async function patchMyNewsletterPreferences(body: {
  is_subscribed?: boolean;
  frequency?: "weekly" | "biweekly" | "monthly" | "never";
  preferred_locale?: string;
}): Promise<NewsletterPreferencesOut> {
  return apiFetch<NewsletterPreferencesOut>("/me/newsletter/preferences", {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

/** Public: 1-click unsubscribe via token from email link (no auth). */
export async function newsletterUnsubscribe(
  token: string
): Promise<{ unsubscribed: boolean; user_id: string }> {
  return apiFetch<{ unsubscribed: boolean; user_id: string }>(
    `/newsletter/unsubscribe?token=${encodeURIComponent(token)}`,
    { auth: false }
  );
}

// ─── B'-2 DM Messaging ──────────────────────────────────────────────────────

export type ConversationView = {
  id: string;
  other_user_id: string;
  last_message_at: string | null;
  created_at: string;
  closed_by_admin: boolean;
  last_message_preview: string | null;
};

export type MessageView = {
  id: string;
  conversation_id: string;
  sender_id: string;
  body: string;
  created_at: string;
  read_at: string | null;
  edited_at: string | null;
  deleted_at: string | null;
};

export type ConversationListResponse = {
  data: ConversationView[];
  next_cursor: string | null;
};

export type MessageListResponse = {
  data: MessageView[];
  next_cursor: string | null;
};

/** Start a conversation with target_user_id, or return the existing one. */
export async function startConversation(
  targetUserId: string
): Promise<ConversationView> {
  return apiFetch<ConversationView>("/conversations", {
    method: "POST",
    body: JSON.stringify({ target_user_id: targetUserId }),
  });
}

/** List current user's conversations (cursor-paginated). */
export async function listConversations(
  cursor?: string | null,
  limit = 20
): Promise<ConversationListResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (cursor) params.set("cursor", cursor);
  return apiFetch<ConversationListResponse>(`/me/conversations?${params}`);
}

/** List messages in a conversation (participants only). */
export async function listMessages(
  conversationId: string,
  cursor?: string | null,
  limit = 30
): Promise<MessageListResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (cursor) params.set("cursor", cursor);
  return apiFetch<MessageListResponse>(
    `/conversations/${conversationId}/messages?${params}`
  );
}

/** Send a message. */
export async function sendMessage(
  conversationId: string,
  body: string
): Promise<MessageView> {
  return apiFetch<MessageView>(`/conversations/${conversationId}/messages`, {
    method: "POST",
    body: JSON.stringify({ body }),
  });
}

/** Edit own message (within 5-minute window). */
export async function editMessage(
  conversationId: string,
  messageId: string,
  body: string
): Promise<MessageView> {
  return apiFetch<MessageView>(
    `/conversations/${conversationId}/messages/${messageId}`,
    {
      method: "PATCH",
      body: JSON.stringify({ body }),
    }
  );
}

/** Soft-delete own message. */
export async function deleteMessage(
  conversationId: string,
  messageId: string
): Promise<MessageView> {
  return apiFetch<MessageView>(
    `/conversations/${conversationId}/messages/${messageId}`,
    { method: "DELETE" }
  );
}

/** Mark all received messages in conversation as read. */
export async function markConversationRead(
  conversationId: string
): Promise<{ marked_read: number }> {
  return apiFetch<{ marked_read: number }>(
    `/conversations/${conversationId}/read`,
    { method: "POST" }
  );
}

/** Report a conversation for abuse. */
export async function reportConversation(
  conversationId: string,
  reason: string
): Promise<{ reported: boolean; conversation_id: string }> {
  return apiFetch<{ reported: boolean; conversation_id: string }>(
    `/conversations/${conversationId}/report`,
    {
      method: "POST",
      body: JSON.stringify({ reason }),
    }
  );
}

// ─── B'-3: Push Notification Preferences ─────────────────────────────────────

export type NotificationPreferencesView = {
  user_id: string;
  push_enabled: boolean;
  email_enabled: boolean;
  push_per_type: Record<string, boolean>;
  email_per_type: Record<string, boolean>;
  digest_frequency: "weekly" | "biweekly" | "monthly" | "never";
  updated_at: string | null;
};

export type NotificationPreferencesPatch = {
  push_enabled?: boolean;
  email_enabled?: boolean;
  push_per_type?: Record<string, boolean>;
  email_per_type?: Record<string, boolean>;
  digest_frequency?: "weekly" | "biweekly" | "monthly" | "never";
};

export type DeviceTokenView = {
  id: string;
  user_id: string;
  platform: "fcm" | "apns";
  device_id: string | null;
  last_active_at: string | null;
  created_at: string | null;
};

export type DeviceRegisterInput = {
  token: string;
  platform: "fcm" | "apns";
  device_id?: string | null;
};

/** GET /me/notifications/preferences — Fetch notification preferences. */
export async function fetchNotificationPreferences(): Promise<NotificationPreferencesView> {
  return apiFetch<NotificationPreferencesView>("/me/notifications/preferences");
}

/** PATCH /me/notifications/preferences — Update notification preferences. */
export async function patchNotificationPreferences(
  body: NotificationPreferencesPatch
): Promise<NotificationPreferencesView> {
  return apiFetch<NotificationPreferencesView>("/me/notifications/preferences", {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

/** POST /me/devices — Register a push device token. */
export async function registerDeviceToken(
  input: DeviceRegisterInput
): Promise<DeviceTokenView> {
  return apiFetch<DeviceTokenView>("/me/devices", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

/** DELETE /me/devices/{id} — Revoke a push device token. */
export async function revokeDeviceToken(
  deviceId: string
): Promise<{ deleted: boolean; id: string }> {
  return apiFetch<{ deleted: boolean; id: string }>(
    `/me/devices/${encodeURIComponent(deviceId)}`,
    { method: "DELETE" }
  );
}

// ─── Phase 10 K-7: AI 큐레이션 컬렉션 ───────────────────────────────────────

export type AiCollectionItem = {
  id: string;
  week_start: string | null;
  theme: string;
  title: string | null;
  description: string | null;
  cover_image_url: string | null;
  post_count: number;
  published_at: string | null;
};

export type AiCollectionPost = {
  position: number;
  post_id: string;
  title: string | null;
  thumbnail_url: string | null;
  author: {
    id: string;
    name: string | null;
    avatar_url: string | null;
  };
};

export type AiCollectionDetail = {
  id: string;
  week_start: string | null;
  theme: string;
  title: string | null;
  description: string | null;
  cover_image_url: string | null;
  published_at: string | null;
  posts: AiCollectionPost[];
};

export type AiCollectionsResponse = {
  items: AiCollectionItem[];
  total: number;
  page: number;
  limit: number;
};

/** GET /ai-collections — 활성 AI 큐레이션 컬렉션 목록 (공개). */
export async function fetchCollections(params: {
  page?: number;
  limit?: number;
  locale?: string;
}): Promise<AiCollectionsResponse> {
  const q = new URLSearchParams();
  if (params.page) q.set("page", String(params.page));
  if (params.limit) q.set("limit", String(params.limit));
  if (params.locale) q.set("locale", params.locale);
  const qs = q.toString();
  // auth: false — 공개 엔드포인트, 인증 토큰 불필요
  return apiFetch<AiCollectionsResponse>(
    `/ai-collections${qs ? `?${qs}` : ""}`,
    { auth: false }
  );
}

/** GET /ai-collections/{id} — 컬렉션 상세 + 작품 리스트. */
export async function fetchCollectionDetail(
  id: string,
  locale?: string
): Promise<AiCollectionDetail> {
  const q = locale ? `?locale=${encodeURIComponent(locale)}` : "";
  // auth: false — 공개 엔드포인트, 인증 토큰 불필요
  return apiFetch<AiCollectionDetail>(
    `/ai-collections/${encodeURIComponent(id)}${q}`,
    { auth: false }
  );
}
