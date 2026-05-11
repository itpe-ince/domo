import { expect, test } from "@playwright/test";

async function expectNoFatalRenderError(page: import("@playwright/test").Page) {
  await expect(page.locator("body")).toBeVisible();
  await expect(page.getByText(/Application error|Unhandled Runtime Error/i)).toHaveCount(0);
}

test.describe("user app smoke", () => {
  test("guest can open the landing page", async ({ page }) => {
    await page.goto("/");
    await expectNoFatalRenderError(page);
  });

  test("authenticated user can open the feed", async ({ page }) => {
    await page.goto("/feed");
    await expectNoFatalRenderError(page);
  });

  test("authenticated user can open account settings", async ({ page }) => {
    await page.goto("/me/account");
    await expectNoFatalRenderError(page);
  });
});
