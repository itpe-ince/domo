"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { PostCard } from "@/components/PostCard";
import { FollowButton } from "@/components/FollowButton";
import {
  fetchExplore,
  PostView,
  searchPosts,
  searchUsers,
  UserSearchResult,
} from "@/lib/api";
import { useI18n } from "@/i18n";
import { useRecentSearches } from "@/lib/useRecentSearches";
import { captureEvent } from "@/lib/analytics/capture";
import { useSearchHistory } from "@/lib/hooks/useSearchHistory";
import { parsePriceToCents } from "@/lib/format";

// Disable prerender — uses useSearchParams() which requires runtime
export const dynamic = "force-dynamic";

type Tab = "artists" | "artworks" | "posts";
type SortOption = "latest" | "popular" | "ending_soon";

const GENRES = [
  null,
  "painting",
  "drawing",
  "photography",
  "sculpture",
  "mixed_media",
];

export default function SearchPage() {
  return (
    <Suspense fallback={<div className="p-8 text-text-muted">로딩 중...</div>}>
      <SearchPageInner />
    </Suspense>
  );
}

function SearchPageInner() {
  const { t } = useI18n();
  const searchParams = useSearchParams();
  const router = useRouter();

  const TABS: { key: Tab; label: string }[] = [
    { key: "artists", label: t("search.tabArtists") },
    { key: "artworks", label: t("search.tabArtworks") },
    { key: "posts", label: t("search.tabPosts") },
  ];
  const q = searchParams.get("q") ?? "";
  const tabParam = searchParams.get("tab") as Tab | null;
  const tab: Tab =
    tabParam && TABS.some((t) => t.key === tabParam) ? tabParam : "artists";

  const [inputValue, setInputValue] = useState(q);
  const [users, setUsers] = useState<UserSearchResult[]>([]);
  const [postResults, setPostResults] = useState<PostView[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [roleFilter, setRoleFilter] = useState<string | null>(null);
  const [genreFilter, setGenreFilter] = useState<string | null>(null);
  const [sortOption, setSortOption] = useState<SortOption>("latest");
  const [priceMin, setPriceMin] = useState<string>("");
  const [priceMax, setPriceMax] = useState<string>("");
  const [regionFilter, setRegionFilter] = useState<string>("");
  const [activeOnly, setActiveOnly] = useState(false);

  // Search history dropdown
  const [inputFocused, setInputFocused] = useState(false);
  const { history, popular, removeEntry, clearAll } = useSearchHistory(10);

  const { items: recent, add, remove } = useRecentSearches();
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setInputValue(q);
    if (q.length >= 2) void doSearch(q, tab);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, tab, roleFilter, genreFilter, sortOption, priceMin, priceMax, regionFilter, activeOnly]);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node) &&
        inputRef.current !== e.target
      ) {
        setInputFocused(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  async function doSearch(query: string, currentTab: Tab) {
    setLoading(true);
    setError(null);
    try {
      let resultCount = 0;
      if (currentTab === "artists") {
        const results = await searchUsers(query, {
          role: roleFilter ?? undefined,
          limit: 20,
        });
        setUsers(results);
        setPostResults([]);
        resultCount = results.length;
      } else if (currentTab === "artworks") {
        // G'-10: user enters dollars in UI; API expects cents.
        const priceMinCents = priceMin ? parsePriceToCents(priceMin) ?? undefined : undefined;
        const priceMaxCents = priceMax ? parsePriceToCents(priceMax) ?? undefined : undefined;
        const results = await searchPosts(query, {
          type: "product",
          genre: genreFilter ?? undefined,
          sort: sortOption,
          limit: 20,
          price_min: priceMinCents,
          price_max: priceMaxCents,
        });
        setPostResults(results);
        setUsers([]);
        resultCount = results.length;
      } else {
        const results = await searchPosts(query, {
          type: "general",
          sort: sortOption === "ending_soon" ? "latest" : sortOption,
          limit: 20,
        });
        setPostResults(results);
        setUsers([]);
        resultCount = results.length;
      }
      // A-1: capture search event with actual result count
      captureEvent({ type: "search", query, results_count: resultCount });
    } catch (e) {
      setError(e instanceof Error ? e.message : "검색 실패");
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = inputValue.trim();
    if (trimmed.length < 2) return;
    add(trimmed);
    setInputFocused(false);
    router.push(`/search?q=${encodeURIComponent(trimmed)}&tab=${tab}`);
  }

  function runSearch(query: string) {
    const trimmed = query.trim();
    if (!trimmed) return;
    add(trimmed);
    setInputValue(trimmed);
    setInputFocused(false);
    router.push(`/search?q=${encodeURIComponent(trimmed)}&tab=${tab}`);
  }

  function switchTab(t: Tab) {
    // Reset filters when switching tabs
    setRoleFilter(null);
    setGenreFilter(null);
    setSortOption("latest");
    if (!q) return;
    captureEvent({ type: "search_filter_applied", filter_type: "tab" });
    router.push(`/search?q=${encodeURIComponent(q)}&tab=${t}`);
  }

  function handleSortChange(opt: SortOption) {
    setSortOption(opt);
    captureEvent({ type: "search_filter_applied", filter_type: "sort" });
  }

  function handleActiveToggle(val: boolean) {
    setActiveOnly(val);
    captureEvent({ type: "search_filter_applied", filter_type: "active" });
  }

  const hasQuery = q.length >= 2;
  const isEmpty =
    hasQuery &&
    !loading &&
    !error &&
    users.length === 0 &&
    postResults.length === 0;

  // Show dropdown: input focused + no active query OR input focused + has value but not searched
  const showDropdown = inputFocused && (history.length > 0 || popular.length > 0);

  return (
    <main className="flex-1 min-w-0 max-w-3xl mx-auto" aria-label={t("common.search")}>
      {/* Search input */}
      <div className="sticky top-0 z-20 bg-background/80 backdrop-blur-md border-b border-border">
        <div className="relative">
          <form onSubmit={handleSubmit} className="px-4 py-3" role="search">
            <div className="relative">
              <input
                ref={inputRef}
                type="text"
                role="searchbox"
                aria-label={t("common.search")}
                placeholder={t("search.placeholder")}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onFocus={() => setInputFocused(true)}
                className="w-full bg-surface rounded-full pl-10 pr-10 py-2.5 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-text-muted text-lg">
                🔍
              </span>
              {inputValue && (
                <button
                  type="button"
                  onClick={() => {
                    setInputValue("");
                    inputRef.current?.focus();
                  }}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary text-xs"
                  aria-label="지우기"
                >
                  ✕
                </button>
              )}
            </div>
          </form>

          {/* Search history / popular dropdown */}
          {showDropdown && (
            <div
              ref={dropdownRef}
              className="absolute left-0 right-0 top-full bg-background border border-border rounded-b-xl shadow-lg z-30 max-h-80 overflow-y-auto"
            >
              {/* Server history (logged-in) */}
              {history.length > 0 && (
                <div className="p-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-semibold text-text-muted">
                      {t("search.v2.recentHistory")}
                    </span>
                    <button
                      onClick={() => clearAll()}
                      className="text-xs text-text-muted hover:text-danger transition-colors"
                    >
                      {t("search.clearAll")}
                    </button>
                  </div>
                  {history.map((entry) => (
                    <div
                      key={entry.id}
                      className="flex items-center justify-between group hover:bg-surface-hover rounded-lg px-2 py-1.5 cursor-pointer"
                      onClick={() => {
                        captureEvent({ type: "search_history_click" });
                        runSearch(entry.query);
                      }}
                    >
                      <span className="text-sm text-text-primary">{entry.query}</span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          removeEntry(entry.id);
                        }}
                        className="text-text-muted opacity-0 group-hover:opacity-100 transition-opacity text-xs ml-2"
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* Popular searches */}
              {popular.length > 0 && (
                <div className="p-3 border-t border-border">
                  <span className="text-xs font-semibold text-text-muted block mb-2">
                    {t("search.v2.popular")}
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {popular.map((p) => (
                      <button
                        key={p.query}
                        onClick={() => {
                          captureEvent({ type: "search_popular_click" });
                          runSearch(p.query);
                        }}
                        className="bg-surface hover:bg-surface-hover text-text-primary text-xs px-3 py-1.5 rounded-full transition-colors"
                      >
                        {p.query}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Tabs */}
        {hasQuery && (
          <div className="flex" role="tablist" aria-label={t("common.search")}>
            {TABS.map((tab_item) => (
              <button
                key={tab_item.key}
                role="tab"
                aria-selected={tab === tab_item.key}
                onClick={() => switchTab(tab_item.key)}
                className={`flex-1 py-2.5 text-sm font-semibold transition-colors relative ${
                  tab === tab_item.key
                    ? "text-text-primary"
                    : "text-text-muted hover:bg-surface-hover"
                }`}
              >
                {tab_item.label}
                {tab === tab_item.key && (
                  <span className="absolute bottom-0 left-1/2 -translate-x-1/2 w-12 h-1 rounded-full bg-primary" />
                )}
              </button>
            ))}
          </div>
        )}

        {/* Filters — tab-specific */}
        {hasQuery && (
          <div className="px-4 py-2 border-t border-border space-y-2">
            {/* Artists tab: role filter + region */}
            {tab === "artists" && (
              <>
                <div className="flex gap-2">
                  {[
                    { value: null, label: t("explore.all") },
                    { value: "artist", label: t("search.artistOnly") },
                  ].map((opt) => (
                    <button
                      key={opt.value ?? "all"}
                      onClick={() => {
                        setRoleFilter(opt.value);
                        captureEvent({ type: "search_filter_applied", filter_type: "role" });
                      }}
                      className={`px-3 py-1 rounded-full text-xs transition-colors ${
                        roleFilter === opt.value
                          ? "bg-primary text-background font-semibold"
                          : "bg-surface text-text-secondary hover:bg-surface-hover"
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={regionFilter}
                    onChange={(e) => setRegionFilter(e.target.value)}
                    onBlur={() => {
                      if (regionFilter) {
                        captureEvent({ type: "search_filter_applied", filter_type: "region" });
                      }
                    }}
                    placeholder={t("search.v2.regionPlaceholder")}
                    className="flex-1 bg-surface text-text-primary text-xs rounded-full px-3 py-1.5 placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>
              </>
            )}

            {/* Artworks tab: genre chips + sort + price + active */}
            {tab === "artworks" && (
              <>
                <div className="flex gap-2 overflow-x-auto">
                  {GENRES.map((g) => (
                    <button
                      key={g ?? "all-g"}
                      onClick={() => {
                        setGenreFilter(g);
                        captureEvent({ type: "search_filter_applied", filter_type: "genre" });
                      }}
                      className={`px-3 py-1 rounded-full text-xs whitespace-nowrap transition-colors ${
                        genreFilter === g
                          ? "bg-primary text-background font-semibold"
                          : "bg-surface text-text-secondary hover:bg-surface-hover"
                      }`}
                    >
                      {g ?? t("explore.all")}
                    </button>
                  ))}
                </div>
                <div className="flex gap-2">
                  {(
                    [
                      { value: "latest", label: t("search.sortLatest") },
                      { value: "popular", label: t("search.sortPopular") },
                      { value: "ending_soon", label: t("search.sortEnding") },
                    ] as { value: SortOption; label: string }[]
                  ).map((opt) => (
                    <button
                      key={opt.value}
                      onClick={() => handleSortChange(opt.value)}
                      className={`px-3 py-1 rounded-full text-xs transition-colors ${
                        sortOption === opt.value
                          ? "bg-primary text-background font-semibold"
                          : "bg-surface text-text-secondary hover:bg-surface-hover"
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
                {/* Price range */}
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    value={priceMin}
                    onChange={(e) => {
                      setPriceMin(e.target.value);
                      captureEvent({ type: "search_filter_applied", filter_type: "price_range" });
                    }}
                    placeholder={t("search.v2.priceMin")}
                    min={0}
                    className="w-28 bg-surface text-text-primary text-xs rounded-full px-3 py-1.5 placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                  <span className="text-text-muted text-xs">–</span>
                  <input
                    type="number"
                    value={priceMax}
                    onChange={(e) => {
                      setPriceMax(e.target.value);
                      captureEvent({ type: "search_filter_applied", filter_type: "price_range" });
                    }}
                    placeholder={t("search.v2.priceMax")}
                    min={0}
                    className="w-28 bg-surface text-text-primary text-xs rounded-full px-3 py-1.5 placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                  <label className="flex items-center gap-1.5 text-xs text-text-secondary cursor-pointer">
                    <input
                      type="checkbox"
                      checked={activeOnly}
                      onChange={(e) => handleActiveToggle(e.target.checked)}
                      className="accent-primary"
                    />
                    {t("search.v2.activeOnly")}
                  </label>
                </div>
              </>
            )}

            {/* Posts tab: sort */}
            {tab === "posts" && (
              <div className="flex gap-2">
                {(
                  [
                    { value: "latest", label: t("search.sortLatest") },
                    { value: "popular", label: t("search.sortPopular") },
                  ] as { value: SortOption; label: string }[]
                ).map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => handleSortChange(opt.value)}
                    className={`px-3 py-1 rounded-full text-xs transition-colors ${
                      sortOption === opt.value
                        ? "bg-primary text-background font-semibold"
                        : "bg-surface text-text-secondary hover:bg-surface-hover"
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="p-4">
        {/* No query — show recent searches (localStorage) */}
        {!hasQuery && (
          <div>
            {recent.length > 0 && (
              <div className="mb-6">
                <h2 className="text-sm font-semibold text-text-muted mb-3">
                  {t("search.recentSearches")}
                </h2>
                <div className="flex flex-wrap gap-2">
                  {recent.map((r) => (
                    <button
                      key={r}
                      onClick={() => {
                        add(r);
                        captureEvent({ type: "search_history_click" });
                        router.push(
                          `/search?q=${encodeURIComponent(r)}&tab=${tab}`
                        );
                      }}
                      className="group flex items-center gap-1.5 bg-surface hover:bg-surface-hover rounded-full px-3 py-1.5 text-sm text-text-primary transition-colors"
                    >
                      {r}
                      <span
                        onClick={(e) => {
                          e.stopPropagation();
                          remove(r);
                        }}
                        className="text-text-muted group-hover:text-text-primary cursor-pointer"
                      >
                        ✕
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}
            <div className="text-center text-text-muted py-12">
              {t("search.searchHint")}
            </div>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="space-y-3" aria-busy="true" aria-label={t("common.loading")}>
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="card p-4 animate-pulse" aria-hidden="true">
                <div className="h-4 w-2/3 bg-surface-hover rounded mb-2" />
                <div className="h-3 w-1/2 bg-surface-hover rounded" />
              </div>
            ))}
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="card border-danger p-4 text-danger text-sm" role="alert">
            {error}
          </div>
        )}

        {/* Empty */}
        {isEmpty && <EmptyState q={q} />}

        {/* Artist results */}
        {!loading && !error && tab === "artists" && users.length > 0 && (
          <ul className="space-y-1">
            {users.map((u) => (
              <li
                key={u.id}
                className="flex items-center gap-3 p-3 rounded-lg hover:bg-surface-hover transition-colors"
              >
                <Link
                  href={`/users/${u.id}`}
                  className="flex items-center gap-3 flex-1 min-w-0"
                >
                  <div className="w-12 h-12 rounded-full bg-surface-hover flex items-center justify-center text-primary font-bold flex-shrink-0">
                    {u.avatar_url ? (
                      <img
                        src={u.avatar_url}
                        alt=""
                        className="w-full h-full rounded-full object-cover"
                      />
                    ) : (
                      u.display_name.charAt(0).toUpperCase()
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-semibold text-text-primary truncate">
                      @{u.display_name}
                    </div>
                    {u.bio && (
                      <div className="text-xs text-text-muted truncate">
                        {u.bio}
                      </div>
                    )}
                    <div className="text-xs text-text-muted mt-0.5">
                      {u.role === "artist" && (
                        <span className="text-primary mr-2">✓ Artist</span>
                      )}
                      {t("common.followers")} {u.follower_count}
                    </div>
                  </div>
                </Link>
                <div className="flex-shrink-0">
                  <FollowButton userId={u.id} size="sm" />
                </div>
              </li>
            ))}
          </ul>
        )}

        {/* Post / artwork results */}
        {!loading &&
          !error &&
          (tab === "artworks" || tab === "posts") &&
          postResults.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {postResults.map((post) => (
                <PostCard key={post.id} post={post} source="search" />
              ))}
            </div>
          )}
      </div>
    </main>
  );
}

function EmptyState({ q }: { q: string }) {
  const { t } = useI18n();
  const [artists, setArtists] = useState<
    Array<{
      id: string;
      display_name: string;
      avatar_url: string | null;
      role: string;
    }>
  >([]);
  const [suggestedTags, setSuggestedTags] = useState<string[]>([]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const posts = await fetchExplore({ type: "product", limit: 8 });
        if (cancelled) return;

        // Extract unique artists
        const unique = Array.from(
          new Map(
            posts
              .filter((p) => p.author.role === "artist")
              .map((p) => [p.author.id, p.author])
          ).values()
        ).slice(0, 3);
        setArtists(unique);

        // Extract popular tags from results
        const tagCounts = new Map<string, number>();
        for (const p of posts) {
          for (const t of p.tags ?? []) {
            tagCounts.set(t, (tagCounts.get(t) || 0) + 1);
          }
        }
        const top = [...tagCounts.entries()]
          .sort((a, b) => b[1] - a[1])
          .slice(0, 3)
          .map(([tag]) => tag);
        setSuggestedTags(
          top.length > 0 ? top : ["painting", "portrait", "sculpture"]
        );
      } catch {
        setSuggestedTags(["painting", "portrait", "sculpture"]);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="text-center py-8">
      <div className="text-4xl mb-4">🔍</div>
      <h2 className="text-lg font-bold mb-2">
        &ldquo;{q}&rdquo;에 대한 검색 결과가 없습니다.
      </h2>

      <div className="mb-6">
        <p className="text-sm text-text-muted mb-2">{t("search.similarKeywords")}</p>
        <div className="flex justify-center gap-2">
          {suggestedTags.map((tag) => (
            <Link
              key={tag}
              href={`/search?q=${encodeURIComponent(tag)}&tab=artworks`}
              className="bg-surface hover:bg-surface-hover rounded-full px-3 py-1 text-sm text-text-primary transition-colors"
            >
              {tag}
            </Link>
          ))}
        </div>
      </div>

      {artists.length > 0 && (
        <div className="card p-4 text-left max-w-sm mx-auto">
          <h3 className="text-sm font-semibold text-text-muted mb-3">
            {t("search.recommendedArtists")}
          </h3>
          <ul className="space-y-3">
            {artists.map((a) => (
              <li key={a.id} className="flex items-center gap-3">
                <Link
                  href={`/users/${a.id}`}
                  className="flex items-center gap-3 flex-1 min-w-0"
                >
                  <div className="w-10 h-10 rounded-full bg-surface-hover flex items-center justify-center text-primary font-bold flex-shrink-0">
                    {a.avatar_url ? (
                      <img
                        src={a.avatar_url}
                        alt=""
                        className="w-full h-full rounded-full object-cover"
                      />
                    ) : (
                      a.display_name.charAt(0).toUpperCase()
                    )}
                  </div>
                  <div className="text-sm font-semibold truncate">
                    @{a.display_name}
                  </div>
                </Link>
                <FollowButton userId={a.id} size="sm" />
              </li>
            ))}
          </ul>
        </div>
      )}

      <Link
        href="/explore"
        className="inline-block mt-6 bg-primary text-background hover:bg-primary-hover rounded-full font-bold px-6 py-2.5 transition-colors"
      >
        {t("search.goExplore")}
      </Link>
    </div>
  );
}
