import { z } from "zod";
import type { UserSettings } from "../types";

export const PENDING_SETTINGS_KEY = "medalarm.settings.pending.v1";

type SettingsSyncStorage = Pick<Storage, "getItem" | "setItem" | "removeItem">;

const settingsSchema = z.object({
  language: z.enum(["ru", "uk", "en"]),
  text_size: z.enum(["small", "regular", "large"]),
  timezone: z.string().min(1).max(64),
  default_snooze_minutes: z.number().int().min(1).max(180),
  remind_until_confirmed: z.boolean(),
});

export function readPendingSettings(storage: Pick<Storage, "getItem"> = localStorage): UserSettings | null {
  try {
    const raw = storage.getItem(PENDING_SETTINGS_KEY);
    if (!raw) return null;
    const result = settingsSchema.safeParse(JSON.parse(raw));
    return result.success ? result.data : null;
  } catch {
    return null;
  }
}

export function writePendingSettings(
  settings: UserSettings,
  storage: Pick<Storage, "setItem"> = localStorage,
): void {
  storage.setItem(PENDING_SETTINGS_KEY, JSON.stringify(settings));
}

export function clearPendingSettingsIfCurrent(
  saved: UserSettings,
  storage: SettingsSyncStorage = localStorage,
): boolean {
  const pending = readPendingSettings(storage);
  if (!pending || JSON.stringify(pending) !== JSON.stringify(saved)) return false;
  storage.removeItem(PENDING_SETTINGS_KEY);
  return true;
}
