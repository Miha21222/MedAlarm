import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AppSettingsProvider, useAppSettings } from "../../src/contexts/AppSettingsContext";
import { ToastProvider } from "../../src/contexts/ToastContext";
import { PENDING_SETTINGS_KEY } from "../../src/features/settingsSyncStorage";
import type { UserSettings } from "../../src/types";

const { saveSettings } = vi.hoisted(() => ({
  saveSettings: vi.fn<(settings: UserSettings) => Promise<void>>(),
}));
vi.mock("../../src/api/settings", () => ({ saveSettings }));

const initial: UserSettings = {
  language: "ru",
  text_size: "regular",
  timezone: "Europe/Kyiv",
  default_snooze_minutes: 10,
  remind_until_confirmed: true,
};

function SettingsProbe() {
  const { settings, updateSettings } = useAppSettings();
  return (
    <button type="button" onClick={() => updateSettings({ text_size: "large" })}>
      {settings.text_size}
    </button>
  );
}

function renderSettings() {
  return render(
    <ToastProvider>
      <AppSettingsProvider initialSettings={initial}>
        <SettingsProbe />
      </AppSettingsProvider>
    </ToastProvider>,
  );
}

describe("AppSettingsProvider", () => {
  beforeEach(() => {
    localStorage.clear();
    saveSettings.mockReset();
  });

  it("retries a persisted settings snapshot after reload and clears it on success", async () => {
    const pending = { ...initial, text_size: "large" as const };
    localStorage.setItem(PENDING_SETTINGS_KEY, JSON.stringify(pending));
    saveSettings.mockResolvedValue();

    renderSettings();

    expect(screen.getByRole("button")).toHaveTextContent("large");
    await waitFor(() => expect(saveSettings).toHaveBeenCalledWith(pending));
    await waitFor(() => expect(localStorage.getItem(PENDING_SETTINGS_KEY)).toBeNull());
  });

  it("keeps a failed update queued while updating the UI immediately", async () => {
    saveSettings.mockRejectedValue(new Error("offline"));
    renderSettings();

    fireEvent.click(screen.getByRole("button"));

    expect(screen.getByRole("button")).toHaveTextContent("large");
    await waitFor(() => expect(saveSettings).toHaveBeenCalledTimes(1));
    expect(JSON.parse(localStorage.getItem(PENDING_SETTINGS_KEY) ?? "null").text_size).toBe("large");
  });
});
