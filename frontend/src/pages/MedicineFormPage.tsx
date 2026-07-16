import { useQueryClient } from "@tanstack/react-query";
import { BookOpen, Check, Clock3, Eraser, Info, PenLine, Plus, Search, Trash2 } from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { searchMedicineCatalog } from "../api/catalog";
import { MedicineCatalogDetails } from "../components/MedicineCatalogDetails";
import { MicButton } from "../components/MicButton";
import { useAppSettings } from "../contexts/AppSettingsContext";
import { useToast } from "../contexts/ToastContext";
import { updateMedicineInCache } from "../features/medicines/cache";
import { clearMedicineDraft, readMedicineDraft, writeMedicineDraft } from "../features/medicines/draftStorage";
import { createLocalMedicine, getLocalMedicine, updateLocalMedicine } from "../features/medicines/localMedicineRepository";
import { useSpeechInput } from "../hooks/useSpeechInput";
import type { MedicineCatalogReference } from "../types";
import {
  combineDosage,
  dosageAmountOptions,
  dosageUnitOptions,
  parseDosageText,
} from "../utils/dosage";
import { hapticImpact, hapticNotification } from "../utils/haptics";

type EntryMode = "catalog" | "manual";

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

  const initialCatalog = savedDraft?.catalog ?? existing?.catalog ?? null;
  const [entryMode, setEntryMode] = useState<EntryMode>(initialCatalog || !medicineId ? "catalog" : "manual");
  const [catalog, setCatalog] = useState<MedicineCatalogReference | null>(initialCatalog);
  const [catalogQuery, setCatalogQuery] = useState("");
  const [catalogResults, setCatalogResults] = useState<MedicineCatalogReference[]>([]);
  const [catalogLoading, setCatalogLoading] = useState(false);
  const [catalogError, setCatalogError] = useState(false);

  const [name, setName] = useState(savedDraft?.name ?? existing?.name ?? "");
  const [amount, setAmount] = useState(savedDraft?.amount ?? parsedDosage.amount);
  const [unit, setUnit] = useState(savedDraft?.unit ?? parsedDosage.unit);
  const [comment, setComment] = useState(savedDraft?.comment ?? existing?.comment ?? "");
  const [times, setTimes] = useState<string[]>(
    savedDraft?.times.length ? savedDraft.times : existing?.schedules.map((slot) => slot.time) ?? ["09:00"],
  );

  useEffect(() => {
    writeMedicineDraft({ context: draftContext, name, amount, unit, comment, times, catalog });
  }, [amount, catalog, comment, draftContext, name, times, unit]);

  useEffect(() => {
    const query = catalogQuery.trim();
    if (entryMode !== "catalog" || catalog || query.length < 2) {
      setCatalogResults([]);
      setCatalogLoading(false);
      setCatalogError(false);
      return;
    }
    let cancelled = false;
    setCatalogLoading(true);
    setCatalogError(false);
    const timer = window.setTimeout(() => {
      void searchMedicineCatalog(query)
        .then((response) => {
          if (!cancelled) setCatalogResults(response.items);
        })
        .catch(() => {
          if (!cancelled) {
            setCatalogResults([]);
            setCatalogError(true);
          }
        })
        .finally(() => {
          if (!cancelled) setCatalogLoading(false);
        });
    }, 400);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [catalog, catalogQuery, entryMode]);

  const appendTranscript = useCallback((current: string, transcript: string) => {
    const separator = current.trim() ? " " : "";
    return `${current}${separator}${transcript}`.trimStart();
  }, []);
  const nameSpeech = useSpeechInput(
    settings.language,
    useCallback((transcript: string) => setName((current) => appendTranscript(current, transcript)), [appendTranscript]),
  );
  const commentSpeech = useSpeechInput(
    settings.language,
    useCallback((transcript: string) => setComment((current) => appendTranscript(current, transcript)), [appendTranscript]),
  );

  const selectCatalogMedicine = (item: MedicineCatalogReference) => {
    setCatalog(item);
    // Reminder names stay within the existing bot/API limit; the full official
    // name remains available in the immutable catalogue snapshot below.
    setName(item.trade_name.slice(0, 128));
    setCatalogQuery("");
    setCatalogResults([]);
    hapticImpact("light");
  };

  const selectMode = (mode: EntryMode) => {
    setEntryMode(mode);
    if (mode === "manual") {
      setCatalog(null);
      if (!existing) setName("");
    }
    hapticImpact("light");
  };

  const clearForm = () => {
    const originalCatalog = existing?.catalog ?? null;
    setCatalog(originalCatalog);
    setEntryMode(originalCatalog ? "catalog" : medicineId ? "manual" : "catalog");
    setCatalogQuery("");
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
    const input = {
      name: name.trim(),
      dosage_text: combineDosage(amount, unit),
      comment: comment.trim() || null,
      catalog,
      schedules,
    };
    const saved = existing ? await updateLocalMedicine(existing, input) : await createLocalMedicine(input);
    updateMedicineInCache(queryClient, saved);
    clearMedicineDraft();
    hapticNotification("success");
    showToast({ message: t("savedToast"), tone: "success" });
    navigate(`/medicines/${saved.client_medicine_id}`);
  };

  const showForm = entryMode === "manual" || catalog !== null;

  return (
    <section className="page-stack">
      {!medicineId ? (
        <div className="entry-method-card">
          <strong>{t("entryMethod")}</strong>
          <div className="entry-method-switch" role="group" aria-label={t("entryMethod")}>
            <button className={entryMode === "catalog" ? "active" : ""} type="button" onClick={() => selectMode("catalog")}>
              <BookOpen size={18} />{t("fromCatalog")}
            </button>
            <button className={entryMode === "manual" ? "active" : ""} type="button" onClick={() => selectMode("manual")}>
              <PenLine size={18} />{t("manually")}
            </button>
          </div>
        </div>
      ) : null}

      {entryMode === "catalog" && !catalog ? (
        <section className="catalog-picker">
          <div className="catalog-scope-note">
            <Info size={19} aria-hidden="true" />
            <div>
              <strong>{t("catalogUkraineTitle")}</strong>
              <p>{t("catalogUkraineHint")}</p>
            </div>
          </div>
          <label>
            {t("catalogSearch")}
            <span className="catalog-search-input">
              <Search size={19} />
              <input
                autoFocus
                value={catalogQuery}
                placeholder={t("catalogSearchHint")}
                onChange={(event) => setCatalogQuery(event.target.value)}
              />
            </span>
          </label>
          {catalogLoading ? <p className="catalog-message">{t("catalogLoading")}</p> : null}
          {catalogError ? <p className="catalog-message error">{t("catalogUnavailable")}</p> : null}
          {!catalogLoading && !catalogError && catalogQuery.trim().length > 0 && catalogQuery.trim().length < 2 ? (
            <p className="catalog-message">{t("catalogMinChars")}</p>
          ) : null}
          {!catalogLoading && !catalogError && catalogQuery.trim().length >= 2 && catalogResults.length === 0 ? (
            <p className="catalog-message">{t("catalogNoResults")}</p>
          ) : null}
          <div className="catalog-results">
            {catalogResults.map((item) => (
              <button key={item.source_id} type="button" onClick={() => selectCatalogMedicine(item)}>
                <strong>{item.trade_name}</strong>
                {item.inn ? <span>{item.inn}</span> : null}
                {item.form ? <small>{item.form}</small> : null}
                <em>{[item.manufacturer, item.registration_number].filter(Boolean).join(" · ")}</em>
              </button>
            ))}
          </div>
        </section>
      ) : null}

      {catalog ? <MedicineCatalogDetails catalog={catalog} condensed /> : null}

      {showForm ? (
        <form className="medicine-form" onSubmit={(event) => void submit(event)}>
          <label>
            {t("name")}
            <span className="field-with-mic">
              <input
                required
                readOnly={Boolean(catalog)}
                maxLength={128}
                value={name}
                onChange={(event) => setName(event.target.value)}
              />
              {!catalog ? (
                <MicButton supported={nameSpeech.supported} recording={nameSpeech.recording} onClick={nameSpeech.toggle} label={t("name")} />
              ) : null}
            </span>
          </label>
          <label>
            {t("dosage")}
            <span className="dosage-row">
              <select required value={amount} onChange={(event) => setAmount(event.target.value)}>
                {dosageAmountOptions(amount).map((option) => <option key={option} value={option}>{option}</option>)}
              </select>
              <select required value={unit} onChange={(event) => setUnit(event.target.value)}>
                {dosageUnitOptions(unit).map((option) => <option key={option} value={option}>{option}</option>)}
              </select>
            </span>
            <span className="field-note">{t("personalDoseHint")}</span>
          </label>
          <label>
            {t("comment")}
            <span className="field-with-mic">
              <textarea rows={3} value={comment} onChange={(event) => setComment(event.target.value)} />
              <MicButton supported={commentSpeech.supported} recording={commentSpeech.recording} onClick={commentSpeech.toggle} label={t("comment")} />
            </span>
          </label>
          <div className="schedule-editor">
            <div className="form-heading">
              <span>{t("time")}</span>
              <button type="button" onClick={() => setTimes([...times, "12:00"])}><Plus size={17} /></button>
            </div>
            {times.map((time, index) => (
              <div className="time-input" key={index}>
                <Clock3 size={18} />
                <input type="time" required value={time} onChange={(event) => setTimes(times.map((item, itemIndex) => itemIndex === index ? event.target.value : item))} />
                {times.length > 1 ? <button type="button" onClick={() => setTimes(times.filter((_, itemIndex) => itemIndex !== index))}><Trash2 size={17} /></button> : null}
              </div>
            ))}
            <p className="field-note">{t("daily")}</p>
          </div>
          <button className="primary-btn full" type="submit"><Check size={19} />{t("save")}</button>
          <button className="danger-btn full" type="button" onClick={clearForm}><Eraser size={18} />{t("clearForm")}</button>
        </form>
      ) : null}
    </section>
  );
}
