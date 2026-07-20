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

// The concurrency-critical function, modeled on PocketMind's bootstrapTaskSync():
// pushes any locally-pending medicines, then re-reads the store fresh (not the
// pre-request snapshot) before merging the bootstrap response in, so a medicine
// deleted locally while this round trip is in flight isn't resurrected.
export async function bootstrapMedicineSync(): Promise<Medicine[]> {
  if (!hasAuthToken()) return listLocalMedicines();

  const remote = await bootstrapSync();
  const remoteIds = new Set(remote.map((medicine) => medicine.client_medicine_id));
  // Legacy installs could label a record "synced" even though it only existed
  // in that device's localStorage. Preserve and upload such records before the
  // server becomes the universal Telegram-account source for every device.
  const local = readMedicineStore().map((medicine) =>
    remoteIds.has(medicine.client_medicine_id)
      ? medicine
      : { ...medicine, syncState: "pending" as const },
  );
  const merged = mergeRemoteMedicines(local, remote);
  writeMedicineStore(merged);

  const pending = merged.filter((medicine) => medicine.syncState === "pending" || medicine.syncState === "error");
  if (pending.length > 0) {
    const remoteResults = await syncMedicineBatch(pending);
    const requestedById = new Map(pending.map((medicine) => [medicine.client_medicine_id, medicine]));
    const remoteById = new Map(remoteResults.map((medicine) => [medicine.client_medicine_id, medicine]));
    const settled = readMedicineStore().map((current) => {
      const requested = requestedById.get(current.client_medicine_id);
      return requested
        ? settleMedicineSync(current, requested, remoteById.get(current.client_medicine_id))
        : current;
    });
    writeMedicineStore(settled);
  }

  return listLocalMedicines();
}
