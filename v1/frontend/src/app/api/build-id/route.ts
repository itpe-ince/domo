/**
 * GET /api/build-id — returns the current server build identifier.
 *
 * BuildVersionWatcher (client) polls this and triggers a reload toast when
 * the value differs from the client's embedded NEXT_PUBLIC_BUILD_ID. This
 * detects "you have an old tab open after we redeployed" and prevents the
 * silent skeleton-stuck-forever bug class (plan C2).
 *
 * Implementation notes:
 *   - We read the same env var that next.config.mjs uses in generateBuildId.
 *     If absent, we read the standalone build's BUILD_ID file as a fallback
 *     (works on Vercel / Docker standalone deploys).
 *   - Force-dynamic + no-store: must never be cached, or stale builds would
 *     never be detected.
 */

import { promises as fs } from "node:fs";
import path from "node:path";
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const revalidate = 0;

let cachedBuildId: string | null = null;

async function readBuildIdFile(): Promise<string | null> {
  // Next.js writes the buildId to .next/BUILD_ID on every build. In a
  // standalone deploy this lives at ./.next/BUILD_ID relative to the
  // process cwd of the server.
  const candidates = [
    path.join(process.cwd(), ".next", "BUILD_ID"),
    path.join(process.cwd(), "..", ".next", "BUILD_ID"),
  ];
  for (const p of candidates) {
    try {
      const v = (await fs.readFile(p, "utf8")).trim();
      if (v) return v;
    } catch {
      // try next
    }
  }
  return null;
}

async function resolveBuildId(): Promise<string> {
  if (cachedBuildId) return cachedBuildId;
  const envId = process.env.NEXT_PUBLIC_BUILD_ID;
  if (envId) {
    cachedBuildId = envId;
    return envId;
  }
  const fileId = await readBuildIdFile();
  cachedBuildId = fileId ?? "unknown";
  return cachedBuildId;
}

export async function GET() {
  const buildId = await resolveBuildId();
  return NextResponse.json(
    { buildId },
    {
      headers: {
        "Cache-Control": "no-store, no-cache, must-revalidate",
        Pragma: "no-cache",
      },
    }
  );
}
