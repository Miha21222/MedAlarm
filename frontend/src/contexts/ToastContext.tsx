import { createContext, PropsWithChildren, useContext, useMemo, useState } from "react";

type ToastTone = "success" | "error" | "info";

type ToastPayload = {
  message: string;
  tone?: ToastTone;
};

type ToastState = {
  id: number;
  message: string;
  tone: ToastTone;
  phase: "entering" | "leaving";
} | null;

type ToastContextValue = {
  showToast: (payload: ToastPayload) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: PropsWithChildren) {
  const [toast, setToast] = useState<ToastState>(null);

  const value = useMemo<ToastContextValue>(
    () => ({
      showToast: ({ message, tone = "info" }) => {
        const id = Date.now();
        setToast({ id, message, tone, phase: "entering" });
        window.setTimeout(() => {
          setToast((prev) => (prev?.id === id ? { ...prev, phase: "leaving" } : prev));
        }, 2200);
        window.setTimeout(() => {
          setToast((prev) => (prev?.id === id ? null : prev));
        }, 2600);
      },
    }),
    [],
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      {toast ? <div className={`toast toast-${toast.tone} toast-${toast.phase}`}>{toast.message}</div> : null}
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within ToastProvider");
  }
  return context;
}
