export type Language = "ru" | "uk" | "en";
export type DoseStatus = "pending" | "taken" | "skipped" | "snoozed" | "missed";

export interface ScheduleSlot {
  time: string;
  days_of_week: string;
  snooze_minutes?: number;
  remind_until_confirmed?: boolean;
}

export interface Medicine {
  client_medicine_id: string;
  name: string;
  dosage_text: string;
  comment: string | null;
  is_active: boolean;
  updated_at: string;
  deleted_at: string | null;
  schedules: ScheduleSlot[];
  syncState?: "synced" | "pending" | "error";
}

export interface UserSettings {
  language: Language;
  timezone: string;
  default_snooze_minutes: number;
  remind_until_confirmed: boolean;
}

export interface TodayItem extends Medicine {
  status: DoseStatus;
  dose_key: string;
  scheduled_at: string;
  event_id: string | null;
  actionable: boolean;
}

export interface HistoryItem {
  event_id: string | null;
  medicine: string;
  scheduled_at: string;
  responded_at: string;
  status: DoseStatus;
}
