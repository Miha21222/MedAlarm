import { useQueryClient } from "@tanstack/react-query";
import { Pill, Trash2 } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { EmptyState } from "../components/EmptyState";
import { useAppSettings } from "../contexts/AppSettingsContext";
import { useToast } from "../contexts/ToastContext";
import { removeMedicineFromCache } from "../features/medicines/cache";
import { deleteLocalMedicine, getLocalMedicine } from "../features/medicines/localMedicineRepository";
import { hapticNotification } from "../utils/haptics";

export function MedicineDetailPage() {
  const { medicineId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { t } = useAppSettings();
  const { showToast } = useToast();
  const medicine = medicineId ? getLocalMedicine(medicineId) : undefined;

  if (!medicine) return <EmptyState icon={<Pill />} text={t("noMedicines")} />;

  const remove = async () => {
    await deleteLocalMedicine(medicine);
    removeMedicineFromCache(queryClient, medicine.client_medicine_id);
    hapticNotification("warning");
    showToast({ message: t("deletedToast"), tone: "success" });
    navigate("/medicines");
  };

  return (
    <section className="page-stack">
      <article className="detail-hero">
        <div className="medicine-icon large">
          <Pill size={32} />
        </div>
        <h2>{medicine.name}</h2>
        <p>{medicine.dosage_text}</p>
        {medicine.comment ? <blockquote>{medicine.comment}</blockquote> : null}
        <div className="time-row center">
          {medicine.schedules.map((slot) => (
            <span key={slot.time}>{slot.time}</span>
          ))}
        </div>
      </article>
      <Link className="primary-btn full" to={`/medicines/${medicine.client_medicine_id}/edit`}>
        {t("editMedicine")}
      </Link>
      <button className="danger-btn full" onClick={() => void remove()}>
        <Trash2 size={18} />
        {t("delete")}
      </button>
    </section>
  );
}
