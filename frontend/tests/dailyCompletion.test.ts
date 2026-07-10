import { calculateDailyCompletion } from "../src/utils/dailyCompletion";
import type { TodayItem } from "../src/types";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

function item(status: TodayItem["status"]): TodayItem {
  return {
    client_medicine_id: crypto.randomUUID(),
    name: "Test",
    dosage_text: "1 таблетка",
    comment: null,
    is_active: true,
    updated_at: "2026-07-07T09:00:00.000Z",
    deleted_at: null,
    schedules: [{ time: "09:00", days_of_week: "*" }],
    dose_key: crypto.randomUUID(),
    scheduled_at: "2026-07-07T09:00:00.000Z",
    event_id: null,
    actionable: false,
    status,
  };
}

const mixed = calculateDailyCompletion([
  item("taken"),
  item("taken"),
  item("taken"),
  item("taken"),
  item("pending"),
  item("pending"),
  item("skipped"),
  item("snoozed"),
]);
assert(mixed.total === 8, "daily completion should count every scheduled today item");
assert(mixed.taken === 4, "daily completion should count only taken items as complete");
assert(mixed.percent === 50, "4 taken out of 8 scheduled should be 50%");

const empty = calculateDailyCompletion([]);
assert(empty.percent === 0 && empty.total === 0, "empty schedule should show 0%");

console.log("dailyCompletion tests passed");
