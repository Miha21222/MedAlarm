import { CalendarDays, Clock3, Pill } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchAdherence, fetchToday } from "../api/dashboard";
import { EmptyState } from "../components/EmptyState";
import { SectionHeader } from "../components/SectionHeader";
import { useAppSettings } from "../contexts/AppSettingsContext";
import { useMedicinesAllQuery } from "../features/medicines/cache";
import { sortMedicines } from "../features/medicines/localMedicines";
import { usePersistentEnumState } from "../hooks/usePersistentEnumState";
import type { TodayItem } from "../types";

const PERIODS = ["7d", "30d"] as const;

export function DashboardPage() {
  const { t } = useAppSettings();
  const { data: medicines = [] } = useMedicinesAllQuery();
  const period = usePersistentEnumState<(typeof PERIODS)[number]>("medalarm.dashboard.period", "7d", PERIODS);
  const [today, setToday] = useState<TodayItem[]>([]);
  const [adherence, setAdherence] = useState({ adherence_percent: 0, counts: {} as Record<string, number> });

  useEffect(() => {
    void Promise.all([fetchToday(medicines), fetchAdherence(period.value)]).then(([items, stats]) => {
      setToday(items);
      setAdherence(stats);
    });
  }, [medicines, period.value]);

  const sorted = sortMedicines(today);

  return (
    <section className="page-stack">
      <div className="hero-panel">
        <div>
          <span>{t("adherence")}</span>
          <strong>{adherence.adherence_percent}%</strong>
        </div>
        <div className="segmented">
          <button className={period.value === "7d" ? "selected" : ""} onClick={() => period.setValue("7d")}>
            {t("sevenDays")}
          </button>
          <button className={period.value === "30d" ? "selected" : ""} onClick={() => period.setValue("30d")}>
            {t("thirtyDays")}
          </button>
        </div>
        <div className="progress-track">
          <span style={{ width: `${adherence.adherence_percent}%` }} />
        </div>
      </div>

      <SectionHeader icon={<Clock3 />} title={t("todayPlan")} count={sorted.length} />
      {sorted.length ? (
        <div className="dose-timeline">
          {sorted.map((medicine) => (
            <Link key={medicine.client_medicine_id} to={`/medicines/${medicine.client_medicine_id}`} className="dose-card">
              <time>{medicine.schedules[0]?.time || "--:--"}</time>
              <div className="dose-symbol">
                <Pill size={20} />
              </div>
              <div className="dose-copy">
                <strong>{medicine.name}</strong>
                <span>{medicine.dosage_text}</span>
              </div>
              <span className={`status-chip ${medicine.status}`}>{t(medicine.status)}</span>
            </Link>
          ))}
        </div>
      ) : (
        <EmptyState icon={<CalendarDays />} text={t("noDoses")} />
      )}
    </section>
  );
}
