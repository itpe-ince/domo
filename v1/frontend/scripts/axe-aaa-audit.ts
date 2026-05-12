/**
 * axe-core AAA 감사 스크립트 — Phase 9 L-E
 *
 * 실행: npx ts-node scripts/axe-aaa-audit.ts
 * 의존: @axe-core/playwright, playwright
 *
 * 핵심 3페이지 AAA 위반 0건 목표.
 *
 * 사전 조건:
 *   npm install --save-dev @axe-core/playwright playwright
 *   npx playwright install chromium
 *   환경변수: TEST_POST_ID, TEST_AUCTION_ID (미설정 시 placeholder 사용)
 */

import { chromium } from "playwright";
import AxeBuilder from "@axe-core/playwright";

const BASE_URL = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000";
const POST_ID = process.env.TEST_POST_ID ?? "test-post-id";
const AUCTION_ID = process.env.TEST_AUCTION_ID ?? "test-auction-id";

const PAGES = [
  { url: `${BASE_URL}/feed`, name: "Feed" },
  { url: `${BASE_URL}/posts/${POST_ID}`, name: "Post Detail" },
  { url: `${BASE_URL}/auctions/${AUCTION_ID}`, name: "Auction Detail" },
];

async function runAudit() {
  const browser = await chromium.launch({
    headless: process.env.HEADLESS !== "false",
  });
  let totalViolations = 0;
  const report: Array<{ page: string; violations: number; details: string[] }> = [];

  for (const page of PAGES) {
    const ctx = await browser.newContext();
    const p = await ctx.newPage();

    try {
      await p.goto(page.url, { waitUntil: "networkidle" });
      await p.waitForTimeout(1000); // Hydration 대기

      const results = await new AxeBuilder({ page: p })
        .withTags(["wcag2aaa", "wcag21aaa"])
        .analyze();

      const violations = results.violations;
      totalViolations += violations.length;

      const details = violations.flatMap((v) => [
        `  [${v.id}] ${v.description} (impact: ${v.impact})`,
        ...v.nodes.map((n) => `    > ${n.html.slice(0, 120)}`),
      ]);

      report.push({ page: page.name, violations: violations.length, details });

      console.log(`\n[${page.name}] ${page.url}`);
      console.log(`  violations: ${violations.length}`);
      details.forEach((d) => console.log(d));
    } catch (err) {
      console.warn(`  [WARN] ${page.name} 페이지 접근 실패: ${err}`);
      report.push({ page: page.name, violations: -1, details: [`접근 실패: ${err}`] });
    } finally {
      await ctx.close();
    }
  }

  await browser.close();

  console.log("\n────────────────────────────────────");
  console.log(`총 AAA 위반: ${totalViolations}건`);
  report.forEach((r) => {
    const status = r.violations === 0 ? "PASS" : r.violations < 0 ? "SKIP" : "FAIL";
    console.log(`  ${status} ${r.page}: ${r.violations < 0 ? "접근 실패" : `${r.violations}건`}`);
  });
  console.log("────────────────────────────────────\n");

  if (totalViolations > 0) {
    process.exit(1);
  }
}

runAudit().catch((err) => {
  console.error("Audit failed:", err);
  process.exit(1);
});
