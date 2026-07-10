import { hapticImpact, hapticNotification, hapticSelection } from "../src/utils/haptics";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

let calls = 0;
const localStorageValues = new Map<string, string>();

Object.defineProperty(globalThis, "window", {
  configurable: true,
  value: {
  localStorage: {
    getItem: (key: string) => localStorageValues.get(key) ?? null,
    setItem: (key: string, value: string) => void localStorageValues.set(key, value),
  },
  dispatchEvent: () => true,
  Telegram: {
    WebApp: {
      isVersionAtLeast: () => false,
      HapticFeedback: {
        impactOccurred: () => calls++,
        notificationOccurred: () => calls++,
        selectionChanged: () => calls++,
      },
    },
  },
  } as unknown as Window,
});

hapticImpact("light");
hapticNotification("success");
hapticSelection();

assert(calls === 0, "haptics should not call Telegram API when WebApp version is too old");

console.log("haptics tests passed");
