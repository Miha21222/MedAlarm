import { useQueryClient } from "@tanstack/react-query";
import { Check, Clock3, Plus, Trash2 } from "lucide-react";
import { FormEvent, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useAppSettings } from "../contexts/AppSettingsContext";
import { useToast } from "../contexts/ToastContext";
import { updateMedicineInCache } from "../features/medicines/cache";
import { createLocalMedicine, getLocalMedicine, updateLocalMedicine } from "../features/medicines/localMedicineRepository";
import { hapticNotification } from "../utils/haptics";

export function MedicineFormPage() {
  const { medicineId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { t } = useAppSettings();
  const { showToast } = useToast();
  const existing = medicineId ? getLocalMedicine(medicineId) : undefined;

  const [name, setName] = useState(existing?.name ?? "");
  const [dosage, setDosage] = useState(existing?.dosage_text ?? "");
  const [comment, setComment] = useState(existing?.comment ?? "");
  const [times, setTimes] = useState<string[]>(existing?.schedules.map((slot) => slot.time) ?? ["09:00"]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const schedules = times.filter(Boolean).map((time) => ({ time, days_of_week: "*" }));
    const input = { name: name.trim(), dosage_text: dosage.trim(), comment: comment.trim() || null, schedules };
    const saved = existing ? await updateLocalMedicine(existing, input) : await createLocalMedicine(input);
    updateMedicineInCache(queryClient, saved);
    hapticNotification("success");
    showToast({ message: t("savedToast"), tone: "success" });
    navigate(`/medicines/${saved.client_medicine_id}`);
  };

  return (
    <section className="page-stack">
      <form className="medicine-form" onSubmit={(event) => void submit(event)}>
        <label>
          {t("name")}
          <input required maxLength={128} value={name} onChange={(event) => setName(event.target.value)} />
        </label>
        <label>
          {t("dosage")}
          <input required maxLength={128} value={dosage} onChange={(event) => setDosage(event.target.value)} />
        </label>
        <label>
          {t("comment")}
          <textarea rows={3} value={comment} onChange={(event) => setComment(event.target.value)} />
        </label>
        <div className="schedule-editor">
          <div className="form-heading">
            <span>{t("time")}</span>
            <button type="button" onClick={() => setTimes([...times, "12:00"])}>
              <Plus size={17} />
            </button>
          </div>
          {times.map((time, index) => (
            <div className="time-input" key={index}>
              <Clock3 size={18} />
              <input
                type="time"
                required
                value={time}
                onChange={(event) =>
                  setTimes(times.map((item, itemIndex) => (itemIndex === index ? event.target.value : item)))
                }
              />
              {times.length > 1 ? (
                <button type="button" onClick={() => setTimes(times.filter((_, itemIndex) => itemIndex !== index))}>
                  <Trash2 size={17} />
                </button>
              ) : null}
            </div>
          ))}
          <p className="field-note">{t("daily")}</p>
        </div>
        <button className="primary-btn full" type="submit">
          <Check size={19} />
          {t("save")}
        </button>
      </form>
    </section>
  );
}
