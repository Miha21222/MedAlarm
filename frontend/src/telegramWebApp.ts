export type TelegramHapticImpactStyle = "light" | "medium" | "heavy" | "rigid" | "soft";
export type TelegramHapticNotificationType = "error" | "success" | "warning";

export interface TelegramHapticFeedback {
  impactOccurred?: (style: TelegramHapticImpactStyle) => void;
  notificationOccurred?: (type: TelegramHapticNotificationType) => void;
  selectionChanged?: () => void;
}

export interface TelegramWebAppControls {
  initData?: string;
  isVersionAtLeast?: (version: string) => boolean;
  ready?: () => void;
  expand?: () => void;
  HapticFeedback?: TelegramHapticFeedback;
  showConfirm?: (message: string, callback: (confirmed: boolean) => void) => void;
}

interface TelegramWindow extends Window {
  Telegram?: {
    WebApp?: TelegramWebAppControls;
  };
}

declare global {
  interface Window {
    Telegram?: {
      WebApp?: TelegramWebAppControls;
    };
  }
}

export function getTelegramWebApp(win?: Window): TelegramWebAppControls | undefined {
  const sourceWindow = win ?? (typeof window === "undefined" ? undefined : window);
  if (!sourceWindow) return undefined;
  return (sourceWindow as TelegramWindow).Telegram?.WebApp;
}

export function initializeTelegramWebApp(webApp: TelegramWebAppControls | undefined = getTelegramWebApp()): void {
  webApp?.ready?.();
  webApp?.expand?.();
}

// The blocking browser window.confirm() desyncs the Telegram Android WebView's
// touch event routing once dismissed, leaving parts of the page unclickable
// until the app is restarted. Telegram's own showConfirm() is non-blocking and
// avoids that; fall back to window.confirm outside of Telegram (e.g. dev:local).
export function showConfirm(message: string, webApp: TelegramWebAppControls | undefined = getTelegramWebApp()): Promise<boolean> {
  if (webApp?.showConfirm) {
    return new Promise((resolve) => webApp.showConfirm!(message, resolve));
  }
  return Promise.resolve(typeof window === "undefined" ? false : window.confirm(message));
}
