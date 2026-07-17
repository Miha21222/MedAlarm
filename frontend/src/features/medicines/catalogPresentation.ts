import type { MedicineCatalogReference } from "../../types";

const STRENGTH_PATTERN = /\d+(?:[.,]\d+)?\s*(?:мкг|мг|кг|г|мл|л|%|мо|од|iu)(?:\s*\/\s*\d+(?:[.,]\d+)?\s*(?:мкг|мг|г|мл|л))?/i;
const PACKAGE_CLAUSE = /^(?:по\s+\d+\s+(?:таблет|капсул|ампул|флакон|пакет|саше)|у\s+(?:блістер|флакон|пакет)|в\s+(?:блістер|флакон|пакет))/i;

function clean(value: string): string {
  return value.replace(/\s+/g, " ").replace(/\s*№\s*\d+.*/i, "").trim().replace(/[.,;:]$/, "");
}

export function catalogCardSummary(medicine: MedicineCatalogReference): string {
  const form = clean((medicine.form ?? "").split(";")[0] ?? "");
  if (!form) return "";

  const strength = form.match(STRENGTH_PATTERN)?.[0]
    ?? medicine.active_ingredients?.match(STRENGTH_PATTERN)?.[0]
    ?? "";
  const clauses = form.split(",").map(clean).filter(Boolean);
  const type = clean((clauses[0] ?? form).replace(STRENGTH_PATTERN, "").replace(/\s+по\s*$/i, ""));
  const specification = clauses
    .slice(1)
    .filter((clause) => !STRENGTH_PATTERN.test(clause) && !PACKAGE_CLAUSE.test(clause))
    .slice(0, 2)
    .join(", ");

  return [type, strength, specification].filter(Boolean).join(" · ");
}

export function catalogResultSummaries(medicines: MedicineCatalogReference[]): Map<string, string> {
  const baseSummaries = new Map(medicines.map((medicine) => [medicine.source_id, catalogCardSummary(medicine)]));
  const groups = new Map<string, MedicineCatalogReference[]>();
  for (const medicine of medicines) {
    const key = [medicine.trade_name, medicine.inn ?? "", baseSummaries.get(medicine.source_id) ?? ""]
      .join("|")
      .normalize("NFKC")
      .toLocaleLowerCase();
    groups.set(key, [...(groups.get(key) ?? []), medicine]);
  }

  for (const group of groups.values()) {
    if (group.length < 2) continue;
    for (const medicine of group) {
      const base = baseSummaries.get(medicine.source_id) ?? "";
      const registration = medicine.registration_number?.trim();
      const manufacturer = medicine.manufacturer?.trim();
      const differentiator = [registration, manufacturer].filter(Boolean).join(" · ")
        || medicine.source_id.slice(-8);
      baseSummaries.set(medicine.source_id, [base, differentiator].filter(Boolean).join(" · "));
    }
  }
  return baseSummaries;
}
