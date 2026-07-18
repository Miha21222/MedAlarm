import { createContext, PropsWithChildren, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { saveSettings } from "../api/settings";
import { useToast } from "./ToastContext";
import { readSettings, writeSettings } from "../features/storage";
import {
  clearPendingSettingsIfCurrent,
  readPendingSettings,
  writePendingSettings,
} from "../features/settingsSyncStorage";
import { translate, type TranslationKey } from "../i18n";
import type { Language, UserSettings } from "../types";

// Unlike PocketMind's client-only settings (which never sync directly and
// instead get snapshotted into each task's sync payload), MedAlarm's settings
// are server-owned and already synced directly via PATCH /settings/me — so
// there's no analogous localSettings.ts snapshot concept to port here, just a
// context wrapper around the existing read/write/save round trip.
type AppSettingsContextValue = {
  settings: UserSettings;
  t: (key: TranslationKey) => string;
  setLanguage: (language: Language) => void;
  updateSettings: (patch: Partial<UserSettings>) => void;
};

const AppSettingsContext = createContext<AppSettingsContextValue | null>(null);

export function AppSettingsProvider({
  initialSettings,
  children,
}: PropsWithChildren<{ initialSettings?: UserSettings }>) {
  const [settings, setSettings] = useState<UserSettings>(() => readPendingSettings() ?? initialSettings ?? readSettings());
  const { showToast } = useToast();
  const saveQueue = useRef<Promise<unknown>>(Promise.resolve());
  const queuedInitialRetry = useRef(false);

  const enqueueSave = useCallback((next: UserSettings) => {
    // Serialize full snapshots so a slower, older request cannot become the
    // final server value after a newer settings change. The pending snapshot
    // remains in localStorage until that exact version succeeds.
    saveQueue.current = saveQueue.current
      .catch(() => undefined)
      .then(() => saveSettings(next))
      .then(() => clearPendingSettingsIfCurrent(next))
      .catch(() => {
        showToast({ message: translate(next.language, "syncError"), tone: "error" });
      });
  }, [showToast]);

  useEffect(() => {
    if (queuedInitialRetry.current) return;
    queuedInitialRetry.current = true;
    const pending = readPendingSettings();
    if (pending) enqueueSave(pending);
  }, [enqueueSave]);

  const value = useMemo<AppSettingsContextValue>(() => {
    const persist = (next: UserSettings) => {
      setSettings(next);
      writeSettings(next);
      writePendingSettings(next);
      enqueueSave(next);
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
