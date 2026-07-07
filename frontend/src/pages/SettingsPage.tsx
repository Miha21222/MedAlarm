import { useAppSettings } from "../contexts/AppSettingsContext";
import type { Language } from "../types";

export function SettingsPage() {
  const { settings, updateSettings, t } = useAppSettings();

  return (
    <section className="page-stack">
      <div className="settings-card">
        <label>
          {t("language")}
          <select
            value={settings.language}
            onChange={(event) => updateSettings({ language: event.target.value as Language })}
          >
            <option value="ru">Русский</option>
            <option value="uk">Українська</option>
            <option value="en">English</option>
          </select>
        </label>
        <label>
          {t("timezone")}
          <input value={settings.timezone} onChange={(event) => updateSettings({ timezone: event.target.value })} />
        </label>
        <label>
          {t("snooze")}
          <div className="suffix-input">
            <input
              type="number"
              min={1}
              max={180}
              value={settings.default_snooze_minutes}
              onChange={(event) => updateSettings({ default_snooze_minutes: Number(event.target.value) })}
            />
            <span>{t("minutes")}</span>
          </div>
        </label>
        <label className="toggle-row">
          <span>
            <strong>{t("repeats")}</strong>
            <small>MedAlarm</small>
          </span>
          <input
            type="checkbox"
            checked={settings.remind_until_confirmed}
            onChange={(event) => updateSettings({ remind_until_confirmed: event.target.checked })}
          />
        </label>
      </div>
    </section>
  );
}
