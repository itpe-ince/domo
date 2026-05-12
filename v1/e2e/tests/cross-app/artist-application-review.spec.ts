import { expect, request, test } from "@playwright/test";
import { e2eEnv } from "../../support/env";

const REVIEW_USER_EMAIL =
  process.env.E2E_REVIEW_USER_EMAIL ?? "e2e-review@domo.example.com";
const REVIEW_USER_PASSWORD =
  process.env.E2E_REVIEW_USER_PASSWORD ?? "DomoE2EReview!2026";
const REVIEW_SCHOOL = "Domo E2E Review School";

async function getReviewUserRole(): Promise<string> {
  const api = await request.newContext({
    extraHTTPHeaders: { "Content-Type": "application/json" },
  });

  try {
    const login = await api.post(
      `${e2eEnv.apiUrl.replace(/\/+$/, "")}/auth/login/email`,
      {
        data: {
          email: REVIEW_USER_EMAIL,
          password: REVIEW_USER_PASSWORD,
        },
      }
    );
    expect(login.ok()).toBeTruthy();
    const loginJson = await login.json();
    const accessToken = loginJson.data.tokens.access_token as string;

    const me = await api.get(`${e2eEnv.apiUrl.replace(/\/+$/, "")}/auth/me`, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });
    expect(me.ok()).toBeTruthy();
    const meJson = await me.json();
    return meJson.data.role as string;
  } finally {
    await api.dispose();
  }
}

test.describe("artist application cross-app flow", () => {
  test("admin approves a pending artist application and user becomes artist", async ({
    page,
  }) => {
    await page.goto("/applications");

    await expect(page.getByRole("heading", { name: "작가 심사 승인" })).toBeVisible();
    await expect(page.getByText(REVIEW_SCHOOL)).toBeVisible();

    const applicationCard = page
      .locator(".card")
      .filter({ hasText: REVIEW_SCHOOL })
      .first();
    await applicationCard
      .getByPlaceholder("심사 메모 (선택)")
      .fill("E2E approval");
    await applicationCard.getByRole("button", { name: "승인" }).click();

    await expect(applicationCard).toHaveCount(0);
    await expect.poll(getReviewUserRole).toBe("artist");
  });
});
