export type Language = "ru" | "uk" | "en";
export type TextSize = "small" | "regular" | "large";
export type DoseStatus = "pending" | "taken" | "skipped" | "snoozed" | "missed";

export interface ScheduleSlot {
  time: string;
  days_of_week: string;
  snooze_minutes?: number;
  remind_until_confirmed?: boolean;
}

export interface MedicineCatalogReference {
  source: "moh_state_register";
  source_id: string;
  trade_name: string;
  inn: string | null;
  form: string | null;
  dispensing_conditions: string | null;
  active_ingredients: string | null;
  pharmacotherapeutic_group: string | null;
  atc_codes: string | null;
  applicant: string | null;
  manufacturer: string | null;
  registration_number: string | null;
  valid_from: string | null;
  valid_until: string | null;
  early_termination: string | null;
  instruction_url: string | null;
}

export interface Medicine {
  client_medicine_id: string;
  name: string;
  dosage_text: string;
  comment: string | null;
  catalog?: MedicineCatalogReference | null;
  is_active: boolean;
  created_at?: string;
  updated_at: string;
  deleted_at: string | null;
  schedules: ScheduleSlot[];
  syncState?: "synced" | "pending" | "error";
}

export interface ReminderSettings {
  language: Language;
  timezone: string;
  default_snooze_minutes: number;
  remind_until_confirmed: boolean;
}

export interface UserSettings extends ReminderSettings {
  text_size: TextSize;
}

export interface ReminderEventState {
  client_medicine_id: string;
  time: string;
  days_of_week: string;
  status: DoseStatus;
  scheduled_at: string;
  event_id: string | null;
  actionable: boolean;
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
