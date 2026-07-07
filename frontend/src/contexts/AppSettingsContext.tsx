import { createContext, PropsWithChildren, useContext, useMemo, useState } from "react";
import { saveSettings } from "../api/settings";
import { readSettings, writeSettings } from "../features/storage";
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
  const [settings, setSettings] = useState<UserSettings>(() => initialSettings ?? readSettings());

  const value = useMemo<AppSettingsContextValue>(() => {
    const persist = (next: UserSettings) => {
      setSettings(next);
      writeSettings(next);
      void saveSettings(next);
    };

    return {
      settings,
      t: (key: TranslationKey) => translate(settings.language, key),
      setLanguage: (language: Language) => persist({ ...settings, language }),
      updateSettings: (patch: Partial<UserSettings>) => persist({ ...settings, ...patch }),
    };
  }, [settings]);

  return <AppSettingsContext.Provider value={value}>{children}</AppSettingsContext.Provider>;
}

export function useAppSettings(): AppSettingsContextValue {
  const context = useContext(AppSettingsContext);
  if (!context) {
    throw new Error("useAppSettings must be used within AppSettingsProvider");
  }
  return context;
}
