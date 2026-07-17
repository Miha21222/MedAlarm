import type { DoseStatus, HistoryItem, Medicine, MedicineCatalogReference, ScheduleSlot } from "../../types";
import { addDaysToDayKey, getZonedDayRange, zonedDateTimeToUtcTimestamp, zonedDayKeyFromTimestamp } from "../../utils/dateTime";
import { PREVIEW_CATALOG_MEDICINES } from "../demo/previewCatalog";

type PreviewInput = {
  id: string;
  name: string;
  dosage_text: string;
  comment: string | null;
  schedules: ScheduleSlot[];
  catalog?: MedicineCatalogReference;
  is_active?: boolean;
  syncState?: Medicine["syncState"];
};

const PREVIEW_INPUTS: PreviewInput[] = [
  {
    id: "moh-aspirin-cardio",
    name: "АСПІРИН КАРДІО®",
    dosage_text: "1 таблетка",
    comment: "Демо лекарства, выбранного из реестра МОЗ. Количество и время введены пользователем.",
    schedules: [{ time: "11:30", days_of_week: "*" }],
    catalog: PREVIEW_CATALOG_MEDICINES[0],
    syncState: "synced",
  },
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
  const createdAt = new Date(now.getTime() - 24 * 60 * 60 * 1000).toISOString();
  return PREVIEW_INPUTS.map((item) => ({
    client_medicine_id: `preview-${item.id}`,
    name: item.name,
    dosage_text: item.dosage_text,
    comment: item.comment,
    catalog: item.catalog ?? null,
    schedules: item.schedules,
    is_active: item.is_active ?? true,
    created_at: createdAt,
    updated_at: updatedAt,
    deleted_at: null,
    syncState: item.syncState,
  }));
}

// Historical fixtures stay deterministic, while four resolved entries are also
// placed earlier in the user's current day so the History page's "Today" and
// status filters can be exercised without changing the Dashboard's independent
// pending/action state.
const HISTORY_STATUS_CYCLE: DoseStatus[] = ["taken", "taken", "taken", "skipped", "missed", "snoozed"];
const TODAY_HISTORY_STATUSES: DoseStatus[] = ["taken", "skipped", "missed", "snoozed"];
const HISTORY_DAY_SPAN = 10;

export function buildPreviewHistory(
  now = new Date(),
  timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
): HistoryItem[] {
  const items: HistoryItem[] = [];
  const todayKey = zonedDayKeyFromTimestamp(now.getTime(), timezone);
  PREVIEW_INPUTS.forEach((medicineInput, medicineIndex) => {
    const time = medicineInput.schedules[0]?.time ?? "09:00";
    for (let dayOffset = 1; dayOffset <= HISTORY_DAY_SPAN; dayOffset++) {
      const dayKey = addDaysToDayKey(todayKey, -dayOffset);
      const scheduledTimestamp = zonedDateTimeToUtcTimestamp(dayKey, time, timezone);
      if (scheduledTimestamp === null) continue;
      const status = HISTORY_STATUS_CYCLE[(medicineIndex + dayOffset) % HISTORY_STATUS_CYCLE.length];
      items.push({
        event_id: `demo-history-${medicineInput.id}-${dayOffset}`,
        medicine: medicineInput.name,
        scheduled_at: new Date(scheduledTimestamp).toISOString(),
        responded_at: new Date(scheduledTimestamp + 4 * 60 * 1000).toISOString(),
        status,
      });
    }
  });

  const todayRange = getZonedDayRange(now, timezone);
  const elapsedToday = now.getTime() - todayRange.start;
  if (elapsedToday > 0) {
    TODAY_HISTORY_STATUSES.forEach((status, index) => {
      const medicineInput = PREVIEW_INPUTS[index];
      const scheduledTimestamp = todayRange.start + Math.floor(elapsedToday * ((index + 1) / 5));
      items.push({
        event_id: `demo-history-today-${medicineInput.id}-${status}`,
        medicine: medicineInput.name,
        scheduled_at: new Date(scheduledTimestamp).toISOString(),
        responded_at: new Date(Math.min(scheduledTimestamp + 4 * 60 * 1000, now.getTime())).toISOString(),
        status,
      });
    });
  }

  return items.sort((left, right) => Date.parse(right.scheduled_at) - Date.parse(left.scheduled_at));
}
