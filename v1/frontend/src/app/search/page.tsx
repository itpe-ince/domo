"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { PostCard } from "@/components/PostCard";
import {
  fetchExplore,
  PostView,
  searchPosts,
  searchUsers,
  UserSearchResult,
} from "@/lib/api";
import { useRecentSearches } from "@/lib/useRecentSearches";

type Tab = "artists" | "artworks" | "posts";
type SortOption = "latest" | "popular" | "ending_soon";

const TABS: { key: Tab; label: string }[] = [
  { key: "artists", label: "작가" },
  { key: "artworks", label: "작품" },
  { key: "posts", label: "포스트" },
];

const GENRES = [
  null,
  "painting",
  "drawing",
  "photography",
  "sculpture",
  "mixed_media",
];

export default function SearchPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
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

  const { items: recent, add, remove } = useRecentSearches();
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setInputValue(q);
    if (q.length >= 2) void doSearch(q, tab);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, tab, roleFilter, genreFilter, sortOption]);

  async function doSearch(query: string, currentTab: Tab) {
    setLoading(true);
    setError(null);
    try {
      if (currentTab === "artists") {
        setUsers(
          await searchUsers(query, {
            role: roleFilter ?? undefined,
            limit: 20,
          })
        );
        setPostResults([]);
      } else if (currentTab === "artworks") {
        setPostResults(
          await searchPosts(query, {
            type: "product",
            genre: genreFilter ?? undefined,
            sort: sortOption,
            limit: 20,
          })
        );
        setUsers([]);
      } else {
        setPostResults(
          await searchPosts(query, {
            type: "general",
            sort: sortOption === "ending_soon" ? "latest" : sortOption,
            limit: 20,
          })
        );
        setUsers([]);
      }
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
    router.push(`/search?q=${encodeURIComponent(trimmed)}&tab=${tab}`);
  }

  function switchTab(t: Tab) {
    // Reset filters when switching tabs
    setRoleFilter(null);
    setGenreFilter(null);
    setSortOption("latest");
    if (!q) return;
    router.push(`/search?q=${encodeURIComponent(q)}&tab=${t}`);
  }

  const hasQuery = q.length >= 2;
  const isEmpty =
    hasQuery &&
    !loading &&
    !error &&
    users.length === 0 &&
    postResults.length === 0;

  return (
    <main className="flex-1 min-w-0 max-w-3xl mx-auto">
      {/* Search input */}
      <div className="sticky top-0 z-20 bg-background/80 backdrop-blur-md border-b border-border">
        <form onSubmit={handleSubmit} className="px-4 py-3">
          <div className="relative">
            <input
              ref={inputRef}
              type="text"
              role="searchbox"
              aria-label="검색"
              placeholder="검색어를 입력하세요"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
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

        {/* Tabs */}
        {hasQuery && (
          <div className="flex">
            {TABS.map((t) => (
              <button
                key={t.key}
                onClick={() => switchTab(t.key)}
                className={`flex-1 py-2.5 text-sm font-semibold transition-colors relative ${
                  tab === t.key
                    ? "text-text-primary"
                    : "text-text-muted hover:bg-surface-hover"
                }`}
              >
                {t.label}
                {tab === t.key && (
                  <span className="absolute bottom-0 left-1/2 -translate-x-1/2 w-12 h-1 rounded-full bg-primary" />
                )}
              </button>
            ))}
          </div>
        )}

        {/* Filters — tab-specific */}
        {hasQuery && (
          <div className="px-4 py-2 border-t border-border space-y-2">
            {/* Artists tab: role filter */}
            {tab === "artists" && (
              <div className="flex gap-2">
                {[
                  { value: null, label: "전체" },
                  { value: "artist", label: "작가만" },
                ].map((opt) => (
                  <button
                    key={opt.value ?? "all"}
                    onClick={() => setRoleFilter(opt.value)}
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
            )}

            {/* Artworks tab: genre chips + sort */}
            {tab === "artworks" && (
              <>
                <div className="flex gap-2 overflow-x-auto">
                  {GENRES.map((g) => (
                    <button
                      key={g ?? "all-g"}
                      onClick={() => setGenreFilter(g)}
                      className={`px-3 py-1 rounded-full text-xs whitespace-nowrap transition-colors ${
                        genreFilter === g
                          ? "bg-primary text-background font-semibold"
                          : "bg-surface text-text-secondary hover:bg-surface-hover"
                      }`}
                    >
                      {g ?? "전체"}
                    </button>
                  ))}
                </div>
                <div className="flex gap-2">
                  {(
                    [
                      { value: "latest", label: "최신순" },
                      { value: "popular", label: "인기순" },
                      { value: "ending_soon", label: "마감임박" },
                    ] as { value: SortOption; label: string }[]
                  ).map((opt) => (
                    <button
                      key={opt.value}
                      onClick={() => setSortOption(opt.value)}
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
              </>
            )}

            {/* Posts tab: sort */}
            {tab === "posts" && (
              <div className="flex gap-2">
                {(
                  [
                    { value: "latest", label: "최신순" },
                    { value: "popular", label: "인기순" },
                  ] as { value: SortOption; label: string }[]
                ).map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => setSortOption(opt.value)}
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
        {/* No query — show recent searches */}
        {!hasQuery && (
          <div>
            {recent.length > 0 && (
              <div className="mb-6">
                <h2 className="text-sm font-semibold text-text-muted mb-3">
                  최근 검색
                </h2>
                <div className="flex flex-wrap gap-2">
                  {recent.map((r) => (
                    <button
                      key={r}
                      onClick={() => {
                        add(r);
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
              검색어를 입력해 작가, 작품, 포스트를 찾아보세요.
            </div>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="space-y-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="card p-4 animate-pulse">
                <div className="h-4 w-2/3 bg-surface-hover rounded mb-2" />
                <div className="h-3 w-1/2 bg-surface-hover rounded" />
              </div>
            ))}
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="card border-danger p-4 text-danger text-sm">
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
                      팔로워 {u.follower_count}
                    </div>
                  </div>
                </Link>
                <button className="px-4 py-1.5 rounded-full text-xs font-semibold bg-primary text-background hover:bg-primary-hover transition-colors flex-shrink-0">
                  팔로우
                </button>
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
                <PostCard key={post.id} post={post} />
              ))}
            </div>
          )}
      </div>
    </main>
  );
}

function EmptyState({ q }: { q: string }) {
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
        <p className="text-sm text-text-muted mb-2">비슷한 키워드:</p>
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
            추천 작가
          </h3>
          <ul className="space-y-3">
            {artists.map((a) => (
              <li key={a.id}>
                <Link
                  href={`/users/${a.id}`}
                  className="flex items-center gap-3"
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
              </li>
            ))}
          </ul>
        </div>
      )}

      <Link
        href="/explore"
        className="inline-block mt-6 bg-primary text-background hover:bg-primary-hover rounded-full font-bold px-6 py-2.5 transition-colors"
      >
        탐색으로 이동
      </Link>
    </div>
  );
}
