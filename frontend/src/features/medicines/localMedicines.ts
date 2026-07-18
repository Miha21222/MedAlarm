// Pure domain logic + localStorage I/O for medicines. Ported from PocketMind's
// features/tasks/localTasks.ts, drastically simplified: MedAlarm has no
// client-side timing/recurrence engine (reminders are computed server-side by
// APScheduler), so this file only needs CRUD shaping, storage read/write, and
// the last-write-wins merge, not PocketMind's applyTiming()/recurrence
// machinery. Kept free of any network/api import (unlike
// localMedicineRepository.ts) so it stays testable in the plain-node test
// harness without pulling in Vite's `import.meta.env`.
import { z } from "zod";
import type { Medicine, ScheduleSlot } from "../../types";

const nullableText = z.string().nullable();
const catalogSchema = z.object({
  source: z.literal("moh_state_register"),
  source_id: z.string().min(1),
  trade_name: z.string().min(1),
  inn: nullableText,
  form: nullableText,
  dispensing_conditions: nullableText,
  active_ingredients: nullableText,
  pharmacotherapeutic_group: nullableText,
  atc_codes: nullableText,
  applicant: nullableText,
  manufacturer: nullableText,
  registration_number: nullableText,
  valid_from: nullableText,
  valid_until: nullableText,
  early_termination: nullableText,
  instruction_url: nullableText,
});
const scheduleSchema = z.object({
  time: z.string().regex(/^(?:[01]\d|2[0-3]):[0-5]\d$/),
  days_of_week: z.string().regex(/^(?:\*|[0-6](?:,[0-6])*)$/),
  snooze_minutes: z.number().int().min(1).max(180).optional(),
  remind_until_confirmed: z.boolean().optional(),
});
const medicineSchema = z.object({
  client_medicine_id: z.string().min(1).max(64),
  name: z.string().min(1),
  dosage_text: z.string().min(1),
  comment: z.string().nullable(),
  catalog: catalogSchema.nullable().optional(),
  is_active: z.boolean(),
  created_at: z.string().datetime({ offset: true }).optional(),
  updated_at: z.string().datetime({ offset: true }),
  deleted_at: z.string().datetime({ offset: true }).nullable(),
  schedules: z.array(scheduleSchema).max(24),
  syncState: z.enum(["synced", "pending", "error"]).optional(),
});

export const STORAGE_KEY = "medalarm.medicines.v1";

function nextTimestamp(previous: string): string {
  const parsed = Date.parse(previous);
  return new Date(Math.max(Date.now(), Number.isFinite(parsed) ? parsed + 1 : 0)).toISOString();
}

export function readMedicineStore(storage: Pick<Storage, "getItem"> = localStorage): Medicine[] {
  try {
    const parsed: unknown = JSON.parse(storage.getItem(STORAGE_KEY) ?? "[]");
    if (!Array.isArray(parsed)) return [];
    return parsed.flatMap((item) => {
      const result = medicineSchema.safeParse(item);
      return result.success ? [result.data as Medicine] : [];
    });
  } catch {
    return [];
  }
}

export function writeMedicineStore(medicines: Medicine[], storage: Pick<Storage, "setItem"> = localStorage): void {
  storage.setItem(STORAGE_KEY, JSON.stringify(medicines));
}

export function createMedicine(
  input: Pick<Medicine, "name" | "dosage_text" | "comment" | "schedules" | "catalog">,
  createdAt = new Date(),
): Medicine {
  const now = createdAt.toISOString();
  return {
    ...input,
    catalog: input.catalog ?? null,
    client_medicine_id: crypto.randomUUID(),
    is_active: true,
    created_at: now,
    updated_at: now,
    deleted_at: null,
    syncState: "pending",
  };
}

export function updateMedicine(
  existing: Medicine,
  input: Pick<Medicine, "name" | "dosage_text" | "comment" | "schedules" | "catalog">,
): Medicine {
  const updatedAt = nextTimestamp(existing.updated_at);
  return {
    ...existing,
    ...input,
    catalog: input.catalog ?? null,
    updated_at: updatedAt,
    deleted_at: null,
    syncState: "pending",
  };
}

export function deleteMedicine(medicine: Medicine): Medicine {
  const now = nextTimestamp(medicine.updated_at);
  return {
    ...medicine,
    is_active: false,
    deleted_at: now,
    updated_at: now,
    syncState: "pending",
  };
}

export function mergeRemoteMedicineIntoLocal(local: Medicine | undefined, remote: Medicine): Medicine {
  if (!local || Date.parse(remote.updated_at) > Date.parse(local.updated_at)) {
    return { ...remote, syncState: "synced" };
  }
  return local;
}

export function mergeRemoteMedicines(local: Medicine[], remote: Medicine[]): Medicine[] {
  const merged = new Map(local.map((medicine) => [medicine.client_medicine_id, medicine]));
  for (const remoteMedicine of remote) {
    const current = merged.get(remoteMedicine.client_medicine_id);
    merged.set(remoteMedicine.client_medicine_id, mergeRemoteMedicineIntoLocal(current, remoteMedicine));
  }
  return [...merged.values()];
}

export function settleMedicineSync(
  current: Medicine | undefined,
  requested: Medicine,
  remote?: Medicine,
): Medicine {
  // A slower request for an older edit must never overwrite a newer local edit,
  // whether that request eventually succeeds or fails.
  if (current && Date.parse(current.updated_at) > Date.parse(requested.updated_at)) return current;
  if (remote && Date.parse(remote.updated_at) >= Date.parse(requested.updated_at)) {
    return { ...remote, syncState: "synced" };
  }
  return { ...(current ?? requested), syncState: "error" };
}

export function isMedicineVisible(medicine: Medicine): boolean {
  return medicine.deleted_at === null;
}

export function sortMedicines<T extends { schedules: ScheduleSlot[] }>(items: T[]): T[] {
  return [...items].sort((left, right) =>
    (left.schedules[0]?.time || "").localeCompare(right.schedules[0]?.time || ""),
  );
}
