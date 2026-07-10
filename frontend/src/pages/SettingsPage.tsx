import { useAppSettings } from "../contexts/AppSettingsContext";
import { useHapticsEnabled } from "../utils/haptics";
import { snoozeOptions, timezoneLabel, timezoneOptions } from "../utils/settingsOptions";

export function SettingsPage() {
  const { settings, updateSettings, t } = useAppSettings();
  const [hapticsEnabled, setHapticsEnabled] = useHapticsEnabled();

  return (
    <section className="page-stack">
      <div className="settings-card">
        <label>
          {t("timezone")}
          <select value={settings.timezone} onChange={(event) => updateSettings({ timezone: event.target.value })}>
            {timezoneOptions(settings.timezone).map((tz) => (
              <option key={tz} value={tz}>
                {timezoneLabel(tz)}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t("snooze")}
          <select
            value={settings.default_snooze_minutes}
            onChange={(event) => updateSettings({ default_snooze_minutes: Number(event.target.value) })}
          >
            {snoozeOptions(settings.default_snooze_minutes).map((minutes) => (
              <option key={minutes} value={minutes}>
                {minutes} {t("minutes")}
              </option>
            ))}
          </select>
        </label>
        <label className="toggle-row">
          <span>
            <strong>{t("repeats")}</strong>
            <small>{t("repeatsHint")}</small>
          </span>
          <span className="toggle-switch">
            <input
              type="checkbox"
              checked={settings.remind_until_confirmed}
              onChange={(event) => updateSettings({ remind_until_confirmed: event.target.checked })}
            />
            <span className="toggle-slider" />
          </span>
        </label>
        <label className="toggle-row">
          <span>
            <strong>{t("haptics")}</strong>
            <small>{t("hapticsHint")}</small>
          </span>
          <span className="toggle-switch">
            <input
              type="checkbox"
              checked={hapticsEnabled}
              onChange={(event) => setHapticsEnabled(event.target.checked)}
            />
            <span className="toggle-slider" />
          </span>
        </label>
        <div className="settings-divider" />
        <div className="settings-support-links">
          <span className="settings-section-title">{t("feedbackSupport")}</span>
          <Link to="/settings/feedback" className="settings-link">
            <Star size={20} aria-hidden="true" />
            <span>
              <strong>{t("rateExperience")}</strong>
              <small>{t("rateExperienceHint")}</small>
            </span>
          </Link>
          <Link to="/settings/bug-report" className="settings-link">
            <Bug size={20} aria-hidden="true" />
            <span>
              <strong>{t("reportBug")}</strong>
              <small>{t("reportBugHint")}</small>
            </span>
          </Link>
        </div>
      </div>
    </section>
  );
}
import { Bug, Star } from "lucide-react";
import { Link } from "react-router-dom";
