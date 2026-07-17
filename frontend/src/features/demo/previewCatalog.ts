import type { MedicineCatalogReference } from "../../types";

// Small, development-only catalogue fixture shaped from the same MOH State
// Register fields used by the backend importer. It is never used in production.
export const PREVIEW_CATALOG_MEDICINES: MedicineCatalogReference[] = [
  {
    source: "moh_state_register",
    source_id: "preview-moh-aspirin-cardio",
    trade_name: "АСПІРИН КАРДІО®",
    inn: "Acetylsalicylic acid",
    form: "таблетки по 100 мг №28",
    dispensing_conditions: "без рецепта",
    active_ingredients: "ацетилсаліцилова кислота",
    pharmacotherapeutic_group: "Антитромботичні засоби",
    atc_codes: "B01AC06",
    applicant: "Заявник (демо)",
    manufacturer: "Виробник (демо)",
    registration_number: "UA/7802/01/01",
    valid_from: "01.01.2025",
    valid_until: "необмежений",
    early_termination: "Ні",
    instruction_url: null,
  },
  {
    source: "moh_state_register",
    source_id: "preview-moh-aspirin",
    trade_name: "АСПІРИН®",
    inn: "Acetylsalicylic acid",
    form: "таблетки",
    dispensing_conditions: null,
    active_ingredients: "ацетилсаліцилова кислота",
    pharmacotherapeutic_group: null,
    atc_codes: "N02BA01",
    applicant: "Заявник (демо)",
    manufacturer: "Виробник (демо)",
    registration_number: "UA/preview/02",
    valid_from: null,
    valid_until: null,
    early_termination: "Ні",
    instruction_url: null,
  },
  {
    source: "moh_state_register",
    source_id: "preview-moh-ibuprofen",
    trade_name: "ІБУПРОФЕН (ДЕМО)",
    inn: "Ibuprofen",
    form: "таблетки, вкриті плівковою оболонкою",
    dispensing_conditions: "без рецепта",
    active_ingredients: "ібупрофен",
    pharmacotherapeutic_group: "Нестероїдні протизапальні засоби",
    atc_codes: "M01AE01",
    applicant: "Заявник (демо)",
    manufacturer: "Виробник (демо)",
    registration_number: "UA/preview/03",
    valid_from: null,
    valid_until: null,
    early_termination: "Ні",
    instruction_url: null,
  },
];

function normalizeCatalogText(value: string): string {
  return value
    .normalize("NFKC")
    .toLocaleLowerCase()
    .replace(/[ії]/g, "и")
    .replace(/є/g, "е")
    .replace(/ґ/g, "г")
    .replace(/ё/g, "е")
    .replace(/[^0-9a-zа-я]+/g, " ")
    .trim()
    .replace(/\s+/g, " ");
}

export function searchPreviewCatalog(query: string, limit = 20): MedicineCatalogReference[] {
  const normalizedQuery = normalizeCatalogText(query);
  if (!normalizedQuery) return [];
  return PREVIEW_CATALOG_MEDICINES.filter((medicine) =>
    normalizeCatalogText([
      medicine.trade_name,
      medicine.inn,
      medicine.active_ingredients,
      medicine.registration_number,
    ].filter(Boolean).join(" ")).includes(normalizedQuery),
  ).slice(0, limit);
}
