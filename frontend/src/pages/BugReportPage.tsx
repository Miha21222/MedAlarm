import { useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { ImagePlus, X } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { submitFeedback } from "../api/feedback";
import { useAppSettings } from "../contexts/AppSettingsContext";
import { useToast } from "../contexts/ToastContext";
import { hapticNotification } from "../utils/haptics";

const MAX_SCREENSHOT_BYTES = 8 * 1024 * 1024;
const ALLOWED_IMAGE_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);

export function BugReportPage() {
  const { t } = useAppSettings();
  const { showToast } = useToast();
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [description, setDescription] = useState("");
  const [showDescriptionError, setShowDescriptionError] = useState(false);
  const [screenshot, setScreenshot] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [screenshotError, setScreenshotError] = useState<string | null>(null);
  const mutation = useMutation({
    mutationFn: () =>
      submitFeedback({
        kind: "bug",
        message: description.trim(),
        screenshot,
      }),
  });

  useEffect(() => () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  }, [previewUrl]);

  const clearScreenshot = () => {
    setScreenshot(null);
    setPreviewUrl(null);
    setScreenshotError(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const selectScreenshot = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    if (!ALLOWED_IMAGE_TYPES.has(file.type)) {
      setScreenshotError(t("screenshotTypeError"));
      return;
    }
    if (file.size > MAX_SCREENSHOT_BYTES) {
      setScreenshotError(t("screenshotSizeError"));
      return;
    }
    setScreenshotError(null);
    setScreenshot(file);
    setPreviewUrl(URL.createObjectURL(file));
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!description.trim()) {
      setShowDescriptionError(true);
      hapticNotification("error");
      return;
    }
    try {
      await mutation.mutateAsync();
      hapticNotification("success");
      showToast({ tone: "success", message: t("feedbackSent") });
      navigate("/settings", { replace: true });
    } catch {
      hapticNotification("error");
      showToast({ tone: "error", message: t("feedbackSendError") });
    }
  };

  return (
    <section className="page-stack">
      <form className="settings-card feedback-form" onSubmit={submit}>
        <div className="feedback-intro">
          <h2>{t("reportBug")}</h2>
          <p>{t("reportBugDescription")}</p>
        </div>
        <label>
          {t("bugDescriptionLabel")}
          <textarea
            rows={6}
            maxLength={5000}
            placeholder={t("bugDescriptionPlaceholder")}
            value={description}
            onChange={(event) => {
              setDescription(event.target.value);
              if (event.target.value.trim()) setShowDescriptionError(false);
            }}
          />
          {showDescriptionError ? <small className="field-error">{t("bugDescriptionRequired")}</small> : null}
        </label>
        <div className="feedback-screenshot-field">
          <span className="settings-section-title">{t("screenshotLabel")}</span>
          <input
            ref={fileInputRef}
            className="feedback-file-input"
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={selectScreenshot}
          />
          {previewUrl ? (
            <div className="feedback-screenshot-preview">
              <img src={previewUrl} alt={t("screenshotPreview")} />
              <button type="button" onClick={clearScreenshot} aria-label={t("removeScreenshot")}>
                <X size={18} />
              </button>
            </div>
          ) : (
            <button type="button" className="attachment-btn" onClick={() => fileInputRef.current?.click()}>
              <ImagePlus size={19} />
              {t("attachScreenshot")}
            </button>
          )}
          <small className="field-note">{t("screenshotHint")}</small>
          {screenshotError ? <small className="field-error">{screenshotError}</small> : null}
        </div>
        <button type="submit" className="primary-btn full" disabled={mutation.isPending}>
          {mutation.isPending ? t("sending") : t("send")}
        </button>
      </form>
    </section>
  );
}
