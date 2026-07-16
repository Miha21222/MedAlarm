import type { MedicineCatalogReference } from "../types";
import { apiRequest } from "./client";

export interface CatalogSourceStatus {
  ready: boolean;
  record_count: number;
  source_updated_at: string | null;
  imported_at: string | null;
  source_url: string;
  license: string;
}

export async function searchMedicineCatalog(query: string): Promise<{
  items: MedicineCatalogReference[];
  source: CatalogSourceStatus;
}> {
  return apiRequest(`/catalog/medicines?q=${encodeURIComponent(query)}&limit=20`);
}
