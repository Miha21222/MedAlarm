import { useEffect, useState } from "react";
import {
  getTelegramWebApp,
  type TelegramHapticImpactStyle,
  type TelegramHapticNotificationType,
} from "../telegramWebApp";

// Haptics is a per-device preference (the Telegram HapticFeedback API only does
// anything inside the Telegram client), so it lives in localStorage rather than
// the server-synced user settings. Default: enabled.
const STORAGE_KEY = "medalarm.haptics.enabled";
export const HAPTICS_CHANGED_EVENT = "medalarm:haptics-changed";

export function isHapticsEnabled(): boolean {
  if (typeof window === "undefined") return true;
  return window.localStorage.getItem(STORAGE_KEY) !== "0";
}

export function setHapticsEnabled(enabled: boolean): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, enabled ? "1" : "0");
  window.dispatchEvent(new CustomEvent(HAPTICS_CHANGED_EVENT));
}

function getSupportedHaptics() {
  const webApp = getTelegramWebApp();
  if (webApp?.isVersionAtLeast && !webApp.isVersionAtLeast("6.1")) return undefined;
  return webApp?.HapticFeedback;
}

export function hapticImpact(style: TelegramHapticImpactStyle = "medium"): void {
  if (!isHapticsEnabled()) return;
  try {
    getSupportedHaptics()?.impactOccurred?.(style);
  } catch {
    /* haptics are best-effort; never let them break an action */
  }
}

export function hapticNotification(type: TelegramHapticNotificationType): void {
  if (!isHapticsEnabled()) return;
  try {
    getSupportedHaptics()?.notificationOccurred?.(type);
  } catch {
    /* best-effort */
  }
}

export function hapticSelection(): void {
  if (!isHapticsEnabled()) return;
  try {
    getSupportedHaptics()?.selectionChanged?.();
  } catch {
    /* best-effort */
  }
}

export function useHapticsEnabled(): [boolean, (enabled: boolean) => void] {
  const [enabled, setEnabled] = useState(isHapticsEnabled);
  useEffect(() => {
    const sync = () => setEnabled(isHapticsEnabled());
    window.addEventListener(HAPTICS_CHANGED_EVENT, sync);
    return () => window.removeEventListener(HAPTICS_CHANGED_EVENT, sync);
  }, []);
  return [enabled, setHapticsEnabled];
}
