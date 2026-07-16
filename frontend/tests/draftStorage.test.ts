import {
  hasMedicineDraft,
  readMedicineDraft,
  writeMedicineDraft,
} from "../src/features/medicines/draftStorage";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

const memory = new Map<string, string>();
const storage = {
  getItem: (key: string) => memory.get(key) ?? null,
  setItem: (key: string, value: string) => void memory.set(key, value),
  removeItem: (key: string) => void memory.delete(key),
};

writeMedicineDraft({
  context: "new",
  entryMode: "catalog",
  manual: {
    name: "Ибупрофен",
    amount: "1",
    unit: "таблетка",
    comment: "После еды",
    times: ["09:00"],
  },
  name: "АСПІРИН",
  amount: "2",
  unit: "таблетки",
  comment: "",
  times: ["18:00"],
  catalog: null,
}, storage);

const restored = readMedicineDraft("new", storage);
assert(restored?.entryMode === "catalog", "active entry mode should round-trip with the draft");
assert(restored.manual?.name === "Ибупрофен", "manual values should survive while the catalogue page is active");
assert(restored.manual.amount === "1", "the complete manual form should be preserved separately");
assert(hasMedicineDraft("new", storage), "restored input should count as a draft");
assert(readMedicineDraft("another", storage) === null, "a draft should only restore in its own context");

console.log("draftStorage tests passed");
