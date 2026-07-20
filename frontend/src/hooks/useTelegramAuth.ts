import { useEffect, useState } from "react";
import { authenticate } from "../api/auth";
interface AuthState {
  loading: boolean;
  error: string | null;
  authenticated: boolean;
}

// MedAlarm's authenticate() already handles both the local-preview bypass
// (MODE==="preview"/DEV/VITE_LOCAL_PREVIEW) and the real Telegram initData
// POST + token storage internally, so this hook is a thinner state-machine
// wrapper than PocketMind's useTelegramAuth, which does that work itself.
export function useTelegramAuth(): AuthState & { retry: () => void } {
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<AuthState>({
    loading: true,
    error: null,
    authenticated: false,
  });

  useEffect(() => {
    let cancelled = false;
    setState((prev) => ({ ...prev, loading: true, error: null }));
    const init = async () => {
      try {
        await authenticate();
        if (!cancelled) {
          setState({ loading: false, error: null, authenticated: true });
        }
      } catch (error) {
        if (!cancelled) {
          setState({
            loading: false,
            authenticated: false,
            error: error instanceof Error ? error.message : "Authentication failed",
          });
        }
      }
    };
    void init();
    return () => {
      cancelled = true;
    };
  }, [attempt]);

  return { ...state, retry: () => setAttempt((value) => value + 1) };
}
