import { History as HistoryIcon } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { fetchHistory } from "../api/history";
import { EmptyState } from "../components/EmptyState";
import { SectionHeader } from "../components/SectionHeader";
import { useAppSettings } from "../contexts/AppSettingsContext";
import { useDemoModeEnabled } from "../features/demo/demoMode";
import {
  filterHistory,
  groupHistory,
  summarizeHistory,
  type HistoryGroupBy,
  type HistoryStatusFilter,
} from "../features/history/historyAnalysis";
import { usePersistentEnumState } from "../hooks/usePersistentEnumState";
import type { TranslationKey } from "../i18n";
import type { HistoryItem } from "../types";
import { formatInTimezone } from "../utils/dateTime";

const PERIODS = ["today", "week", "month"] as const;
type Period = (typeof PERIODS)[number];
const PERIOD_LABELS: Record<Period, TranslationKey> = {
  today: "periodToday",
  week: "periodWeek",
  month: "periodMonth",
};

// "By day"/"By medicine" grouping is hidden for the "today" period — with a
// single day in view, day-grouping is a no-op and medicine-grouping adds a
// layer of navigation over what's already a short list.
const GROUP_OPTIONS: HistoryGroupBy[] = ["none", "day", "medicine"];
const GROUP_LABELS: Record<HistoryGroupBy, TranslationKey> = {
  none: "groupByNone",
  day: "groupByDay",
  medicine: "groupByMedicine",
};

const STATUS_FILTERS: HistoryStatusFilter[] = ["all", "taken", "skipped", "missed", "snoozed"];
const STATUS_LABELS: Record<HistoryStatusFilter, TranslationKey> = {
  all: "allStatuses",
  taken: "taken",
  skipped: "skipped",
  missed: "missed",
  snoozed: "snoozed",
};

export function HistoryPage() {
  const { t, settings } = useAppSettings();
  const [items, setItems] = useState<HistoryItem[]>([]);
  const period = usePersistentEnumState<Period>("medalarm.history.period", "month", PERIODS);
  const groupBy = usePersistentEnumState<HistoryGroupBy>("medalarm.history.groupBy", "none", GROUP_OPTIONS);
  const [status, setStatus] = useState<HistoryStatusFilter>("all");
  const [demoEnabled] = useDemoModeEnabled();

  useEffect(() => {
    void fetchHistory(period.value).then(setItems);
  }, [period.value, demoEnabled]);

  const effectiveGroupBy = period.value === "today" ? "none" : groupBy.value;
  const filtered = useMemo(() => filterHistory(items, { status }), [items, status]);
  const groups = useMemo(
    () => groupHistory(filtered, effectiveGroupBy, settings.timezone, settings.language),
    [filtered, effectiveGroupBy, settings.timezone, settings.language],
  );
  const summary = useMemo(() => summarizeHistory(filtered), [filtered]);

  return (
    <section className="page-stack">
      {summary.total > 0 ? (
        <div className="history-summary">
          <div className="history-summary-percent">
            <strong>{summary.takenPercent}%</strong>
            <span>{t("taken")}</span>
          </div>
          <div className="history-summary-chips">
            <span className="status-chip taken">
              {summary.taken} {t("taken")}
            </span>
            <span className="status-chip skipped">
              {summary.skipped} {t("skipped")}
            </span>
            <span className="status-chip snoozed">
              {summary.snoozed} {t("snoozed")}
            </span>
            {summary.missed > 0 ? (
              <span className="status-chip missed">
                {summary.missed} {t("missed")}
              </span>
            ) : null}
          </div>
        </div>
      ) : null}

      <SectionHeader icon={<HistoryIcon />} title={t("history")} />

      <div className="history-filters">
        <div className="history-filter-row">
          <select value={period.value} onChange={(event) => period.setValue(event.target.value as Period)}>
            {PERIODS.map((option) => (
              <option key={option} value={option}>
                {t(PERIOD_LABELS[option])}
              </option>
            ))}
          </select>
          <select value={status} onChange={(event) => setStatus(event.target.value as HistoryStatusFilter)}>
            {STATUS_FILTERS.map((option) => (
              <option key={option} value={option}>
                {t(STATUS_LABELS[option])}
              </option>
            ))}
          </select>
        </div>
        {period.value !== "today" ? (
          <select value={groupBy.value} onChange={(event) => groupBy.setValue(event.target.value as HistoryGroupBy)}>
            {GROUP_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {t(GROUP_LABELS[option])}
              </option>
            ))}
          </select>
        ) : null}
      </div>

      {groups.length ? (
        <div className="history-groups">
          {groups.map((group) => (
            <div key={group.key}>
              {effectiveGroupBy !== "none" ? <h3 className="history-group-label">{group.label}</h3> : null}
              <div className="history-group-items">
                {group.items.map((item, index) => (
                  <article className="history-row" key={`${item.event_id}-${index}`}>
                    <span className={`history-dot ${item.status}`} />
                    <div>
                      <strong>{item.medicine}</strong>
                      <time>{formatInTimezone(item.scheduled_at, settings.timezone, settings.language, true)}</time>
                    </div>
                    <span className={`status-chip ${item.status}`}>{t(item.status)}</span>
                  </article>
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState icon={<HistoryIcon />} text={t("noHistory")} />
      )}
    </section>
  );
}
