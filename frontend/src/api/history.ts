import type { HistoryItem } from "../types";
import { apiRequest, hasAuthToken } from "./client";

export async function fetchHistory(period: "today" | "week" | "month" = "month"): Promise<HistoryItem[]> {
  if (!hasAuthToken()) return [];
  const result = await apiRequest<{ items: HistoryItem[] }>(`/history?period=${period}`);
  return result.items;
}
