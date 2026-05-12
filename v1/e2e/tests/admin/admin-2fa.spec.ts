import { expect, test } from "@playwright/test";
import { generate as generateTotp } from "otplib";
import { e2eEnv } from "../../support/env";

test.describe("admin 2FA login", () => {
  test("admin can log in through password and TOTP UI", async ({ page }) => {
    test.skip(
      !e2eEnv.adminEmail || !e2eEnv.adminPassword || !e2eEnv.adminTotpSecret,
      "Set E2E_ADMIN_EMAIL, E2E_ADMIN_PASSWORD, and E2E_ADMIN_TOTP_SECRET."
    );

    await page.addInitScript(() => {
      window.localStorage.clear();
    });

    await page.goto("/login");
    await page.getByLabel("관리자 이메일").fill(e2eEnv.adminEmail!);
    await page.getByLabel("비밀번호").fill(e2eEnv.adminPassword!);
    await page.getByRole("button", { name: "다음 →" }).click();

    await expect(page.getByLabel("Authenticator 6자리 코드")).toBeVisible();
    const totpCode = await generateTotp({ secret: e2eEnv.adminTotpSecret! });
    await page.getByLabel("Authenticator 6자리 코드").fill(totpCode);
    await page.getByRole("button", { name: "로그인" }).click();

    await expect(page).toHaveURL(/\/dashboard$/);
    await expect(page.locator("body")).toBeVisible();
  });
});
