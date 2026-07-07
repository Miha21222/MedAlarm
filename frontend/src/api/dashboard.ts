import type { Medicine, TodayItem } from "../types";
import { apiRequest, hasAuthToken } from "./client";

// Unauthenticated (local-preview) fallback: derive "today" from local schedules
// by day-of-week instead of calling the server-authoritative endpoint.
export async function fetchToday(local: Medicine[]): Promise<TodayItem[]> {
  if (!hasAuthToken()) {
    const nowDay = new Date().getDay();
    const weekday = nowDay === 0 ? 6 : nowDay - 1;
    return local
      .filter(
        (medicine) =>
          medicine.is_active &&
          !medicine.deleted_at &&
          medicine.schedules.some(
            (slot) => slot.days_of_week === "*" || slot.days_of_week.split(",").includes(String(weekday)),
          ),
      )
      .map((medicine) => ({ ...medicine, status: "pending" }));
  }
  const result = await apiRequest<{ items: TodayItem[] }>("/dashboard/today");
  return result.items;
}

export async function fetchAdherence(period: "7d" | "30d"): Promise<{ adherence_percent: number; counts: Record<string, number> }> {
  if (!hasAuthToken()) return { adherence_percent: 0, counts: {} };
  return apiRequest<{ adherence_percent: number; counts: Record<string, number> }>(
    `/dashboard/adherence?period=${period}`,
  );
}
