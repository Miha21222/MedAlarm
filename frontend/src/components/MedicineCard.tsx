import { ChevronRight, Pill } from "lucide-react";
import { Link } from "react-router-dom";
import type { TranslationKey } from "../i18n";
import type { Medicine } from "../types";

// Modeled on PocketMind's TaskCard.tsx structure (clickable card, title row,
// meta lines, sync-state badge) but authored for MedAlarm's actual fields —
// there's no task-shaped equivalent to port field-for-field.
export function MedicineCard({
  medicine,
  t,
}: {
  medicine: Medicine;
  t: (key: TranslationKey) => string;
}) {
  return (
    <Link to={`/medicines/${medicine.client_medicine_id}`} className="medicine-card">
      <div className="medicine-icon">
        <Pill />
      </div>
      <div>
        <strong>{medicine.name}</strong>
        <p>{medicine.dosage_text}</p>
        <div className="time-row">
          {medicine.schedules.map((slot) => (
            <span key={`${slot.time}-${slot.days_of_week}`}>{slot.time}</span>
          ))}
        </div>
        {medicine.syncState === "pending" ? <small>{t("syncPending")}</small> : null}
        {medicine.syncState === "error" ? <small className="error">{t("syncError")}</small> : null}
      </div>
      <ChevronRight />
    </Link>
  );
}
