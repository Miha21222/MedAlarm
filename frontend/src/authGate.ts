interface TelegramGateState {
  authError: string | null;
  hasTelegramInitData: boolean;
}

type TelegramWindow = Window & {
  Telegram?: {
    WebApp?: {
      initData?: string;
    };
  };
};

export function shouldShowTelegramGate({ authError, hasTelegramInitData }: TelegramGateState): boolean {
  return Boolean(authError && !hasTelegramInitData);
}

export function hasTelegramLaunchData(): boolean {
  const searchParams = new URLSearchParams(window.location.search);
  const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ""));
  const telegramWindow = window as TelegramWindow;
  return Boolean(
    telegramWindow.Telegram?.WebApp?.initData ||
      searchParams.get("tgWebAppData") ||
      hashParams.get("tgWebAppData"),
  );
}
