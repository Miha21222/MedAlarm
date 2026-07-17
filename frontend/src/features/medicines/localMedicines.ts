// Pure domain logic + localStorage I/O for medicines. Ported from PocketMind's
// features/tasks/localTasks.ts, drastically simplified: MedAlarm has no
// client-side timing/recurrence engine (reminders are computed server-side by
// APScheduler), so this file only needs CRUD shaping, storage read/write, and
// the last-write-wins merge, not PocketMind's applyTiming()/recurrence
// machinery. Kept free of any network/api import (unlike
// localMedicineRepository.ts) so it stays testable in the plain-node test
// harness without pulling in Vite's `import.meta.env`.
import type { Medicine, ScheduleSlot } from "../../types";

export const STORAGE_KEY = "medalarm.medicines.v1";

export function readMedicineStore(storage: Pick<Storage, "getItem"> = localStorage): Medicine[] {
  try {
    const parsed = JSON.parse(storage.getItem(STORAGE_KEY) ?? "[]");
    return Array.isArray(parsed) ? parsed : [];
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
  return {
    ...existing,
    ...input,
    catalog: input.catalog ?? null,
    updated_at: new Date().toISOString(),
    deleted_at: null,
    syncState: "pending",
  };
}

export function deleteMedicine(medicine: Medicine): Medicine {
  const now = new Date().toISOString();
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

export function isMedicineVisible(medicine: Medicine): boolean {
  return medicine.deleted_at === null;
}

export function sortMedicines<T extends { schedules: ScheduleSlot[] }>(items: T[]): T[] {
  return [...items].sort((left, right) =>
    (left.schedules[0]?.time || "").localeCompare(right.schedules[0]?.time || ""),
  );
}
