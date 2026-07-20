import {
  clearPendingSettingsIfCurrent,
  PENDING_SETTINGS_KEY,
  readPendingSettings,
  reminderSettingsFrom,
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

const reminderSettings = reminderSettingsFrom(settings);
writePendingSettings(reminderSettings, storage);
assert(readPendingSettings(storage)?.timezone === "Europe/Kyiv", "pending reminder settings should survive a reload");
assert(
  !clearPendingSettingsIfCurrent({ ...reminderSettings, timezone: "UTC" }, storage),
  "an older save must not clear a newer pending snapshot",
);
assert(readPendingSettings(storage)?.timezone === "Europe/Kyiv", "the newer pending snapshot should remain queued");
assert(
  !("text_size" in reminderSettings),
  "UI-only text size must not enter the server reminder projection",
);
assert(clearPendingSettingsIfCurrent(reminderSettings, storage), "the matching successful save should clear pending state");
assert(readPendingSettings(storage) === null, "cleared settings should not retry again");

memory.set(PENDING_SETTINGS_KEY, JSON.stringify({ ...settings, default_snooze_minutes: "soon" }));
assert(readPendingSettings(storage) === null, "corrupted pending settings should be ignored safely");

console.log("settingsSyncStorage tests passed");
