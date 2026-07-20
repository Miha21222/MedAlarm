import { hasAuthToken } from "../../api/client";
import { bootstrapSync, syncMedicine, syncMedicineBatch } from "../../api/sync";
import type { Medicine } from "../../types";
import { isDemoModeEnabled } from "../demo/demoMode";
import {
  createMedicine as buildMedicine,
  deleteMedicine as tombstoneMedicine,
  isMedicineVisible,
  mergeRemoteMedicines,
  readMedicineStore,
  settleMedicineSync,
  sortMedicines,
  updateMedicine as applyMedicineUpdate,
  writeMedicineStore,
} from "./localMedicines";
import { buildPreviewMedicines } from "./previewMedicines";

function replaceMedicine(medicines: Medicine[], medicine: Medicine): Medicine[] {
  const next = medicines.filter((item) => item.client_medicine_id !== medicine.client_medicine_id);
  next.push(medicine);
  return next;
}

// Local-first: write to localStorage immediately, then fire the matching
// per-record network call. Network failures are swallowed and the medicine is
// marked "error" so the UI can surface it without blocking on connectivity.
async function persistWithSync(medicine: Medicine): Promise<Medicine> {
  // Demo mode is a read-only sandbox: edits to a demo medicine are reflected
  // back to the caller (so the UI doesn't appear broken) but never written to
  // the user's real store.
  if (isDemoModeEnabled()) return medicine;
  writeMedicineStore(replaceMedicine(readMedicineStore(), medicine));
  if (!hasAuthToken()) return medicine;
  try {
    const synced = await syncMedicine(medicine.client_medicine_id, medicine);
    const current = readMedicineStore().find(
      (item) => item.client_medicine_id === medicine.client_medicine_id,
    );
    const settled = settleMedicineSync(current, medicine, synced);
    writeMedicineStore(replaceMedicine(readMedicineStore(), settled));
    return settled;
  } catch {
    const current = readMedicineStore().find(
      (item) => item.client_medicine_id === medicine.client_medicine_id,
    );
    const failed = settleMedicineSync(current, medicine);
    writeMedicineStore(replaceMedicine(readMedicineStore(), failed));
    return failed;
  }
}

export function listLocalMedicines(): Medicine[] {
  if (isDemoModeEnabled()) return sortMedicines(buildPreviewMedicines().filter(isMedicineVisible));
  return sortMedicines(readMedicineStore().filter(isMedicineVisible));
}

export function getLocalMedicine(clientMedicineId: string): Medicine | undefined {
  if (isDemoModeEnabled()) {
    return buildPreviewMedicines().find((item) => item.client_medicine_id === clientMedicineId);
  }
  return readMedicineStore().find((item) => item.client_medicine_id === clientMedicineId);
}

export async function createLocalMedicine(
  input: Pick<Medicine, "name" | "dosage_text" | "comment" | "schedules" | "catalog">,
): Promise<Medicine> {
  return persistWithSync(buildMedicine(input));
}

export async function updateLocalMedicine(
  existing: Medicine,
  input: Pick<Medicine, "name" | "dosage_text" | "comment" | "schedules" | "catalog">,
): Promise<Medicine> {
  return persistWithSync(applyMedicineUpdate(existing, input));
}

export async function deleteLocalMedicine(medicine: Medicine): Promise<Medicine> {
  return persistWithSync(tombstoneMedicine(medicine));
}

// PocketMind's proven multi-device bootstrap: push the complete local snapshot
// first, receive the complete Telegram-account snapshot back, then merge it
// against a fresh local read so edits made during the request are not lost.
export async function bootstrapMedicineSync(): Promise<Medicine[]> {
  if (!hasAuthToken()) return listLocalMedicines();

  try {
    const local = readMedicineStore();
    const remote = local.length > 0
      ? await syncMedicineBatch(local)
      : await bootstrapSync();
    const merged = mergeRemoteMedicines(readMedicineStore(), remote);
    writeMedicineStore(merged);
    return sortMedicines(merged.filter(isMedicineVisible));
  } catch {
    return listLocalMedicines();
  }
}
