import { shouldShowTelegramGate } from "../src/authGate";

function assertEqual<T>(actual: T, expected: T): void {
  if (actual !== expected) {
    throw new Error(`Expected ${String(expected)}, got ${String(actual)}`);
  }
}

assertEqual(
  shouldShowTelegramGate({ authError: "No Telegram initData available", hasTelegramInitData: false }),
  true,
);

assertEqual(
  shouldShowTelegramGate({ authError: "Authentication failed", hasTelegramInitData: true }),
  false,
);

assertEqual(
  shouldShowTelegramGate({ authError: null, hasTelegramInitData: false }),
  false,
);

console.log("authGate tests passed");
