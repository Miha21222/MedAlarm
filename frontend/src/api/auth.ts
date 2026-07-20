import { activateMedicineStore } from "../features/medicines/localMedicines";
import { getTelegramWebApp } from "../telegramWebApp";
import { apiRequest, setAuthToken } from "./client";

export function isLocalPreview(): boolean {
  return (
    import.meta.env.DEV ||
    import.meta.env.MODE === "preview" ||
    import.meta.env.VITE_LOCAL_PREVIEW === "true"
  );
}

export async function authenticate(): Promise<void> {
  if (isLocalPreview()) return;
  const telegram = getTelegramWebApp();
  const response = await apiRequest<{ access_token: string; user: { telegram_id: number } }>("/auth/telegram", {
    method: "POST",
    body: JSON.stringify({ init_data: telegram?.initData || "" }),
  });
  setAuthToken(response.access_token);
  activateMedicineStore(response.user.telegram_id);
}
