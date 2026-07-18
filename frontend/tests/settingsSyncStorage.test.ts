import {
  clearPendingSettingsIfCurrent,
  PENDING_SETTINGS_KEY,
  readPendingSettings,
  writePendingSettings,
} from "../src/features/settingsSyncStorage";
import type { UserSettings } from "../src/types";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

const memory = new Map<string, string>();
const storage = {
  getItem: (key: string) => memory.get(key) ?? null,
  setItem: (key: string, value: string) => void memory.set(key, value),
  removeItem: (key: string) => void memory.delete(key),
};
const settings: UserSettings = {
  language: "ru",
  text_size: "large",
  timezone: "Europe/Kyiv",
  default_snooze_minutes: 15,
  remind_until_confirmed: true,
};

writePendingSettings(settings, storage);
assert(readPendingSettings(storage)?.text_size === "large", "pending settings should survive a reload");
assert(
  !clearPendingSettingsIfCurrent({ ...settings, text_size: "small" }, storage),
  "an older save must not clear a newer pending snapshot",
);
assert(readPendingSettings(storage)?.text_size === "large", "the newer pending snapshot should remain queued");
assert(clearPendingSettingsIfCurrent(settings, storage), "the matching successful save should clear pending state");
assert(readPendingSettings(storage) === null, "cleared settings should not retry again");

memory.set(PENDING_SETTINGS_KEY, JSON.stringify({ ...settings, default_snooze_minutes: "soon" }));
assert(readPendingSettings(storage) === null, "corrupted pending settings should be ignored safely");

console.log("settingsSyncStorage tests passed");
