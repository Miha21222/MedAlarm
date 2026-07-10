import { useQueryClient } from "@tanstack/react-query";
import { Check, Clock3, Eraser, Plus, Trash2 } from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { MicButton } from "../components/MicButton";
import { useAppSettings } from "../contexts/AppSettingsContext";
import { useToast } from "../contexts/ToastContext";
import { updateMedicineInCache } from "../features/medicines/cache";
import { clearMedicineDraft, readMedicineDraft, writeMedicineDraft } from "../features/medicines/draftStorage";
import { createLocalMedicine, getLocalMedicine, updateLocalMedicine } from "../features/medicines/localMedicineRepository";
import { useSpeechInput } from "../hooks/useSpeechInput";
import {
  combineDosage,
  dosageAmountOptions,
  dosageUnitOptions,
  parseDosageText,
} from "../utils/dosage";
import { hapticImpact, hapticNotification } from "../utils/haptics";

export function MedicineFormPage() {
  const { medicineId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { settings, t } = useAppSettings();
  const { showToast } = useToast();
  const existing = medicineId ? getLocalMedicine(medicineId) : undefined;
  const draftContext = medicineId ?? "new";
  const savedDraft = useMemo(() => readMedicineDraft(draftContext), [draftContext]);
  const parsedDosage = parseDosageText(existing?.dosage_text ?? "");

  const [name, setName] = useState(savedDraft?.name ?? existing?.name ?? "");
  const [amount, setAmount] = useState(savedDraft?.amount ?? parsedDosage.amount);
  const [unit, setUnit] = useState(savedDraft?.unit ?? parsedDosage.unit);
  const [comment, setComment] = useState(savedDraft?.comment ?? existing?.comment ?? "");
  const [times, setTimes] = useState<string[]>(
    savedDraft?.times.length ? savedDraft.times : existing?.schedules.map((slot) => slot.time) ?? ["09:00"],
  );

  useEffect(() => {
    writeMedicineDraft({ context: draftContext, name, amount, unit, comment, times });
  }, [amount, comment, draftContext, name, times, unit]);

  const appendTranscript = useCallback((current: string, transcript: string) => {
    const separator = current.trim() ? " " : "";
    return `${current}${separator}${transcript}`.trimStart();
  }, []);

  const handleNameTranscript = useCallback(
    (transcript: string) => setName((current) => appendTranscript(current, transcript)),
    [appendTranscript],
  );
  const handleCommentTranscript = useCallback(
    (transcript: string) => setComment((current) => appendTranscript(current, transcript)),
    [appendTranscript],
  );
  const nameSpeech = useSpeechInput(settings.language, handleNameTranscript);
  const commentSpeech = useSpeechInput(settings.language, handleCommentTranscript);

  const clearForm = () => {
    setName(existing?.name ?? "");
    setAmount(parsedDosage.amount);
    setUnit(parsedDosage.unit);
    setComment(existing?.comment ?? "");
    setTimes(existing?.schedules.map((slot) => slot.time) ?? ["09:00"]);
    clearMedicineDraft();
    hapticImpact("light");
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const schedules = times.filter(Boolean).map((time) => ({ time, days_of_week: "*" }));
    const input = { name: name.trim(), dosage_text: combineDosage(amount, unit), comment: comment.trim() || null, schedules };
    const saved = existing ? await updateLocalMedicine(existing, input) : await createLocalMedicine(input);
    updateMedicineInCache(queryClient, saved);
    clearMedicineDraft();
    hapticNotification("success");
    showToast({ message: t("savedToast"), tone: "success" });
    navigate(`/medicines/${saved.client_medicine_id}`);
  };

  return (
    <section className="page-stack">
      <form className="medicine-form" onSubmit={(event) => void submit(event)}>
        <label>
          {t("name")}
          <span className="field-with-mic">
            <input required maxLength={128} value={name} onChange={(event) => setName(event.target.value)} />
            <MicButton
              supported={nameSpeech.supported}
              recording={nameSpeech.recording}
              onClick={nameSpeech.toggle}
              label={t("name")}
            />
          </span>
        </label>
        <label>
          {t("dosage")}
          <span className="dosage-row">
            <select required value={amount} onChange={(event) => setAmount(event.target.value)}>
              {dosageAmountOptions(amount).map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
            <select required value={unit} onChange={(event) => setUnit(event.target.value)}>
              {dosageUnitOptions(unit).map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </span>
        </label>
        <label>
          {t("comment")}
          <span className="field-with-mic">
            <textarea rows={3} value={comment} onChange={(event) => setComment(event.target.value)} />
            <MicButton
              supported={commentSpeech.supported}
              recording={commentSpeech.recording}
              onClick={commentSpeech.toggle}
              label={t("comment")}
            />
          </span>
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
        <button className="danger-btn full" type="button" onClick={clearForm}>
          <Eraser size={18} />
          {t("clearForm")}
        </button>
      </form>
    </section>
  );
}
