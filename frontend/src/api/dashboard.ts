import { buildTodayPlan, mergeReminderState } from "../features/dashboard/todayPlan";
import type { Medicine, ReminderEventState, TodayItem } from "../types";
import { apiRequest, hasAuthToken } from "./client";

// The plan always comes from the local medicine store. The server contributes
// only reminder dispatch state, which is required to expose real Taken/Skipped
// actions tied to an event that was actually sent.
export async function fetchToday(local: Medicine[], timezone = "UTC"): Promise<TodayItem[]> {
  const plan = buildTodayPlan(local, timezone);
  if (!hasAuthToken()) return plan;

  try {
    const result = await apiRequest<{ items: ReminderEventState[] }>("/dashboard/today");
    return mergeReminderState(plan, result.items);
  } catch {
    return plan.map((item) => ({ ...item, event_id: null, actionable: false }));
  }
}
