"use client";

/**
 * FollowingContext — single source of truth for "who does the current user
 * follow?" across the app. Backed by GET /me/following/ids; mutations call
 * POST/DELETE /users/{id}/follow with optimistic updates and rollback on
 * failure. Re-loads on AUTH_CHANGED_EVENT so login/logout flips state.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  AUTH_CHANGED_EVENT,
  ApiClientError,
  fetchMyFollowingIds,
  followArtist,
  tokenStore,
  unfollowArtist,
} from "@/lib/api";

type FollowingContextValue = {
  ready: boolean;
  isFollowing: (userId: string) => boolean;
  follow: (userId: string) => Promise<void>;
  unfollow: (userId: string) => Promise<void>;
};

const FollowingContext = createContext<FollowingContextValue>({
  ready: false,
  isFollowing: () => false,
  follow: async () => {},
  unfollow: async () => {},
});

export function FollowingProvider({ children }: { children: React.ReactNode }) {
  const [ids, setIds] = useState<Set<string>>(new Set());
  const [ready, setReady] = useState(false);
  // 동시 follow/unfollow 호출 시 마지막 호출만 신뢰하기 위한 토큰
  const tokenRef = useRef(0);

  const load = useCallback(async () => {
    if (!tokenStore.get()) {
      setIds(new Set());
      setReady(true);
      return;
    }
    try {
      const list = await fetchMyFollowingIds();
      setIds(new Set(list));
    } catch {
      setIds(new Set());
    } finally {
      setReady(true);
    }
  }, []);

  useEffect(() => {
    void load();
    const handler = () => {
      setReady(false);
      void load();
    };
    window.addEventListener(AUTH_CHANGED_EVENT, handler);
    return () => window.removeEventListener(AUTH_CHANGED_EVENT, handler);
  }, [load]);

  const isFollowing = useCallback((userId: string) => ids.has(userId), [ids]);

  const follow = useCallback(async (userId: string) => {
    const myToken = ++tokenRef.current;
    // 낙관적 추가
    setIds((prev) => {
      if (prev.has(userId)) return prev;
      const next = new Set(prev);
      next.add(userId);
      return next;
    });
    try {
      await followArtist(userId);
    } catch (e) {
      // 롤백 — 단, 더 최신 호출이 있으면 그 결과를 존중
      if (tokenRef.current === myToken) {
        setIds((prev) => {
          if (!prev.has(userId)) return prev;
          const next = new Set(prev);
          next.delete(userId);
          return next;
        });
      }
      if (e instanceof ApiClientError) throw e;
      throw new Error("Follow failed");
    }
  }, []);

  const unfollow = useCallback(async (userId: string) => {
    const myToken = ++tokenRef.current;
    setIds((prev) => {
      if (!prev.has(userId)) return prev;
      const next = new Set(prev);
      next.delete(userId);
      return next;
    });
    try {
      await unfollowArtist(userId);
    } catch (e) {
      if (tokenRef.current === myToken) {
        setIds((prev) => {
          if (prev.has(userId)) return prev;
          const next = new Set(prev);
          next.add(userId);
          return next;
        });
      }
      if (e instanceof ApiClientError) throw e;
      throw new Error("Unfollow failed");
    }
  }, []);

  const value = useMemo(
    () => ({ ready, isFollowing, follow, unfollow }),
    [ready, isFollowing, follow, unfollow]
  );

  return (
    <FollowingContext.Provider value={value}>
      {children}
    </FollowingContext.Provider>
  );
}

export function useFollowing() {
  return useContext(FollowingContext);
}
