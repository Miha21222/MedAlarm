import { searchPreviewCatalog, PREVIEW_CATALOG_MEDICINES } from "../src/features/demo/previewCatalog";
import { filterHistory } from "../src/features/history/historyAnalysis";
import { catalogCardSummary, catalogResultSummaries } from "../src/features/medicines/catalogPresentation";
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
  medicines.some((medicine) => medicine.catalog?.source === "moh_state_register"),
  "preview should include a medicine selected from the MOH catalogue",
);
assert(searchPreviewCatalog("аспирин").length >= 2, "preview catalogue search should normalize Russian spelling");
assert(searchPreviewCatalog("Ibuprofen").some((item) => item.inn === "Ibuprofen"), "preview catalogue should support Latin INN search");
assert(
  catalogCardSummary(PREVIEW_CATALOG_MEDICINES[0]) === "таблетки · 100 мг",
  "catalogue cards should reduce the official form to type and strength",
);
assert(
  catalogCardSummary({
    ...PREVIEW_CATALOG_MEDICINES[0],
    form: "таблетки, вкриті плівковою оболонкою; по 10 таблеток у блістері",
    active_ingredients: "1 таблетка містить 200 мг діючої речовини",
  }) === "таблетки · 200 мг · вкриті плівковою оболонкою",
  "catalogue cards should add a short form specification and use active ingredients as a strength fallback",
);
const ambiguousCatalogItems = [
  PREVIEW_CATALOG_MEDICINES[0],
  { ...PREVIEW_CATALOG_MEDICINES[0], source_id: "another", registration_number: "UA/other/01" },
];
const ambiguousSummaries = catalogResultSummaries(ambiguousCatalogItems);
assert(
  ambiguousSummaries.get("another")?.includes("UA/other/01"),
  "visually identical catalogue results should include a registration differentiator",
);
assert(
  medicines.every((medicine) => medicine.client_medicine_id.startsWith("preview-")),
  "preview records should use stable preview ids",
);

const history = buildPreviewHistory(now, "UTC");

assert(history.length > 20, "preview history should span many days across many medicines");
assert(
  history.every((item) => Date.parse(item.scheduled_at) < now.getTime()),
  "preview history should never contain future resolved intakes",
);
const todayHistory = filterHistory(history, { status: "all", period: "today", timezone: "UTC", now });
assert(todayHistory.length === 4, "preview history should include four mock intakes from today");
for (const status of ["taken", "skipped", "missed", "snoozed"] as const) {
  assert(todayHistory.some((item) => item.status === status), `today preview should include a ${status} intake`);
}
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
