import { readStoredEnumValue, writeStoredEnumValue } from "../src/hooks/usePersistentEnumState";

function assertEqual<T>(actual: T, expected: T): void {
  if (JSON.stringify(actual) !== JSON.stringify(expected)) {
    throw new Error(`Expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
  }
}

function createWindowStub(initial: Record<string, string> = {}) {
  const store = new Map(Object.entries(initial));
  return {
    localStorage: {
      getItem(key: string) {
        return store.has(key) ? store.get(key)! : null;
      },
      setItem(key: string, value: string) {
        store.set(key, value);
      },
    },
  };
}

{
  const originalWindow = globalThis.window;
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: createWindowStub({ "pref.key": "soon" }),
  });

  assertEqual(readStoredEnumValue("pref.key", "today", ["today", "soon"] as const), "soon");

  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: originalWindow,
  });
}

{
  const originalWindow = globalThis.window;
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: createWindowStub({ "pref.key": "invalid" }),
  });

  assertEqual(readStoredEnumValue("pref.key", "today", ["today", "soon"] as const), "today");

  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: originalWindow,
  });
}

{
  const originalWindow = globalThis.window;
  const nextWindow = createWindowStub();
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: nextWindow,
  });

  writeStoredEnumValue("pref.key", "overdue");
  assertEqual(nextWindow.localStorage.getItem("pref.key"), "overdue");

  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: originalWindow,
  });
}

console.log("persistentEnumState tests passed");
