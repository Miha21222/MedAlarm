import { createContext, PropsWithChildren, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { saveReminderSettings } from "../api/settings";
import {
  clearPendingSettingsIfCurrent,
  readPendingSettings,
  reminderSettingsFrom,
  writePendingSettings,
} from "../features/settingsSyncStorage";
import { readSettings, writeSettings } from "../features/storage";
import { translate, type TranslationKey } from "../i18n";
import type { Language, ReminderSettings, UserSettings } from "../types";
import { useToast } from "./ToastContext";

type AppSettingsContextValue = {
  settings: UserSettings;
  t: (key: TranslationKey) => string;
  setLanguage: (language: Language) => void;
  updateSettings: (patch: Partial<UserSettings>) => void;
};

const AppSettingsContext = createContext<AppSettingsContextValue | null>(null);

function sameReminderSettings(left: ReminderSettings, right: ReminderSettings): boolean {
  return JSON.stringify(left) === JSON.stringify(right);
}

export function AppSettingsProvider({ children }: PropsWithChildren) {
  // The browser owns app settings. The server receives only the projection it
  // needs while the Mini App is closed to schedule and render reminders.
  const [settings, setSettings] = useState<UserSettings>(() => readSettings());
  const { showToast } = useToast();
  const saveQueue = useRef<Promise<unknown>>(Promise.resolve());
  const queuedInitialSync = useRef(false);

  const enqueueSave = useCallback((next: ReminderSettings) => {
    saveQueue.current = saveQueue.current
      .catch(() => undefined)
      .then(() => saveReminderSettings(next))
      .then(() => clearPendingSettingsIfCurrent(next))
      .catch(() => {
        showToast({ message: translate(next.language, "syncError"), tone: "error" });
      });
  }, [showToast]);

  useEffect(() => {
    if (queuedInitialSync.current) return;
    queuedInitialSync.current = true;
    const snapshot = readPendingSettings() ?? reminderSettingsFrom(readSettings());
    writePendingSettings(snapshot);
    enqueueSave(snapshot);
  }, [enqueueSave]);

  const value = useMemo<AppSettingsContextValue>(() => {
    const persist = (next: UserSettings) => {
      const previousReminderSettings = reminderSettingsFrom(settings);
      const nextReminderSettings = reminderSettingsFrom(next);
      setSettings(next);
      writeSettings(next);

      // Text size and other UI-only preferences never cross the network.
      if (!sameReminderSettings(previousReminderSettings, nextReminderSettings)) {
        writePendingSettings(nextReminderSettings);
        enqueueSave(nextReminderSettings);
      }
    };

    return {
      settings,
      t: (key: TranslationKey) => translate(settings.language, key),
      setLanguage: (language: Language) => persist({ ...settings, language }),
      updateSettings: (patch: Partial<UserSettings>) => persist({ ...settings, ...patch }),
    };
  }, [enqueueSave, settings]);

  return <AppSettingsContext.Provider value={value}>{children}</AppSettingsContext.Provider>;
}

export function useAppSettings(): AppSettingsContextValue {
  const context = useContext(AppSettingsContext);
  if (!context) {
    throw new Error("useAppSettings must be used within AppSettingsProvider");
  }
  return context;
}
