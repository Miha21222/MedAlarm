import { useCallback, useState } from "react";

export function readStoredEnumValue<T extends string>(storageKey: string, defaultValue: T, allowedValues: readonly T[]): T {
  if (typeof window === "undefined") return defaultValue;

  try {
    const raw = window.localStorage.getItem(storageKey);
    if (raw && allowedValues.includes(raw as T)) {
      return raw as T;
    }
  } catch {
    return defaultValue;
  }

  return defaultValue;
}

export function writeStoredEnumValue<T extends string>(storageKey: string, value: T): void {
  if (typeof window === "undefined") return;

  try {
    window.localStorage.setItem(storageKey, value);
  } catch {
    // Filter persistence should never block navigation or rendering.
  }
}

export function usePersistentEnumState<T extends string>(
  storageKey: string,
  defaultValue: T,
  allowedValues: readonly T[],
): { value: T; setValue: (next: T) => void; reset: () => void; isDefault: boolean } {
  const [value, setValueState] = useState<T>(() => readStoredEnumValue(storageKey, defaultValue, allowedValues));

  const setValue = useCallback(
    (next: T) => {
      setValueState(next);
      writeStoredEnumValue(storageKey, next);
    },
    [storageKey],
  );

  const reset = useCallback(() => {
    setValue(defaultValue);
  }, [defaultValue, setValue]);

  return {
    value,
    setValue,
    reset,
    isDefault: value === defaultValue,
  };
}
