import { buildPreviewMedicines } from "../src/features/medicines/previewMedicines";
import {
  readLocalIntakeHistory,
  resolveLocalDoseAction,
  statusForToday,
} from "../src/features/medicines/localIntakeHistory";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

const memory = new Map<string, string>();
const storage = {
  getItem: (key: string) => memory.get(key) ?? null,
  setItem: (key: string, value: string) => void memory.set(key, value),
};
const now = new Date("2026-07-07T09:15:00.000Z");
const medicine = buildPreviewMedicines(now).find((item) => item.client_medicine_id === "preview-two-times");
assert(medicine, "preview medicine should exist");

const taken = resolveLocalDoseAction(medicine, "taken", "Europe/Kyiv", storage, now);
assert(taken.status === "taken", "taken action should create taken history");
assert(statusForToday(medicine, "Europe/Kyiv", storage, now) === "taken", "today status should reflect action");

const repeat = resolveLocalDoseAction(medicine, "skipped", "Europe/Kyiv", storage, now);
assert(repeat.status === "taken", "repeated action on same dose should be idempotent");

const history = readLocalIntakeHistory("month", storage, now);
assert(history.length === 1, "idempotent action should leave one history item");
assert(history[0].medicine === medicine.name, "history should keep the medicine name");
assert(history[0].event_id === taken.event_id, "history should keep stable event id");

console.log("localIntakeHistory tests passed");
