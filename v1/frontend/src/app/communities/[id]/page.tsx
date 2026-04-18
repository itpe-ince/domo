"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useI18n } from "@/i18n";
import { apiFetch } from "@/lib/api";
import { useMe } from "@/lib/useMe";

type CommunityDetail = {
  id: string; name: string; type: string; description: string | null;
  member_count: number;
};

type CommunityPostItem = {
  id: string;
  author: { id: string; display_name: string; avatar_url: string | null };
  content: string;
  created_at: string;
};

export default function CommunityDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { me } = useMe();
  const { t } = useI18n();
  const [community, setCommunity] = useState<CommunityDetail | null>(null);
  const [posts, setPosts] = useState<CommunityPostItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [joined, setJoined] = useState(false);
  const [newPost, setNewPost] = useState("");
  const [posting, setPosting] = useState(false);

  useEffect(() => { void load(); }, [id]);

  async function load() {
    setLoading(true);
    try {
      const c = await apiFetch<CommunityDetail>(`/communities/${id}`, { auth: false });
      setCommunity(c);
      const p = await apiFetch<CommunityPostItem[]>(`/communities/${id}/posts`, { auth: false });
      setPosts(p);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }

  async function handleJoin() {
    try {
      await apiFetch(`/communities/${id}/join`, { method: "POST" });
      setJoined(true);
      void load();
    } catch { /* ignore */ }
  }

  async function handleLeave() {
    try {
      await apiFetch(`/communities/${id}/leave`, { method: "DELETE" });
      setJoined(false);
      void load();
    } catch { /* ignore */ }
  }

  async function handlePost() {
    if (!newPost.trim()) return;
    setPosting(true);
    try {
      await apiFetch(`/communities/${id}/posts`, {
        method: "POST",
        body: JSON.stringify({ content: newPost.trim() }),
      });
      setNewPost("");
      void load();
    } catch { /* ignore */ }
    finally { setPosting(false); }
  }

  if (loading) {
    return (
      <main className="flex-1 min-w-0 max-w-3xl mx-auto px-6 py-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 w-1/3 bg-surface-hover rounded" />
          <div className="h-4 w-2/3 bg-surface-hover rounded" />
          <div className="h-32 bg-surface-hover rounded" />
        </div>
      </main>
    );
  }

  if (!community) {
    return (
      <main className="flex-1 min-w-0 max-w-3xl mx-auto px-6 py-8 text-center text-text-muted">
        커뮤니티를 찾을 수 없습니다.
      </main>
    );
  }

  return (
    <main className="flex-1 min-w-0 max-w-3xl mx-auto px-6 py-8">
      <Link href="/communities" className="text-sm text-text-muted hover:text-primary mb-4 inline-block">
        ← 커뮤니티 목록
      </Link>

      <div className="card p-6 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">{community.name}</h1>
            {community.description && (
              <p className="text-text-muted text-sm mt-1">{community.description}</p>
            )}
            <p className="text-xs text-text-muted mt-2">{community.member_count} members</p>
          </div>
          {me && (
            joined ? (
              <button onClick={handleLeave} className="btn-secondary text-sm">탈퇴</button>
            ) : (
              <button onClick={handleJoin} className="btn-primary text-sm">가입</button>
            )
          )}
        </div>
      </div>

      {/* Write post */}
      {me && joined && (
        <div className="card p-4 mb-4 space-y-3">
          <textarea
            value={newPost}
            onChange={(e) => setNewPost(e.target.value)}
            placeholder="커뮤니티에 글을 남겨보세요..."
            rows={3}
            className="w-full bg-background border border-border rounded-lg px-4 py-2 text-sm focus:border-primary outline-none resize-none"
          />
          <div className="flex justify-end">
            <button
              onClick={handlePost}
              disabled={posting || !newPost.trim()}
              className="btn-primary text-sm disabled:opacity-50"
            >
              {posting ? "작성 중..." : "게시"}
            </button>
          </div>
        </div>
      )}

      {!me && (
        <div className="card p-4 mb-4 text-center text-text-muted text-sm">
          로그인 후 커뮤니티에 참여할 수 있습니다.
        </div>
      )}

      {/* Posts */}
      <div className="space-y-3">
        {posts.length === 0 ? (
          <div className="card p-8 text-center text-text-muted">아직 게시글이 없습니다.</div>
        ) : (
          posts.map((p) => (
            <div key={p.id} className="card p-4">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-8 h-8 rounded-full bg-surface-hover flex items-center justify-center text-primary font-bold text-sm flex-shrink-0">
                  {p.author.avatar_url ? (
                    <img src={p.author.avatar_url} alt="" className="w-full h-full rounded-full object-cover" />
                  ) : (
                    p.author.display_name.charAt(0).toUpperCase()
                  )}
                </div>
                <div>
                  <span className="text-sm font-semibold">@{p.author.display_name}</span>
                  <span className="text-xs text-text-muted ml-2">
                    {new Date(p.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
              <p className="text-sm text-text-primary whitespace-pre-wrap">{p.content}</p>
            </div>
          ))
        )}
      </div>
    </main>
  );
}
