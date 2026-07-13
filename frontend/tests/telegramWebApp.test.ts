import {
  calculateKeyboardOffset,
  initializeTelegramWebApp,
  showConfirm,
  type TelegramWebAppControls,
  type VirtualKeyboardControls,
} from "../src/telegramWebApp";

function assertEqual<T>(actual: T, expected: T): void {
  if (actual !== expected) {
    throw new Error(`Expected ${String(expected)}, got ${String(actual)}`);
  }
}

function buildWebApp(): TelegramWebAppControls & { calls: string[] } {
  const calls: string[] = [];
  return {
    calls,
    ready: () => calls.push("ready"),
    expand: () => calls.push("expand"),
    isVersionAtLeast: (version) => version === "8.0",
  };
}

{
  assertEqual(calculateKeyboardOffset(800, 480), 320);
  assertEqual(calculateKeyboardOffset(800, 480, 20), 300);
  assertEqual(calculateKeyboardOffset(480, 800), 0);
}

{
  const webApp = buildWebApp();
  const virtualKeyboard: VirtualKeyboardControls = { overlaysContent: false };
  initializeTelegramWebApp(webApp, virtualKeyboard);

  assertEqual(virtualKeyboard.overlaysContent, true);
  assertEqual(webApp.calls.join(","), "ready,expand");
}

{
  const calls: string[] = [];
  initializeTelegramWebApp({
    ready: () => calls.push("ready"),
    expand: () => calls.push("expand"),
    isVersionAtLeast: () => false,
  });

  assertEqual(calls.join(","), "ready,expand");
}

{
  initializeTelegramWebApp(undefined);
}

async function run(): Promise<void> {
  {
    // Prefers Telegram's non-blocking showConfirm over window.confirm, which
    // desyncs touch handling in the Telegram Android WebView after it closes.
    const calls: string[] = [];
    const confirmed = await showConfirm("Delete?", {
      showConfirm: (message, callback) => {
        calls.push(message);
        callback(true);
      },
    });
    assertEqual(confirmed, true);
    assertEqual(calls.join(","), "Delete?");
  }

  {
    const confirmed = await showConfirm("Delete?", {
      showConfirm: (_message, callback) => callback(false),
    });
    assertEqual(confirmed, false);
  }

  {
    // No Telegram WebApp and no browser window in this test environment:
    // resolves to false instead of throwing.
    const confirmed = await showConfirm("Delete?", {});
    assertEqual(confirmed, false);
  }

  console.log("telegramWebApp tests passed");
}

run();
