import type { Medicine, TodayItem } from "../types";
import { buildTodayPlan } from "../features/dashboard/todayPlan";
import { apiRequest, hasAuthToken } from "./client";

// Unauthenticated (local-preview) fallback: derive "today" from local schedules
// by day-of-week instead of calling the server-authoritative endpoint.
export async function fetchToday(local: Medicine[], timezone = "UTC"): Promise<TodayItem[]> {
  if (!hasAuthToken()) return buildTodayPlan(local, timezone);
  const result = await apiRequest<{ items: TodayItem[] }>("/dashboard/today");
  return result.items;
}
