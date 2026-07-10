import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Star } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { submitFeedback } from "../api/feedback";
import { useAppSettings } from "../contexts/AppSettingsContext";
import { useToast } from "../contexts/ToastContext";
import { hapticNotification, hapticSelection } from "../utils/haptics";

const RATINGS = [1, 2, 3, 4, 5] as const;

export function FeedbackRatingPage() {
  const { t } = useAppSettings();
  const { showToast } = useToast();
  const navigate = useNavigate();
  const [rating, setRating] = useState<number | null>(null);
  const [comment, setComment] = useState("");
  const [showRatingError, setShowRatingError] = useState(false);
  const mutation = useMutation({
    mutationFn: () =>
      submitFeedback({
        kind: "rating",
        rating,
        message: comment.trim() || null,
      }),
  });

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (rating === null) {
      setShowRatingError(true);
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
          <h2>{t("rateExperience")}</h2>
          <p>{t("rateExperienceDescription")}</p>
        </div>
        <fieldset className="feedback-rating-field">
          <legend>{t("feedbackRatingLabel")}</legend>
          <div className="feedback-star-row" role="radiogroup" aria-label={t("feedbackRatingLabel")}>
            {RATINGS.map((value) => (
              <button
                key={value}
                type="button"
                role="radio"
                aria-checked={rating === value}
                aria-label={`${value} / 5`}
                className={rating !== null && value <= rating ? "selected" : ""}
                onClick={() => {
                  hapticSelection();
                  setRating(value);
                  setShowRatingError(false);
                }}
              >
                <Star size={28} fill="currentColor" />
              </button>
            ))}
          </div>
          {showRatingError ? <small className="field-error">{t("ratingRequired")}</small> : null}
        </fieldset>
        <label>
          {t("feedbackCommentLabel")}
          <textarea
            rows={4}
            maxLength={5000}
            placeholder={t("feedbackCommentPlaceholder")}
            value={comment}
            onChange={(event) => setComment(event.target.value)}
          />
        </label>
        <button type="submit" className="primary-btn full" disabled={mutation.isPending}>
          {mutation.isPending ? t("sending") : t("send")}
        </button>
      </form>
    </section>
  );
}
