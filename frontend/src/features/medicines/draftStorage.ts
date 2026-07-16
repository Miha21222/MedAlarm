import type { MedicineCatalogReference } from "../../types";

// Autosaves in-progress medicine-form input so navigating away accidentally
// doesn't lose it, mirroring PocketMind's task-create draft pattern. Keyed by
// `context` (the medicineId being edited, or "new") so a stale draft from a
// different medicine/create session is never restored into the wrong form.

const DRAFT_KEY = "medalarm.medicineDraft.v1";

type DraftStorage = Pick<Storage, "getItem" | "setItem" | "removeItem">;

export type MedicineEntryMode = "catalog" | "manual";

export interface ManualMedicineDraftValues {
  name: string;
  amount: string;
  unit: string;
  comment: string;
  times: string[];
}

export interface MedicineDraft {
  context: string;
  entryMode?: MedicineEntryMode;
  manual?: ManualMedicineDraftValues;
  name: string;
  amount: string;
  unit: string;
  comment: string;
  times: string[];
  catalog?: MedicineCatalogReference | null;
}

export function readMedicineDraft(context: string, storage: DraftStorage = localStorage): MedicineDraft | null {
  try {
    const raw = storage.getItem(DRAFT_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<MedicineDraft> | null;
    if (!parsed || typeof parsed !== "object" || parsed.context !== context) return null;
    return parsed as MedicineDraft;
  } catch {
    return null;
  }
}

export function writeMedicineDraft(draft: MedicineDraft, storage: DraftStorage = localStorage): void {
  try {
    storage.setItem(DRAFT_KEY, JSON.stringify(draft));
  } catch {
    // best-effort; losing a draft is not fatal
  }
}

export function clearMedicineDraft(storage: DraftStorage = localStorage): void {
  try {
    storage.removeItem(DRAFT_KEY);
  } catch {
    // ignore
  }
}

// A draft is written on every keystroke, including the very first render of a
// blank form — so "exists" alone would flag every visit to the form, not just
// ones with actual unsaved progress. Require a non-empty name instead.
export function hasMedicineDraft(context: string, storage: DraftStorage = localStorage): boolean {
  const draft = readMedicineDraft(context, storage);
  return draft !== null && draft.name.trim().length > 0;
}
