import type { MedicineCatalogReference } from "../../types";

// Autosaves in-progress medicine-form input so navigating away accidentally
// doesn't lose it, mirroring PocketMind's task-create draft pattern. Keyed by
// `context` (the medicineId being edited, or "new") so a stale draft from a
// different medicine/create session is never restored into the wrong form.

const DRAFT_KEY = "medalarm.medicineDraft.v1";

export interface MedicineDraft {
  context: string;
  name: string;
  amount: string;
  unit: string;
  comment: string;
  times: string[];
  catalog?: MedicineCatalogReference | null;
}

export function readMedicineDraft(context: string): MedicineDraft | null {
  try {
    const raw = localStorage.getItem(DRAFT_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<MedicineDraft> | null;
    if (!parsed || typeof parsed !== "object" || parsed.context !== context) return null;
    return parsed as MedicineDraft;
  } catch {
    return null;
  }
}

export function writeMedicineDraft(draft: MedicineDraft): void {
  try {
    localStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
  } catch {
    // best-effort; losing a draft is not fatal
  }
}

export function clearMedicineDraft(): void {
  try {
    localStorage.removeItem(DRAFT_KEY);
  } catch {
    // ignore
  }
}

// A draft is written on every keystroke, including the very first render of a
// blank form — so "exists" alone would flag every visit to the form, not just
// ones with actual unsaved progress. Require a non-empty name instead.
export function hasMedicineDraft(context: string): boolean {
  const draft = readMedicineDraft(context);
  return draft !== null && draft.name.trim().length > 0;
}
