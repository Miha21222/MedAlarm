import { buildTodayPlan } from "../src/features/dashboard/todayPlan";
import type { Medicine } from "../src/types";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

function medicine(overrides: Partial<Medicine>): Medicine {
  return {
    client_medicine_id: "daily",
    name: "Daily",
    dosage_text: "1",
    comment: null,
    is_active: true,
    updated_at: "2026-07-01T00:00:00.000Z",
    deleted_at: null,
    schedules: [{ time: "08:00", days_of_week: "*" }],
    ...overrides,
  };
}

// At this instant it is already Tuesday in Kyiv but still Monday in UTC.
const now = new Date("2026-07-06T21:30:00.000Z");
const history = [
  {
    event_id: "local-tuesday-2026-07-07-09:00",
    medicine: "Tuesday",
    scheduled_at: "2026-07-07T06:00:00.000Z",
    responded_at: "2026-07-06T21:31:00.000Z",
    status: "taken",
  },
];
const storage = {
  getItem: (key: string) => key === "medalarm.intakeHistory.v1" ? JSON.stringify(history) : null,
};
const medicines = [
  medicine({
    client_medicine_id: "tuesday",
    name: "Tuesday",
    schedules: [
      { time: "09:00", days_of_week: "1" },
      { time: "21:00", days_of_week: "1" },
    ],
  }),
  medicine({ client_medicine_id: "monday", schedules: [{ time: "10:00", days_of_week: "0" }] }),
  medicine({ client_medicine_id: "daily", schedules: [{ time: "08:00", days_of_week: "*" }] }),
  medicine({ client_medicine_id: "inactive", is_active: false }),
  medicine({ client_medicine_id: "deleted", deleted_at: "2026-07-01T00:00:00.000Z" }),
];

const plan = buildTodayPlan(medicines, "Europe/Kyiv", now, storage);
assert(plan.length === 3, "today plan includes every due slot and excludes inactive, deleted, and wrong-weekday medicines");
assert(plan.every((item) => item.dose_key.includes("2026-07-07")), "dose keys use the configured timezone's day");
assert(!plan.some((item) => item.client_medicine_id === "monday"), "weekday selection uses the configured timezone");
assert(plan.find((item) => item.dose_key.endsWith("09:00"))?.scheduled_at === "2026-07-07T06:00:00.000Z", "scheduled time is converted from the configured timezone to UTC");
assert(plan.find((item) => item.dose_key.endsWith("09:00"))?.status === "taken", "each local dose picks up its matching action status");
assert(plan.find((item) => item.dose_key.endsWith("21:00"))?.status === "pending", "other slots remain independent and pending");
assert(new Set(plan.map((item) => item.dose_key)).size === plan.length, "multiple daily slots have independent stable keys");

const creationTime = new Date("2026-07-07T12:00:30.000Z"); // 15:00 in Kyiv
const newlyCreated = medicine({
  client_medicine_id: "new",
  created_at: creationTime.toISOString(),
  updated_at: creationTime.toISOString(),
  schedules: [
    { time: "09:00", days_of_week: "*" },
    { time: "15:00", days_of_week: "*" },
    { time: "16:00", days_of_week: "*" },
  ],
});
const catalogueCreated: Medicine = {
  ...newlyCreated,
  client_medicine_id: "catalogue-new",
  name: "Catalogue medicine",
  catalog: {
    source: "moh_state_register",
    source_id: "record-1",
    trade_name: "Catalogue medicine",
    inn: null,
    form: null,
    dispensing_conditions: null,
    active_ingredients: null,
    pharmacotherapeutic_group: null,
    atc_codes: null,
    applicant: null,
    manufacturer: null,
    registration_number: null,
    valid_from: null,
    valid_until: null,
    early_termination: null,
    instruction_url: null,
  },
};
const creationDayPlan = buildTodayPlan([newlyCreated, catalogueCreated], "Europe/Kyiv", creationTime, storage);
const manualTimes = creationDayPlan
  .filter((item) => item.client_medicine_id === newlyCreated.client_medicine_id)
  .map((item) => item.schedules[0].time);
const catalogueTimes = creationDayPlan
  .filter((item) => item.client_medicine_id === catalogueCreated.client_medicine_id)
  .map((item) => item.schedules[0].time);
assert(
  manualTimes.join(",") === "15:00,16:00",
  "a newly created medicine starts today only for intake times equal to or later than its creation minute",
);
assert(
  catalogueTimes.join(",") === manualTimes.join(","),
  "MOH catalogue medicines and manually entered medicines use identical dashboard eligibility rules",
);
const nextDayPlan = buildTodayPlan([newlyCreated, catalogueCreated], "Europe/Kyiv", new Date("2026-07-08T05:00:00.000Z"), storage);
assert(nextDayPlan.length === 6, "intake times skipped on the creation day appear for both entry methods from the next day onward");

console.log("todayPlan tests passed");
