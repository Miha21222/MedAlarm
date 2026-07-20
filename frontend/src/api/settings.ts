import type { ReminderSettings } from "../types";
import { apiRequest, hasAuthToken } from "./client";

export async function saveReminderSettings(settings: ReminderSettings): Promise<void> {
  if (!hasAuthToken()) return;
  await apiRequest("/reminders/config", { method: "PATCH", body: JSON.stringify(settings) });
}
