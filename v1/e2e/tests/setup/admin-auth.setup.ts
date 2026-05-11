import { test } from "@playwright/test";
import fs from "node:fs/promises";
import path from "node:path";
import { e2eEnv } from "../../support/env";
import { createAdminStorageState } from "../../support/auth";

async function writeEmptyStorageState(filePath: string): Promise<void> {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  await fs.writeFile(filePath, JSON.stringify({ cookies: [], origins: [] }, null, 2));
}

test("create admin storage state", async () => {
  if (!e2eEnv.adminEmail || !e2eEnv.adminPassword || !e2eEnv.adminTotpSecret) {
    await writeEmptyStorageState("playwright/.auth/admin.json");
    test.info().annotations.push({
      type: "warning",
      description:
        "E2E admin credentials are missing; wrote an empty storage state for guest smoke coverage.",
    });
    return;
  }

  await createAdminStorageState({
    filePath: "playwright/.auth/admin.json",
  });
});
