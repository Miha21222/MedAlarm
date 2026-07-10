import type { DoseStatus, Medicine } from "../types";
import { resolveLocalDoseAction, type DoseAction } from "../features/medicines/localIntakeHistory";
import { apiRequest, hasAuthToken } from "./client";

export async function resolveReminderAction({
  eventId,
  medicine,
  action,
  timezone,
}: {
  eventId: string | null;
  medicine: Medicine;
  action: DoseAction;
  timezone: string;
}): Promise<{ event_id: string | number | null; status: DoseStatus }> {
  if (hasAuthToken()) {
    if (!eventId) throw new Error("Reminder event is not actionable yet");
    const result = await apiRequest<{ event_id: string; status: DoseStatus }>(`/reminder-events/${eventId}/actions`, {
      method: "POST",
      body: JSON.stringify({ action }),
    });
    return { event_id: result.event_id, status: result.status };
  }

  const item = resolveLocalDoseAction(medicine, action, timezone);
  return { event_id: item.event_id, status: item.status };
}
