import type { UserSettings } from "../types";

export const SETTINGS_KEY = "medalarm.settings.v1";

export const defaultSettings: UserSettings = {
  language: "ru",
  timezone: "Europe/Kyiv",
  default_snooze_minutes: 10,
  remind_until_confirmed: true,
};

export function readSettings(storage: Pick<Storage, "getItem"> = localStorage): UserSettings {
  try {
    return { ...defaultSettings, ...JSON.parse(storage.getItem(SETTINGS_KEY) ?? "{}") };
  } catch {
    return defaultSettings;
  }
}

export function writeSettings(
  settings: UserSettings,
  storage: Pick<Storage, "setItem"> = localStorage,
): void {
  storage.setItem(SETTINGS_KEY, JSON.stringify(settings));
}
