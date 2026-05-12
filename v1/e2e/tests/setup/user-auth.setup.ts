import { test } from "@playwright/test";
import fs from "node:fs/promises";
import path from "node:path";
import { e2eEnv } from "../../support/env";
import { createUserStorageState } from "../../support/auth";

async function writeEmptyStorageState(filePath: string): Promise<void> {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  await fs.writeFile(filePath, JSON.stringify({ cookies: [], origins: [] }, null, 2));
}

test("create user and artist storage states", async () => {
  if (
    !e2eEnv.userEmail ||
    !e2eEnv.userPassword ||
    !e2eEnv.artistEmail ||
    !e2eEnv.artistPassword
  ) {
    await writeEmptyStorageState("playwright/.auth/user.json");
    await writeEmptyStorageState("playwright/.auth/artist.json");
    test.info().annotations.push({
      type: "warning",
      description:
        "E2E user credentials are missing; wrote empty storage states for guest smoke coverage.",
    });
    return;
  }

  await createUserStorageState({
    email: e2eEnv.userEmail!,
    password: e2eEnv.userPassword!,
    filePath: "playwright/.auth/user.json",
  });

  await createUserStorageState({
    email: e2eEnv.artistEmail!,
    password: e2eEnv.artistPassword!,
    filePath: "playwright/.auth/artist.json",
  });
});
