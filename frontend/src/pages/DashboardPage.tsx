import { CalendarDays, Check, Clock3, Pill, X } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchToday } from "../api/dashboard";
import { resolveReminderAction } from "../api/reminderActions";
import { EmptyState } from "../components/EmptyState";
import { SectionHeader } from "../components/SectionHeader";
import { useAppSettings } from "../contexts/AppSettingsContext";
import { useToast } from "../contexts/ToastContext";
import { useDemoModeEnabled } from "../features/demo/demoMode";
import { useMedicinesAllQuery } from "../features/medicines/cache";
import { sortMedicines } from "../features/medicines/localMedicines";
import type { DoseStatus, TodayItem } from "../types";
import { calculateDailyCompletion } from "../utils/dailyCompletion";
import { hapticNotification } from "../utils/haptics";

export function DashboardPage() {
  const { t, settings } = useAppSettings();
  const { showToast } = useToast();
  const { data: medicines = [] } = useMedicinesAllQuery();
  const [today, setToday] = useState<TodayItem[]>([]);
  const [demoEnabled] = useDemoModeEnabled();

  useEffect(() => {
    void fetchToday(medicines, settings.timezone).then(setToday);
  }, [medicines, settings.timezone, demoEnabled]);

  const sorted = sortMedicines(today);
  const completion = calculateDailyCompletion(sorted);
  const applyAction = async (medicine: TodayItem, action: "taken" | "skipped") => {
    const result = await resolveReminderAction({
      eventId: medicine.event_id,
      medicine,
      action,
      timezone: settings.timezone,
    });
    setToday((current) =>
      current.map((item) =>
        item.dose_key === medicine.dose_key ? { ...item, status: result.status as DoseStatus } : item,
      ),
    );
    hapticNotification(action === "taken" ? "success" : "warning");
    showToast({ message: t(action === "taken" ? "takenToast" : "skippedToast"), tone: "success" });
  };

  return (
    <section className="page-stack">
      <div className="hero-panel">
        <div>
          <span>{t("adherence")}</span>
          <strong>{completion.percent}%</strong>
        </div>
        <div className="completion-summary">
          {completion.taken} / {completion.total} {t("takenToday")}
        </div>
        <div className="progress-track">
          <span style={{ width: `${completion.percent}%` }} />
        </div>
      </div>

      <SectionHeader icon={<Clock3 />} title={t("todayPlan")} />
      {sorted.length ? (
        <div className="dose-timeline">
          {sorted.map((medicine) => (
            <article key={medicine.dose_key} className="dose-card">
              <Link to={`/medicines/${medicine.client_medicine_id}`} className="dose-link">
                <div className="dose-header">
                  <time>{medicine.schedules[0]?.time || "--:--"}</time>
                  <span className={`status-chip ${medicine.status}`}>{t(medicine.status)}</span>
                </div>
                <div className="dose-body">
                  <div className="dose-symbol">
                    <Pill size={20} />
                  </div>
                  <div className="dose-copy">
                    <strong>{medicine.name}</strong>
                    <span>{medicine.dosage_text}</span>
                  </div>
                </div>
              </Link>
              {medicine.status === "pending" && medicine.actionable ? (
                <div className="dose-actions" aria-label={t("doseActions")}>
                  <button type="button" onClick={() => void applyAction(medicine, "taken")}>
                    <Check size={15} />
                    {t("markTaken")}
                  </button>
                  <button type="button" onClick={() => void applyAction(medicine, "skipped")}>
                    <X size={15} />
                    {t("markSkipped")}
                  </button>
                </div>
              ) : null}
            </article>
          ))}
        </div>
      ) : (
        <EmptyState icon={<CalendarDays />} text={t("noDoses")} />
      )}
    </section>
  );
}
