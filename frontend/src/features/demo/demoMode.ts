import { useEffect, useState } from "react";

// Demo mode is a read-only sandbox switch: while enabled, medicine/dashboard/
// history reads are served from generated fixtures instead of real storage,
// and real-storage writes are skipped entirely — so flipping it back off
// instantly restores the user's actual data, untouched the whole time it was on.
const DEMO_MODE_KEY = "medalarm.demoMode.v1";
export const DEMO_MODE_CHANGED_EVENT = "medalarm:demo-mode-changed";
let demoModeAvailable = false;

export function configureDemoModeAvailability(available: boolean): void {
  demoModeAvailable = available;
  if (typeof window === "undefined" || available) return;
  window.localStorage.removeItem(DEMO_MODE_KEY);
}

export function isDemoModeAvailable(): boolean {
  return demoModeAvailable;
}

export function isDemoModeEnabled(): boolean {
  if (typeof window === "undefined" || !demoModeAvailable) return false;
  return window.localStorage.getItem(DEMO_MODE_KEY) === "1";
}

export function setDemoModeEnabled(enabled: boolean): void {
  if (typeof window === "undefined") return;
  if (!demoModeAvailable) {
    window.localStorage.removeItem(DEMO_MODE_KEY);
    return;
  }
  window.localStorage.setItem(DEMO_MODE_KEY, enabled ? "1" : "0");
  window.dispatchEvent(new CustomEvent(DEMO_MODE_CHANGED_EVENT));
}

export function useDemoModeEnabled(): [boolean, (enabled: boolean) => void] {
  const [enabled, setEnabled] = useState(isDemoModeEnabled);
  useEffect(() => {
    const sync = () => setEnabled(isDemoModeEnabled());
    window.addEventListener(DEMO_MODE_CHANGED_EVENT, sync);
    return () => window.removeEventListener(DEMO_MODE_CHANGED_EVENT, sync);
  }, []);
  return [enabled, setDemoModeEnabled];
}
