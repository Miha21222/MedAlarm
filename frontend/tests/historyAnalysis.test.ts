import type { HistoryItem } from "../src/types";
import {
  filterHistory,
  groupHistory,
  listHistoryMedicineNames,
  summarizeHistory,
} from "../src/features/history/historyAnalysis";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

function item(overrides: Partial<HistoryItem>): HistoryItem {
  return {
    event_id: "evt",
    medicine: "Aspirin",
    scheduled_at: "2026-07-07T09:00:00.000Z",
    responded_at: "2026-07-07T09:05:00.000Z",
    status: "taken",
    ...overrides,
  };
}

const items: HistoryItem[] = [
  item({ event_id: "1", medicine: "Aspirin", status: "taken", scheduled_at: "2026-07-07T09:00:00.000Z" }),
  item({ event_id: "2", medicine: "Aspirin", status: "skipped", scheduled_at: "2026-07-07T21:00:00.000Z" }),
  item({ event_id: "3", medicine: "Vitamin D", status: "taken", scheduled_at: "2026-07-06T08:00:00.000Z" }),
  item({ event_id: "4", medicine: "Vitamin D", status: "missed", scheduled_at: "2026-07-05T08:00:00.000Z" }),
];

// filterHistory
assert(filterHistory(items, { status: "all", medicine: "all" }).length === 4, "no filters keeps everything");
assert(
  filterHistory(items, { status: "taken", medicine: "all" }).every((entry) => entry.status === "taken"),
  "status filter narrows to matching status",
);
assert(
  filterHistory(items, { status: "all", medicine: "Aspirin" }).every((entry) => entry.medicine === "Aspirin"),
  "medicine filter narrows to matching medicine",
);
assert(
  filterHistory(items, { status: "taken", medicine: "Vitamin D" }).length === 1,
  "combined filters intersect",
);

// listHistoryMedicineNames
assert(
  JSON.stringify(listHistoryMedicineNames(items)) === JSON.stringify(["Aspirin", "Vitamin D"]),
  "medicine names are deduped and sorted",
);

// groupHistory — none
const noneGroups = groupHistory(items, "none", "UTC", "en");
assert(noneGroups.length === 1 && noneGroups[0].items.length === 4, "groupBy none returns a single bucket");
assert(groupHistory([], "none", "UTC", "en").length === 0, "groupBy none on empty input returns no groups");

// groupHistory — day (three distinct UTC days in the fixture)
const dayGroups = groupHistory(items, "day", "UTC", "en");
assert(dayGroups.length === 3, "groupBy day buckets by calendar day");
assert(dayGroups[0].items.length === 2, "the most recent day group keeps both same-day entries");

// groupHistory — medicine (sorted alphabetically, not by recency)
const medicineGroups = groupHistory(items, "medicine", "UTC", "en");
assert(
  medicineGroups.map((group) => group.key).join(",") === "Aspirin,Vitamin D",
  "groupBy medicine sorts groups alphabetically",
);
assert(
  medicineGroups.find((group) => group.key === "Aspirin")?.items.length === 2,
  "each medicine group contains only that medicine's entries",
);

// summarizeHistory
const summary = summarizeHistory(items);
assert(summary.total === 4 && summary.taken === 2 && summary.skipped === 1 && summary.missed === 1, "summary counts by status");
assert(summary.takenPercent === 50, "2 taken out of 4 is 50%");
assert(summarizeHistory([]).takenPercent === 0, "empty history summarizes to 0%");

console.log("historyAnalysis tests passed");
