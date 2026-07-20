import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Medicine } from "../../src/types";

const { bootstrapSync, syncMedicine, syncMedicineBatch } = vi.hoisted(() => ({
  bootstrapSync: vi.fn<() => Promise<Medicine[]>>(),
  syncMedicine: vi.fn(),
  syncMedicineBatch: vi.fn<(medicines: Medicine[]) => Promise<Medicine[]>>(),
}));

vi.mock("../../src/api/client", () => ({ hasAuthToken: () => true }));
vi.mock("../../src/api/sync", () => ({ bootstrapSync, syncMedicine, syncMedicineBatch }));
vi.mock("../../src/features/demo/demoMode", () => ({ isDemoModeEnabled: () => false }));

import { bootstrapMedicineSync } from "../../src/features/medicines/localMedicineRepository";
import {
  activateMedicineStore,
  medicineStorageKeyForTelegramUser,
} from "../../src/features/medicines/localMedicines";

function medicine(id: string, name: string): Medicine {
  return {
    client_medicine_id: id,
    name,
    dosage_text: "1 таблетка",
    comment: null,
    catalog: null,
    is_active: true,
    created_at: "2026-07-20T08:00:00.000Z",
    updated_at: "2026-07-20T08:00:00.000Z",
    deleted_at: null,
    schedules: [{ time: "09:00", days_of_week: "*" }],
    syncState: "synced",
  };
}

describe("multi-device medicine bootstrap", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it("pushes every local record and adopts the complete account snapshot", async () => {
    const local = medicine("phone-record", "Аспигрель");
    const remoteOnly = medicine("desktop-record", "Ессенциале");
    const telegramId = 1001;
    localStorage.setItem("medalarm.medicines.v1", JSON.stringify([local]));
    activateMedicineStore(telegramId);
    syncMedicineBatch.mockResolvedValue([local, remoteOnly]);

    const result = await bootstrapMedicineSync();

    expect(syncMedicineBatch).toHaveBeenCalledWith([expect.objectContaining({ client_medicine_id: local.client_medicine_id })]);
    expect(bootstrapSync).not.toHaveBeenCalled();
    expect(result.map((item) => item.client_medicine_id).sort()).toEqual(["desktop-record", "phone-record"]);
    const stored = JSON.parse(localStorage.getItem(medicineStorageKeyForTelegramUser(telegramId)) ?? "[]") as Medicine[];
    expect(stored.map((item) => item.client_medicine_id).sort()).toEqual(["desktop-record", "phone-record"]);
  });
});
