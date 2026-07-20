import type { Medicine } from "../types";
import { apiRequest } from "./client";

export async function bootstrapSync(): Promise<Medicine[]> {
  const result = await apiRequest<{ medicines: Medicine[] }>("/sync/bootstrap");
  return result.medicines;
}

export async function syncMedicine(clientMedicineId: string, payload: Medicine): Promise<Medicine> {
  const result = await apiRequest<{ applied: boolean; medicine: Medicine }>(
    `/sync/medicines/${clientMedicineId}`,
    { method: "PUT", body: JSON.stringify(payload) },
  );
  return result.medicine;
}

export async function syncMedicineBatch(medicines: Medicine[]): Promise<Medicine[]> {
  if (medicines.length === 0) return [];
  const result = await apiRequest<{ medicines: Medicine[] }>("/sync/batch", {
    method: "POST",
    body: JSON.stringify({ medicines }),
  });
  return result.medicines;
}
