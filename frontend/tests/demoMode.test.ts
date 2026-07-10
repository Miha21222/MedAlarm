import {
  configureDemoModeAvailability,
  isDemoModeAvailable,
  isDemoModeEnabled,
  setDemoModeEnabled,
} from "../src/features/demo/demoMode";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

const memory = new Map<string, string>();
const localStorage = {
  getItem: (key: string) => memory.get(key) ?? null,
  setItem: (key: string, value: string) => void memory.set(key, value),
  removeItem: (key: string) => void memory.delete(key),
};

Object.assign(globalThis, {
  window: {
    localStorage,
    dispatchEvent: () => true,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
  },
  CustomEvent: class CustomEvent {
    constructor(public type: string) {}
  },
});

configureDemoModeAvailability(true);
setDemoModeEnabled(true);
assert(isDemoModeAvailable(), "demo mode should be available after an explicit development configuration");
assert(isDemoModeEnabled(), "demo mode should be enabled in an available development build");

configureDemoModeAvailability(false);
assert(!isDemoModeAvailable(), "demo mode should be unavailable in a production build");
assert(!isDemoModeEnabled(), "production must ignore and clear previously stored demo state");
setDemoModeEnabled(true);
assert(!isDemoModeEnabled(), "production must reject attempts to re-enable demo mode");

console.log("demoMode tests passed");
