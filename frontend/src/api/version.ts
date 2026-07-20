import { apiRequest } from "./client";

export const FRONTEND_VERSION = import.meta.env.VITE_APP_VERSION || "unknown";

export async function fetchBackendVersion(): Promise<string> {
  const response = await apiRequest<{ version: string }>("/version", { cache: "no-store" });
  return response.version;
}
