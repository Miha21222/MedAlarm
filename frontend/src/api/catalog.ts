import type { MedicineCatalogReference } from "../types";
import { isDemoModeEnabled } from "../features/demo/demoMode";
import { searchPreviewCatalog } from "../features/demo/previewCatalog";
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
  if (import.meta.env.MODE === "preview" || isDemoModeEnabled()) {
    return {
      items: searchPreviewCatalog(query),
      source: {
        ready: true,
        record_count: 3,
        source_updated_at: null,
        imported_at: null,
        source_url: "https://data.gov.ua/dataset/reestr_likarskyh_zasobiv_moz",
        license: "CC BY",
      },
    };
  }
  return apiRequest(`/catalog/medicines?q=${encodeURIComponent(query)}&limit=20`);
}
