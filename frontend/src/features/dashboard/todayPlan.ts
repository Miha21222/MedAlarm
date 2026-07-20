import type { Medicine, ReminderEventState, TodayItem } from "../../types";
import { zonedDateTimeToUtcTimestamp, zonedDayKeyFromTimestamp } from "../../utils/dateTime";
import { statusForToday } from "../medicines/localIntakeHistory";

function weekdayForDayKey(dayKey: string): number {
  const [year, month, day] = dayKey.split("-").map(Number);
  const sundayBased = new Date(Date.UTC(year, month - 1, day)).getUTCDay();
  return sundayBased === 0 ? 6 : sundayBased - 1;
}

function slotIsDue(daysOfWeek: string, weekday: number): boolean {
  return daysOfWeek === "*" || daysOfWeek.split(",").map((day) => day.trim()).includes(String(weekday));
}

function localDoseKey(item: TodayItem): string {
  const slot = item.schedules[0];
  return `${item.client_medicine_id}:${slot?.time ?? ""}:${slot?.days_of_week ?? "*"}`;
}

function reminderEventKey(item: ReminderEventState): string {
  return `${item.client_medicine_id}:${item.time}:${item.days_of_week}`;
}

export function mergeReminderState(local: TodayItem[], remote: ReminderEventState[]): TodayItem[] {
  const remoteByDose = new Map(remote.map((item) => [reminderEventKey(item), item]));
  return local.map((item) => {
    const serverEvent = remoteByDose.get(localDoseKey(item));
    if (!serverEvent) return { ...item, event_id: null, actionable: false };
    return {
      ...item,
      status: serverEvent.status,
      event_id: serverEvent.event_id,
      actionable: serverEvent.actionable,
    };
  });
}

export function buildTodayPlan(
  medicines: Medicine[],
  timezone: string,
  now = new Date(),
  storage: Pick<Storage, "getItem"> = localStorage,
): TodayItem[] {
  const dayKey = zonedDayKeyFromTimestamp(now.getTime(), timezone);
  const weekday = weekdayForDayKey(dayKey);

  return medicines
    .filter((medicine) => medicine.is_active && !medicine.deleted_at)
    .flatMap((medicine) =>
      medicine.schedules
        .filter((slot) => slotIsDue(slot.days_of_week, weekday))
        .map((slot): TodayItem | null => {
          const scheduledTimestamp = zonedDateTimeToUtcTimestamp(dayKey, slot.time, timezone);
          if (scheduledTimestamp === null) return null;

          const createdTimestamp = Date.parse(medicine.created_at ?? "");
          const createdOnDay = Number.isFinite(createdTimestamp)
            && zonedDayKeyFromTimestamp(createdTimestamp, timezone) === dayKey;
          if (createdOnDay && scheduledTimestamp < Math.floor(createdTimestamp / 60_000) * 60_000) return null;

          const doseMedicine = { ...medicine, schedules: [slot] };
          return {
            ...doseMedicine,
            dose_key: `local:${medicine.client_medicine_id}:${dayKey}:${slot.time}`,
            scheduled_at: new Date(scheduledTimestamp).toISOString(),
            event_id: null,
            actionable: true,
            status: statusForToday(doseMedicine, timezone, storage, now),
          };
        })
        .filter((item): item is TodayItem => item !== null),
    );
}
