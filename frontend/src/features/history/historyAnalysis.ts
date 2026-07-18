import type { HistoryItem } from "../../types";
import { dayKeyInTimezone, formatDayInTimezone, getZonedCalendarPeriodRange } from "../../utils/dateTime";

// History logs only ever carry a resolved status (never "pending" — that only
// applies to today's not-yet-acted-on doses), so the filter/group vocabulary
// here is deliberately narrower than the full DoseStatus union.
export type HistoryStatusFilter = "all" | "taken" | "skipped" | "missed" | "snoozed";
export type HistoryGroupBy = "none" | "day" | "medicine";
export type HistoryPeriod = "today" | "week" | "month";

export interface HistoryFilters {
  status: HistoryStatusFilter;
  medicine?: string;
  period?: HistoryPeriod;
  timezone?: string;
  now?: Date;
}

export const ALL_MEDICINES = "all";

function historyTimestamp(item: HistoryItem): string {
  return item.responded_at || item.scheduled_at;
}

export function filterHistory(items: HistoryItem[], filters: HistoryFilters): HistoryItem[] {
  const now = filters.now ?? new Date();
  const periodRange = filters.period
    ? getZonedCalendarPeriodRange(now, filters.timezone ?? "UTC", filters.period)
    : null;

  return items.filter((item) => {
    if (filters.status !== "all" && item.status !== filters.status) return false;
    if (filters.medicine && filters.medicine !== ALL_MEDICINES && item.medicine !== filters.medicine) return false;
    if (periodRange !== null) {
      const respondedAt = Date.parse(historyTimestamp(item));
      if (!Number.isFinite(respondedAt) || respondedAt < periodRange.start || respondedAt >= periodRange.end) return false;
    }
    return true;
  });
}

export function listHistoryMedicineNames(items: HistoryItem[]): string[] {
  return [...new Set(items.map((item) => item.medicine))].sort((a, b) => a.localeCompare(b));
}

export interface HistoryGroup {
  key: string;
  label: string;
  items: HistoryItem[];
}

// Items arrive newest-first (both the API and the local fallback sort that
// way), so a Map preserves that order for "day" groups. "medicine" groups are
// re-sorted alphabetically instead, since recency of the group's most recent
// dose isn't a meaningful ordering for "which medicines have history".
export function groupHistory(
  items: HistoryItem[],
  groupBy: HistoryGroupBy,
  timezone: string,
  locale: string,
): HistoryGroup[] {
  if (groupBy === "none") {
    return items.length ? [{ key: "all", label: "", items }] : [];
  }

  const buckets = new Map<string, HistoryItem[]>();
  for (const item of items) {
    const key = groupBy === "day" ? dayKeyInTimezone(historyTimestamp(item), timezone) : item.medicine;
    const bucket = buckets.get(key);
    if (bucket) {
      bucket.push(item);
    } else {
      buckets.set(key, [item]);
    }
  }

  const groups = [...buckets.entries()].map(([key, groupItems]) => ({
    key,
    label: groupBy === "day" ? formatDayInTimezone(historyTimestamp(groupItems[0]), timezone, locale) : key,
    items: groupItems,
  }));

  if (groupBy === "medicine") {
    groups.sort((left, right) => left.label.localeCompare(right.label));
  }
  return groups;
}

export interface HistorySummary {
  total: number;
  taken: number;
  skipped: number;
  missed: number;
  snoozed: number;
  takenPercent: number;
}

export function summarizeHistory(items: HistoryItem[]): HistorySummary {
  const total = items.length;
  const taken = items.filter((item) => item.status === "taken").length;
  const skipped = items.filter((item) => item.status === "skipped").length;
  const missed = items.filter((item) => item.status === "missed").length;
  const snoozed = items.filter((item) => item.status === "snoozed").length;
  return { total, taken, skipped, missed, snoozed, takenPercent: total ? Math.round((taken / total) * 100) : 0 };
}
