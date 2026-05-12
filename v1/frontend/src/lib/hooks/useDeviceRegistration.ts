/**
 * useDeviceRegistration — B'-3 push-email-digest-foundation
 *
 * Web Push registration hook (Phase 8 scope: backend + frontend preferences UI).
 * Actual native push registration (FCM Service Worker / APNs) is Phase 9+ Mobile PDCA.
 *
 * This hook:
 *  1. Generates a stable browser device_id from localStorage
 *  2. Optionally registers a Web Push subscription (if VAPID key configured)
 *  3. Calls POST /me/devices with the token + platform=fcm + device_id
 *  4. Provides revoke() to soft-delete the token on logout
 *
 * In Phase 8 (web scope): token is a placeholder UUID since native FCM service
 * worker is not yet wired. The endpoint accepts any non-empty token string.
 */

import { useCallback, useEffect, useState } from "react";
import { registerDeviceToken, revokeDeviceToken, DeviceTokenView } from "@/lib/api";
import { tokenStore } from "@/lib/api";

const DEVICE_ID_KEY = "domo_device_id";

/** Get or create a stable browser-local device_id. */
function getOrCreateDeviceId(): string {
  if (typeof window === "undefined") return "server";
  let id = localStorage.getItem(DEVICE_ID_KEY);
  if (!id) {
    id = `web-${Math.random().toString(36).slice(2, 10)}-${Date.now()}`;
    localStorage.setItem(DEVICE_ID_KEY, id);
  }
  return id;
}

type RegistrationState =
  | "idle"
  | "registering"
  | "registered"
  | "revoked"
  | "error";

export interface UseDeviceRegistrationReturn {
  state: RegistrationState;
  deviceToken: DeviceTokenView | null;
  deviceId: string | null;
  register: () => Promise<void>;
  revoke: (tokenId: string) => Promise<void>;
  error: string | null;
}

/**
 * Hook for managing push device token registration.
 *
 * Phase 8 Web scope:
 *   - Registers a web browser token (placeholder token string)
 *   - Phase 9+ mobile: replace with real FCM/APNs SDK token
 *
 * @param autoRegister - If true, registers on mount when user is logged in.
 */
export function useDeviceRegistration(
  autoRegister = false
): UseDeviceRegistrationReturn {
  const [state, setState] = useState<RegistrationState>("idle");
  const [deviceToken, setDeviceToken] = useState<DeviceTokenView | null>(null);
  const [deviceId, setDeviceId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      setDeviceId(getOrCreateDeviceId());
    }
  }, []);

  const register = useCallback(async () => {
    const accessToken = tokenStore.get();
    if (!accessToken) {
      setError("Authentication required to register push token");
      return;
    }

    setState("registering");
    setError(null);

    try {
      const did = getOrCreateDeviceId();

      // Phase 8 Web: use a browser-fingerprinted placeholder token.
      // Phase 9+ Mobile: replace with real FCM registration token from
      //   firebase.messaging().getToken({ vapidKey: VAPID_KEY })
      //   or APNs token from Apple's Push Notification Entitlement.
      const webToken = `web-placeholder-${did}`;

      const result = await registerDeviceToken({
        token: webToken,
        platform: "fcm",
        device_id: did,
      });

      setDeviceToken(result);
      setState("registered");
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Failed to register push token";
      setError(msg);
      setState("error");
    }
  }, []);

  const revoke = useCallback(async (tokenId: string) => {
    setState("registering");
    setError(null);
    try {
      await revokeDeviceToken(tokenId);
      setDeviceToken(null);
      setState("revoked");
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Failed to revoke push token";
      setError(msg);
      setState("error");
    }
  }, []);

  // Auto-register on mount if configured
  useEffect(() => {
    if (!autoRegister) return;
    const token = tokenStore.get();
    if (!token) return; // Not logged in
    if (state === "idle") {
      register();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoRegister, state]);

  return { state, deviceToken, deviceId, register, revoke, error };
}
