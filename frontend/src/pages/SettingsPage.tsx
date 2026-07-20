import { Bug, Info, Star, Type } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchBackendVersion, FRONTEND_VERSION } from "../api/version";
import { useAppSettings } from "../contexts/AppSettingsContext";
import type { TextSize } from "../types";
import { useHapticsEnabled } from "../utils/haptics";
import { snoozeOptions, timezoneLabel, timezoneOptions } from "../utils/settingsOptions";

export function SettingsPage() {
  const { settings, updateSettings, t } = useAppSettings();
  const [hapticsEnabled, setHapticsEnabled] = useHapticsEnabled();
  const [backendVersion, setBackendVersion] = useState<string | null>();

  useEffect(() => {
    let active = true;
    void fetchBackendVersion()
      .then((version) => {
        if (active) setBackendVersion(version);
      })
      .catch(() => {
        if (active) setBackendVersion(null);
      });
    return () => {
      active = false;
    };
  }, []);

  const formatVersion = (version: string) => (version === "unknown" ? t("versionUnavailable") : `v${version}`);
  const versionStatus =
    backendVersion === undefined
      ? t("versionChecking")
      : backendVersion === null || FRONTEND_VERSION === "unknown" || backendVersion === "unknown"
        ? t("versionUnavailable")
        : backendVersion === FRONTEND_VERSION
          ? t("versionMatch")
          : t("versionMismatch");
  const versionStatusTone =
    backendVersion && backendVersion !== "unknown" && FRONTEND_VERSION !== "unknown"
      ? backendVersion === FRONTEND_VERSION
        ? "match"
        : "warning"
      : "neutral";

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
        <div className="text-size-setting">
          <div className="text-size-setting-heading">
            <Type size={20} aria-hidden="true" />
            <div className="text-size-setting-copy">
              <strong>{t("textSize")}</strong>
              <small>{t("textSizeHint")}</small>
            </div>
          </div>
          <div className="text-size-presets" role="group" aria-label={t("textSize")}>
            {(["small", "regular", "large"] as TextSize[]).map((size) => (
              <button
                key={size}
                type="button"
                className={settings.text_size === size ? "active" : ""}
                aria-pressed={settings.text_size === size}
                onClick={() => updateSettings({ text_size: size })}
              >
                <span className={`text-size-sample ${size}`} aria-hidden="true">Aa</span>
                <span className="text-size-preset-label">
                  {t(size === "small" ? "textSizeSmall" : size === "regular" ? "textSizeRegular" : "textSizeLarge")}
                </span>
              </button>
            ))}
          </div>
        </div>
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
        <div className="settings-divider" />
        <div className="settings-version-panel">
          <div className="settings-version-heading">
            <Info size={20} aria-hidden="true" />
            <span className="settings-section-title">{t("appVersion")}</span>
          </div>
          <div className="settings-version-row">
            <span>{t("frontendVersion")}</span>
            <strong>{formatVersion(FRONTEND_VERSION)}</strong>
          </div>
          <div className="settings-version-row">
            <span>{t("backendVersion")}</span>
            <strong>
              {backendVersion === undefined
                ? t("versionChecking")
                : backendVersion === null
                  ? t("versionUnavailable")
                  : formatVersion(backendVersion)}
            </strong>
          </div>
          <small className={`settings-version-status ${versionStatusTone}`} aria-live="polite">
            {versionStatus}
          </small>
        </div>
      </div>
    </section>
  );
}
