import type { DoseStatus, HistoryItem, Medicine } from "../../types";
import { getZonedCalendarPeriodRange, getZonedDayRange, zonedDateTimeToUtcTimestamp, zonedDayKeyFromTimestamp } from "../../utils/dateTime";
import { isDemoModeEnabled } from "../demo/demoMode";
import { buildPreviewHistory } from "./previewMedicines";

export type DoseAction = "taken" | "skipped";

const HISTORY_KEY = "medalarm.intakeHistory.v1";
// Live dose actions taken while demo mode is on (e.g. tapping Taken/Skip on a
// demo dashboard card) land here instead of HISTORY_KEY, so demo mode stays
// fully interactive without ever touching the user's real intake log.
const DEMO_HISTORY_KEY = "medalarm.demoIntakeHistory.v1";

function activeHistoryKey(): string {
  return isDemoModeEnabled() ? DEMO_HISTORY_KEY : HISTORY_KEY;
}

function readRawHistory(storage: Pick<Storage, "getItem"> = localStorage, key: string = activeHistoryKey()): HistoryItem[] {
  try {
    const parsed = JSON.parse(storage.getItem(key) ?? "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeRawHistory(
  items: HistoryItem[],
  storage: Pick<Storage, "setItem"> = localStorage,
  key: string = activeHistoryKey(),
): void {
  storage.setItem(key, JSON.stringify(items));
}

function scheduledAtFor(medicine: Medicine, timezone: string, now: Date): string {
  const time = medicine.schedules[0]?.time ?? "09:00";
  const dayKey = zonedDayKeyFromTimestamp(now.getTime(), timezone);
  const timestamp = zonedDateTimeToUtcTimestamp(dayKey, time, timezone) ?? now.getTime();
  return new Date(timestamp).toISOString();
}

function eventIdFor(medicine: Medicine, timezone: string, now: Date): string {
  const time = medicine.schedules[0]?.time ?? "09:00";
  const dayKey = zonedDayKeyFromTimestamp(now.getTime(), timezone);
  return `local-${medicine.client_medicine_id}-${dayKey}-${time}`;
}

export function readLocalIntakeHistory(
  period: "today" | "week" | "month" = "month",
  storage: Pick<Storage, "getItem"> = localStorage,
  now = new Date(),
  timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
): HistoryItem[] {
  const { start, end } = getZonedCalendarPeriodRange(now, timezone, period);
  const inPeriod = (item: HistoryItem) => {
    const respondedAt = Date.parse(item.responded_at || item.scheduled_at);
    return respondedAt >= start && respondedAt < end;
  };

  // Demo mode overlays generated fixture history (buildPreviewHistory, never
  // persisted) with whatever the user has actually clicked during this demo
  // session (DEMO_HISTORY_KEY, via activeHistoryKey()) — both read-only from
  // the real intake log's point of view.
  const live = readRawHistory(storage).filter(inPeriod);
  if (!isDemoModeEnabled()) {
    return live.sort(
      (left, right) => Date.parse(right.responded_at || right.scheduled_at) - Date.parse(left.responded_at || left.scheduled_at),
    );
  }
  const synthetic = buildPreviewHistory(now, timezone).filter(inPeriod);
  return [...live, ...synthetic].sort(
    (left, right) => Date.parse(right.responded_at || right.scheduled_at) - Date.parse(left.responded_at || left.scheduled_at),
  );
}

export function resolveLocalDoseAction(
  medicine: Medicine,
  action: DoseAction,
  timezone: string,
  storage: Pick<Storage, "getItem" | "setItem"> = localStorage,
  now = new Date(),
): HistoryItem {
  const eventId = eventIdFor(medicine, timezone, now);
  const current = readRawHistory(storage);
  const existing = current.find((item) => item.event_id === eventId);
  if (existing) return existing;

  const item: HistoryItem = {
    event_id: eventId,
    medicine: medicine.name,
    scheduled_at: scheduledAtFor(medicine, timezone, now),
    responded_at: now.toISOString(),
    status: action,
  };
  writeRawHistory([item, ...current], storage);
  return item;
}

export function statusForToday(
  medicine: Medicine,
  timezone: string,
  storage: Pick<Storage, "getItem"> = localStorage,
  now = new Date(),
): DoseStatus {
  const range = getZonedDayRange(now, timezone);
  const eventId = eventIdFor(medicine, timezone, now);
  const item = readRawHistory(storage).find(
    (historyItem) =>
      historyItem.event_id === eventId &&
      Date.parse(historyItem.scheduled_at) >= range.start &&
      Date.parse(historyItem.scheduled_at) < range.end,
  );
  return item?.status ?? "pending";
}

export function clearDemoIntakeHistory(storage: Pick<Storage, "setItem"> = localStorage): void {
  writeRawHistory([], storage, DEMO_HISTORY_KEY);
}
