import { buildPreviewHistory, buildPreviewMedicines } from "../src/features/medicines/previewMedicines";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

const now = new Date("2026-07-07T09:00:00.000Z");
const medicines = buildPreviewMedicines(now);

assert(medicines.length >= 8, "preview should include a broad medicine set");
assert(
  new Set(medicines.flatMap((medicine) => medicine.schedules.map((slot) => slot.time))).size >= 10,
  "preview should include varied reminder times",
);
assert(medicines.some((medicine) => medicine.schedules.length > 1), "preview should include multi-time medicines");
assert(medicines.some((medicine) => !medicine.is_active), "preview should include an inactive medicine");
assert(medicines.some((medicine) => medicine.syncState === "error"), "preview should include an error sync state");
assert(medicines.some((medicine) => medicine.comment), "preview should include comments");
assert(
  medicines.every((medicine) => medicine.client_medicine_id.startsWith("preview-")),
  "preview records should use stable preview ids",
);

const history = buildPreviewHistory(now);

assert(history.length > 20, "preview history should span many days across many medicines");
assert(
  history.every((item) => Date.parse(item.scheduled_at) < now.getTime()),
  "preview history should only cover days before today, leaving today's demo doses pending",
);
assert(
  new Set(history.map((item) => item.medicine)).size >= 8,
  "preview history should cover most demo medicines, not just one",
);
for (const status of ["taken", "skipped", "missed", "snoozed"] as const) {
  assert(history.some((item) => item.status === status), `preview history should include a ${status} entry`);
}
assert(
  history.every((item, index) => index === 0 || Date.parse(history[index - 1].scheduled_at) >= Date.parse(item.scheduled_at)),
  "preview history should be sorted newest first",
);
assert(new Set(history.map((item) => item.event_id)).size === history.length, "preview history event ids should be unique");

console.log("previewMedicines tests passed");
