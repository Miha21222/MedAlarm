import {
  createMedicine,
  deleteMedicine,
  mergeRemoteMedicineIntoLocal,
  mergeRemoteMedicines,
  readMedicineStore,
  updateMedicine,
  writeMedicineStore,
} from "../src/features/medicines/localMedicines";
import type { Medicine } from "../src/types";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

const memory = new Map<string, string>();
const storage = {
  getItem: (key: string) => memory.get(key) ?? null,
  setItem: (key: string, value: string) => void memory.set(key, value),
};

const medicine = createMedicine({
  name: "Vitamin D",
  dosage_text: "1 capsule",
  comment: null,
  schedules: [{ time: "09:00", days_of_week: "*" }],
});
writeMedicineStore([medicine], storage);
assert(readMedicineStore(storage)[0].name === "Vitamin D", "medicine should round-trip");
assert(medicine.created_at === medicine.updated_at, "new medicine should retain its creation timestamp");
assert(medicine.catalog === null, "manual medicines should normalize an absent catalogue reference to null");

const catalogMedicine = createMedicine({
  name: "АСПІРИН КАРДІО®",
  dosage_text: "1 таблетка",
  comment: null,
  schedules: [{ time: "09:00", days_of_week: "*" }],
  catalog: {
    source: "moh_state_register",
    source_id: "record-1",
    trade_name: "АСПІРИН КАРДІО®",
    inn: "Acetylsalicylic acid",
    form: "таблетки по 100 мг №28",
    dispensing_conditions: "без рецепта",
    active_ingredients: "ацетилсаліцилова кислота",
    pharmacotherapeutic_group: "Антитромботичні засоби",
    atc_codes: "B01AC06",
    applicant: "Applicant",
    manufacturer: "Manufacturer",
    registration_number: "UA/7802/01/01",
    valid_from: "01.01.2025",
    valid_until: "необмежений",
    early_termination: "Ні",
    instruction_url: "https://example.test/instruction",
  },
});
assert(catalogMedicine.catalog?.registration_number === "UA/7802/01/01", "catalog metadata should be retained");
assert(catalogMedicine.is_active === medicine.is_active, "catalogue and manual medicines should share activation rules");
assert(catalogMedicine.schedules[0].time === medicine.schedules[0].time, "catalogue and manual medicines should retain schedules identically");
assert(Boolean(catalogMedicine.created_at) === Boolean(medicine.created_at), "both entry methods should retain creation timestamps");

const deleted = deleteMedicine(medicine);
assert(deleted.deleted_at !== null && deleted.is_active === false, "delete should create tombstone");

const newer: Medicine = {
  ...medicine,
  name: "Vitamin D3",
  updated_at: new Date(Date.parse(medicine.updated_at) + 1000).toISOString(),
};
assert(mergeRemoteMedicines([medicine], [newer])[0].name === "Vitamin D3", "newer remote wins");

const updated = updateMedicine(medicine, {
  name: "Vitamin D (updated)",
  dosage_text: medicine.dosage_text,
  comment: "taken with food",
  schedules: medicine.schedules,
});
assert(updated.name === "Vitamin D (updated)", "updateMedicine should apply the new fields");
assert(updated.syncState === "pending", "updateMedicine should mark the record pending");
assert(Date.parse(updated.updated_at) >= Date.parse(medicine.updated_at), "updateMedicine should bump updated_at");

const older: Medicine = {
  ...medicine,
  name: "Vitamin D (stale)",
  updated_at: new Date(Date.parse(medicine.updated_at) - 1000).toISOString(),
};
assert(
  mergeRemoteMedicineIntoLocal(medicine, older).name === "Vitamin D",
  "mergeRemoteMedicineIntoLocal should keep local when remote is older",
);
assert(
  mergeRemoteMedicineIntoLocal(medicine, newer).syncState === "synced",
  "mergeRemoteMedicineIntoLocal should mark the winning remote record synced",
);
assert(
  mergeRemoteMedicineIntoLocal(undefined, medicine).client_medicine_id === medicine.client_medicine_id,
  "mergeRemoteMedicineIntoLocal should adopt a remote-only record",
);

console.log("localMedicines tests passed");
