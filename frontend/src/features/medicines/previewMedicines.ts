import type { DoseStatus, HistoryItem, Medicine, ScheduleSlot } from "../../types";

type PreviewInput = {
  id: string;
  name: string;
  dosage_text: string;
  comment: string | null;
  schedules: ScheduleSlot[];
  is_active?: boolean;
  syncState?: Medicine["syncState"];
};

const PREVIEW_INPUTS: PreviewInput[] = [
  {
    id: "morning-tablet",
    name: "Демо: утренняя таблетка",
    dosage_text: "1 таблетка",
    comment: "После завтрака. Тест длинного комментария для карточки и экрана деталей.",
    schedules: [{ time: "07:30", days_of_week: "*" }],
    syncState: "synced",
  },
  {
    id: "two-times",
    name: "Демо: два раза в день",
    dosage_text: "2 капсулы",
    comment: "Проверка нескольких напоминаний в одной карточке.",
    schedules: [
      { time: "09:00", days_of_week: "*" },
      { time: "21:00", days_of_week: "*" },
    ],
    syncState: "pending",
  },
  {
    id: "liquid",
    name: "Демо: жидкая форма",
    dosage_text: "5 мл",
    comment: "Проверка единицы измерения мл.",
    schedules: [{ time: "10:15", days_of_week: "*" }],
    syncState: "synced",
  },
  {
    id: "weekday",
    name: "Демо: будни",
    dosage_text: "1 пакетик",
    comment: "Показывает расписание только по рабочим дням.",
    schedules: [{ time: "12:45", days_of_week: "0,1,2,3,4" }],
    syncState: "synced",
  },
  {
    id: "drops",
    name: "Демо: капли",
    dosage_text: "3 капля",
    comment: null,
    schedules: [
      { time: "08:00", days_of_week: "*" },
      { time: "14:00", days_of_week: "*" },
      { time: "20:00", days_of_week: "*" },
    ],
    syncState: "synced",
  },
  {
    id: "injection",
    name: "Демо: укол",
    dosage_text: "1 укол",
    comment: "Запись для проверки другой единицы дозировки.",
    schedules: [{ time: "18:30", days_of_week: "1,3,5" }],
    syncState: "error",
  },
  {
    id: "night",
    name: "Демо: поздний приём",
    dosage_text: "0.5 таблетка",
    comment: "Позднее время помогает проверить сортировку.",
    schedules: [{ time: "23:10", days_of_week: "*" }],
    syncState: "pending",
  },
  {
    id: "inactive",
    name: "Демо: неактивное лекарство",
    dosage_text: "10 мг",
    comment: "Проверка поля is_active в данных карточки (список его пока не отображает отдельно).",
    schedules: [{ time: "16:00", days_of_week: "*" }],
    is_active: false,
    syncState: "synced",
  },
  {
    id: "long-name",
    name: "Демо: очень длинное название лекарства для проверки переноса строки",
    dosage_text: "1 доза",
    comment: "Проверка плотной карточки и переносов текста.",
    schedules: [{ time: "06:50", days_of_week: "*" }],
    syncState: "synced",
  },
];

export function buildPreviewMedicines(now = new Date()): Medicine[] {
  const updatedAt = now.toISOString();
  return PREVIEW_INPUTS.map((item) => ({
    client_medicine_id: `preview-${item.id}`,
    name: item.name,
    dosage_text: item.dosage_text,
    comment: item.comment,
    schedules: item.schedules,
    is_active: item.is_active ?? true,
    updated_at: updatedAt,
    deleted_at: null,
    syncState: item.syncState,
  }));
}

// One entry per (medicine, day) for the last HISTORY_DAY_SPAN days — "today"
// (dayOffset 0) is deliberately excluded so the Dashboard's demo doses stay
// pending/interactive rather than pre-resolved. Status cycles deterministically
// (not randomly) so the fixture — and any test asserting on it — is stable.
const HISTORY_STATUS_CYCLE: DoseStatus[] = ["taken", "taken", "taken", "skipped", "missed", "snoozed"];
const HISTORY_DAY_SPAN = 10;

export function buildPreviewHistory(now = new Date()): HistoryItem[] {
  const items: HistoryItem[] = [];
  PREVIEW_INPUTS.forEach((medicineInput, medicineIndex) => {
    const [hours, minutes] = (medicineInput.schedules[0]?.time ?? "09:00").split(":").map(Number);
    for (let dayOffset = 1; dayOffset <= HISTORY_DAY_SPAN; dayOffset++) {
      const scheduled = new Date(now.getFullYear(), now.getMonth(), now.getDate() - dayOffset, hours, minutes, 0, 0);
      const status = HISTORY_STATUS_CYCLE[(medicineIndex + dayOffset) % HISTORY_STATUS_CYCLE.length];
      items.push({
        event_id: `demo-history-${medicineInput.id}-${dayOffset}`,
        medicine: medicineInput.name,
        scheduled_at: scheduled.toISOString(),
        responded_at: new Date(scheduled.getTime() + 4 * 60 * 1000).toISOString(),
        status,
      });
    }
  });
  return items.sort((left, right) => Date.parse(right.scheduled_at) - Date.parse(left.scheduled_at));
}
