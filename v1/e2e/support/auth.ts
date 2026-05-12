import fs from "node:fs/promises";
import path from "node:path";
import { generate as generateTotp } from "otplib";
import { e2eEnv, requireEnv } from "./env";
import { postJson } from "./api";

const TOKEN_KEY = "domo_access_token";
const REFRESH_KEY = "domo_refresh_token";

type TokenPair = {
  access_token: string;
  refresh_token: string;
};

type UserLoginResponse = {
  tokens: TokenPair;
};

type AdminLoginStep1Response =
  | {
      totp_required: true;
      challenge_token: string;
    }
  | {
      totp_required: false;
      totp_setup_required: true;
      tokens: TokenPair;
    };

type AdminVerifyResponse = {
  tokens: TokenPair;
};

type StorageState = {
  cookies: [];
  origins: Array<{
    origin: string;
    localStorage: Array<{ name: string; value: string }>;
  }>;
};

function originOf(url: string): string {
  return new URL(url).origin;
}

async function writeStorageState(
  filePath: string,
  origin: string,
  tokens: TokenPair
): Promise<void> {
  const state: StorageState = {
    cookies: [],
    origins: [
      {
        origin,
        localStorage: [
          { name: TOKEN_KEY, value: tokens.access_token },
          { name: REFRESH_KEY, value: tokens.refresh_token },
        ],
      },
    ],
  };

  await fs.mkdir(path.dirname(filePath), { recursive: true });
  await fs.writeFile(filePath, JSON.stringify(state, null, 2));
}

export async function createUserStorageState(options: {
  email: string;
  password: string;
  filePath: string;
  origin?: string;
}): Promise<void> {
  const data = await postJson<UserLoginResponse>("/auth/login/email", {
    email: options.email,
    password: options.password,
  });

  await writeStorageState(
    options.filePath,
    options.origin ?? originOf(e2eEnv.frontendUrl),
    data.tokens
  );
}

export async function createAdminStorageState(options: {
  email?: string;
  password?: string;
  totpSecret?: string;
  filePath: string;
  origin?: string;
}): Promise<void> {
  const email = options.email ?? requireEnv("adminEmail", "E2E_ADMIN_EMAIL");
  const password =
    options.password ?? requireEnv("adminPassword", "E2E_ADMIN_PASSWORD");

  const step1 = await postJson<AdminLoginStep1Response>("/auth/admin/login", {
    email,
    password,
  });

  if (!step1.totp_required) {
    await writeStorageState(
      options.filePath,
      options.origin ?? originOf(e2eEnv.adminUrl),
      step1.tokens
    );
    return;
  }

  const totpSecret =
    options.totpSecret ?? requireEnv("adminTotpSecret", "E2E_ADMIN_TOTP_SECRET");
  const totpCode = await generateTotp({ secret: totpSecret });
  const verified = await postJson<AdminVerifyResponse>(
    "/auth/admin/login/verify",
    {
      challenge_token: step1.challenge_token,
      totp_code: totpCode,
    }
  );

  await writeStorageState(
    options.filePath,
    options.origin ?? originOf(e2eEnv.adminUrl),
    verified.tokens
  );
}
