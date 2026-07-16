import type { TextSize, UserSettings } from "../types";

export const SETTINGS_KEY = "medalarm.settings.v1";

export const defaultSettings: UserSettings = {
  language: "ru",
  text_size: "regular",
  timezone: "Europe/Kyiv",
  default_snooze_minutes: 10,
  remind_until_confirmed: true,
};

export function readSettings(storage: Pick<Storage, "getItem"> = localStorage): UserSettings {
  try {
    const stored = JSON.parse(storage.getItem(SETTINGS_KEY) ?? "{}") as Partial<UserSettings>;
    const allowedTextSizes: TextSize[] = ["small", "regular", "large"];
    return {
      ...defaultSettings,
      ...stored,
      text_size: allowedTextSizes.includes(stored.text_size as TextSize) ? stored.text_size as TextSize : "regular",
    };
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
