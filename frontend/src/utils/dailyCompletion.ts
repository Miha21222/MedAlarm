import type { TodayItem } from "../types";

export function calculateDailyCompletion(items: TodayItem[]): { taken: number; total: number; percent: number } {
  const total = items.length;
  const taken = items.filter((item) => item.status === "taken").length;
  return {
    taken,
    total,
    percent: total ? Math.round((taken / total) * 100) : 0,
  };
}
