import type { Medicine, TodayItem } from "../types";
import { statusForToday } from "../features/medicines/localIntakeHistory";
import { apiRequest, hasAuthToken } from "./client";

// Unauthenticated (local-preview) fallback: derive "today" from local schedules
// by day-of-week instead of calling the server-authoritative endpoint.
export async function fetchToday(local: Medicine[], timezone = "UTC"): Promise<TodayItem[]> {
  if (!hasAuthToken()) {
    const nowDay = new Date().getDay();
    const weekday = nowDay === 0 ? 6 : nowDay - 1;
    const dayKey = new Intl.DateTimeFormat("en-CA", {
      timeZone: timezone,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(new Date());
    return local
      .filter(
        (medicine) =>
          medicine.is_active &&
          !medicine.deleted_at &&
          medicine.schedules.some(
            (slot) => slot.days_of_week === "*" || slot.days_of_week.split(",").includes(String(weekday)),
          ),
      )
      .flatMap((medicine) =>
        medicine.schedules
          .filter((slot) => slot.days_of_week === "*" || slot.days_of_week.split(",").includes(String(weekday)))
          .map((slot) => {
            const doseMedicine = { ...medicine, schedules: [slot] };
            return {
              ...doseMedicine,
              dose_key: `local:${medicine.client_medicine_id}:${dayKey}:${slot.time}`,
              scheduled_at: `${dayKey}T${slot.time}:00`,
              event_id: null,
              actionable: true,
              status: statusForToday(doseMedicine, timezone),
            };
          }),
      );
  }
  const result = await apiRequest<{ items: TodayItem[] }>("/dashboard/today");
  return result.items;
}
