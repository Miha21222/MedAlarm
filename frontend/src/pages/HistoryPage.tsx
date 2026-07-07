import { History as HistoryIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { fetchHistory } from "../api/history";
import { EmptyState } from "../components/EmptyState";
import { SectionHeader } from "../components/SectionHeader";
import { useAppSettings } from "../contexts/AppSettingsContext";
import type { HistoryItem } from "../types";
import { formatInTimezone } from "../utils/dateTime";

export function HistoryPage() {
  const { t, settings } = useAppSettings();
  const [items, setItems] = useState<HistoryItem[]>([]);

  useEffect(() => {
    void fetchHistory().then(setItems);
  }, []);

  return (
    <section className="page-stack">
      <SectionHeader icon={<HistoryIcon />} title={t("history")} count={items.length} />
      {items.length ? (
        items.map((item, index) => (
          <article className="history-row" key={`${item.event_id}-${index}`}>
            <span className={`history-dot ${item.status}`} />
            <div>
              <strong>{item.medicine}</strong>
              <time>{formatInTimezone(item.scheduled_at, settings.timezone, settings.language, true)}</time>
            </div>
            <span className={`status-chip ${item.status}`}>{t(item.status)}</span>
          </article>
        ))
      ) : (
        <EmptyState icon={<HistoryIcon />} text={t("noHistory")} />
      )}
    </section>
  );
}
