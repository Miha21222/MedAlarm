import type { HistoryItem } from "../types";
import { readLocalIntakeHistory } from "../features/medicines/localIntakeHistory";
import { apiRequest, hasAuthToken } from "./client";

export async function fetchHistory(
  period: "today" | "week" | "month" = "month",
  timezone = "UTC",
): Promise<HistoryItem[]> {
  if (!hasAuthToken()) return readLocalIntakeHistory(period, localStorage, new Date(), timezone);
  const result = await apiRequest<{ items: HistoryItem[] }>(`/history?period=${period}`);
  return result.items;
}
