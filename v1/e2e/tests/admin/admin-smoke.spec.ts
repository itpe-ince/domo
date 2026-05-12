import { expect, test } from "@playwright/test";

async function expectNoFatalRenderError(page: import("@playwright/test").Page) {
  await expect(page.locator("body")).toBeVisible();
  await expect(page.getByText(/Application error|Unhandled Runtime Error/i)).toHaveCount(0);
}

test.describe("admin app smoke", () => {
  test("admin can open the dashboard", async ({ page }) => {
    await page.goto("/dashboard");
    await expectNoFatalRenderError(page);
  });

  test("admin can open user management", async ({ page }) => {
    await page.goto("/users");
    await expectNoFatalRenderError(page);
  });

  test("admin can open artist applications", async ({ page }) => {
    await page.goto("/applications");
    await expectNoFatalRenderError(page);
  });
});
