import type { UserSettings } from "../types";
import { apiRequest, hasAuthToken } from "./client";

export async function saveSettings(settings: UserSettings): Promise<void> {
  if (!hasAuthToken()) return;
  await apiRequest("/settings/me", { method: "PATCH", body: JSON.stringify(settings) });
}
