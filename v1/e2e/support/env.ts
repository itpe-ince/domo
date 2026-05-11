type E2eEnv = {
  frontendUrl: string;
  adminUrl: string;
  apiUrl: string;
  userEmail?: string;
  userPassword?: string;
  artistEmail?: string;
  artistPassword?: string;
  adminEmail?: string;
  adminPassword?: string;
  adminTotpSecret?: string;
  runId: string;
};

function optional(name: string): string | undefined {
  const value = process.env[name]?.trim();
  return value ? value : undefined;
}

function withDefault(name: string, fallback: string): string {
  return optional(name) ?? fallback;
}

function buildRunId(): string {
  const explicit = optional("E2E_RUN_ID");
  if (explicit) return explicit;
  return new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14);
}

export const e2eEnv: E2eEnv = {
  frontendUrl: withDefault("E2E_FRONTEND_URL", "http://localhost:3000"),
  adminUrl: withDefault("E2E_ADMIN_URL", "http://localhost:3800"),
  apiUrl: withDefault("E2E_API_URL", "http://localhost:3710/v1"),
  userEmail: optional("E2E_USER_EMAIL"),
  userPassword: optional("E2E_USER_PASSWORD"),
  artistEmail: optional("E2E_ARTIST_EMAIL"),
  artistPassword: optional("E2E_ARTIST_PASSWORD"),
  adminEmail: optional("E2E_ADMIN_EMAIL"),
  adminPassword: optional("E2E_ADMIN_PASSWORD"),
  adminTotpSecret: optional("E2E_ADMIN_TOTP_SECRET"),
  runId: buildRunId(),
};

export function requireEnv<K extends keyof E2eEnv>(
  key: K,
  label: string = String(key)
): NonNullable<E2eEnv[K]> {
  const value = e2eEnv[key];
  if (!value) {
    throw new Error(`Missing required E2E environment variable: ${label}`);
  }
  return value as NonNullable<E2eEnv[K]>;
}
