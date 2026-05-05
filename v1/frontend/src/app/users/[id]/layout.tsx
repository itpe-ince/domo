/**
 * /users/[id]/layout.tsx — G'-6 Metadata wrapper
 *
 * Server component: exports generateMetadata for artist profile pages.
 * The opengraph-image.tsx in this segment is auto-inferred by Next.js.
 *
 * This layout is non-visual — it only provides metadata and passes children
 * through, so it doesn't affect the existing "use client" page.tsx rendering.
 */

import type { Metadata } from "next";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3710/v1";

interface UserMeta {
  display_name?: string;
  country_code?: string | null;
  role?: string;
  artist_profile?: { statement?: string | null } | null;
}

async function fetchUserMeta(id: string): Promise<UserMeta | null> {
  try {
    const res = await fetch(`${API_BASE}/users/${id}`, {
      next: { revalidate: 300 },
    });
    if (!res.ok) return null;
    const json = await res.json() as { data?: UserMeta };
    return json.data ?? null;
  } catch {
    return null;
  }
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const user = await fetchUserMeta(id);

  const name = user?.display_name ?? "작가 프로필";
  const country = user?.country_code ? ` · ${user.country_code}` : "";
  const statement = user?.artist_profile?.statement;

  return {
    title: `@${name} | Domo Lounge`,
    description:
      statement
        ? statement.slice(0, 150)
        : `${name}의 작가 프로필${country} — Domo 글로벌 신진작가 플랫폼`,
    openGraph: {
      title: `@${name}`,
      description: statement
        ? statement.slice(0, 150)
        : `${name}의 작가 프로필${country}`,
      // images: auto-inferred from opengraph-image.tsx in this segment
    },
    twitter: {
      card: "summary_large_image",
      title: `@${name} | Domo Lounge`,
      description: statement
        ? statement.slice(0, 150)
        : `${name}의 작가 프로필${country}`,
      // images: auto-inferred from opengraph-image.tsx in this segment
    },
  };
}

export default function UserLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
