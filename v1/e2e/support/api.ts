import { request } from "@playwright/test";
import { e2eEnv } from "./env";

type ApiEnvelope<T> = { data: T } | { error: { code: string; message: string } };

export async function postJson<T>(
  path: string,
  body: Record<string, unknown>
): Promise<T> {
  const context = await request.newContext({
    extraHTTPHeaders: {
      "Content-Type": "application/json",
    },
  });

  try {
    const relativePath = path.replace(/^\/+/, "");
    const url = `${e2eEnv.apiUrl.replace(/\/+$/, "")}/${relativePath}`;
    const response = await context.post(url, { data: body });
    const json = (await response.json()) as ApiEnvelope<T>;

    if (!response.ok() || "error" in json) {
      const message =
        "error" in json
          ? `${json.error.code}: ${json.error.message}`
          : `${response.status()} ${response.statusText()}`;
      throw new Error(`E2E API POST ${path} failed: ${message}`);
    }

    return json.data;
  } finally {
    await context.dispose();
  }
}
