// Structured amount+unit dosage picker. Backend/storage still just sees a
// single `dosage_text` string, so this is a pure presentation-layer split —
// no data model change. Parsing existing free-text values is best-effort:
// unrecognized amounts/units are kept as an extra option rather than
// discarded, so old data never silently disappears from the picker.

export const DOSAGE_AMOUNTS = ["0.5", "1", "1.5", "2", "2.5", "3", "4", "5", "6", "8", "10"] as const;

export const DOSAGE_UNITS = ["таблетка", "капсула", "мл", "мг", "капля", "пакетик", "укол", "доза"] as const;

export function parseDosageText(dosageText: string): { amount: string; unit: string } {
  const trimmed = dosageText.trim();
  const match = trimmed.match(/^(\d+(?:[.,]\d+)?)\s*(.*)$/);
  if (!match) {
    return { amount: DOSAGE_AMOUNTS[1], unit: trimmed || DOSAGE_UNITS[0] };
  }
  const amount = match[1].replace(",", ".");
  const unit = match[2].trim() || DOSAGE_UNITS[0];
  return { amount, unit };
}

export function combineDosage(amount: string, unit: string): string {
  return `${amount} ${unit}`.trim();
}

export function dosageAmountOptions(current: string): string[] {
  const known: string[] = [...DOSAGE_AMOUNTS];
  return current && !known.includes(current) ? [current, ...known] : known;
}

export function dosageUnitOptions(current: string): string[] {
  const known: string[] = [...DOSAGE_UNITS];
  return current && !known.includes(current) ? [current, ...known] : known;
}
