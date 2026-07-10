import { apiUpload } from "./client";

export type FeedbackKind = "rating" | "bug";

export interface FeedbackPayload {
  kind: FeedbackKind;
  rating?: number | null;
  message?: string | null;
  screenshot?: File | null;
}

export function submitFeedback(payload: FeedbackPayload): Promise<{ id: number }> {
  const form = new FormData();
  form.append("kind", payload.kind);
  if (payload.rating != null) form.append("rating", String(payload.rating));
  if (payload.message) form.append("message", payload.message);
  if (payload.screenshot) form.append("screenshot", payload.screenshot, payload.screenshot.name);
  return apiUpload<{ id: number }>("/feedback", form);
}
