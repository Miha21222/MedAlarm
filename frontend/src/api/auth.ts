import { getTelegramWebApp } from "../telegramWebApp";
import type { UserSettings } from "../types";
import { apiRequest, setAuthToken } from "./client";

const PREVIEW_USER: UserSettings = {
  language: "ru",
  timezone: "Europe/Kyiv",
  default_snooze_minutes: 10,
  remind_until_confirmed: true,
};

export function isLocalPreview(): boolean {
  return (
    import.meta.env.DEV ||
    import.meta.env.MODE === "preview" ||
    import.meta.env.VITE_LOCAL_PREVIEW === "true"
  );
}

export async function authenticate(): Promise<UserSettings> {
  if (isLocalPreview()) {
    return PREVIEW_USER;
  }
  const telegram = getTelegramWebApp();
  const response = await apiRequest<{ access_token: string; user: UserSettings }>("/auth/telegram", {
    method: "POST",
    body: JSON.stringify({ init_data: telegram?.initData || "" }),
  });
  setAuthToken(response.access_token);
  return response.user;
}
