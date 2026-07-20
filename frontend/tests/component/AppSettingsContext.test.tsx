import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AppSettingsProvider, useAppSettings } from "../../src/contexts/AppSettingsContext";
import { ToastProvider } from "../../src/contexts/ToastContext";
import { PENDING_SETTINGS_KEY, reminderSettingsFrom } from "../../src/features/settingsSyncStorage";
import { SETTINGS_KEY } from "../../src/features/storage";
import type { ReminderSettings, UserSettings } from "../../src/types";

const { saveReminderSettings } = vi.hoisted(() => ({
  saveReminderSettings: vi.fn<(settings: ReminderSettings) => Promise<void>>(),
}));
vi.mock("../../src/api/settings", () => ({ saveReminderSettings }));

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
    <>
      <button type="button" onClick={() => updateSettings({ text_size: "large" })}>
        size:{settings.text_size}
      </button>
      <button type="button" onClick={() => updateSettings({ timezone: "UTC" })}>
        timezone:{settings.timezone}
      </button>
    </>
  );
}

function renderSettings() {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(initial));
  return render(
    <ToastProvider>
      <AppSettingsProvider>
        <SettingsProbe />
      </AppSettingsProvider>
    </ToastProvider>,
  );
}

describe("AppSettingsProvider", () => {
  beforeEach(() => {
    localStorage.clear();
    saveReminderSettings.mockReset();
  });

  it("retries a persisted reminder projection without replacing local app settings", async () => {
    const pending = { ...reminderSettingsFrom(initial), timezone: "Europe/Warsaw" };
    localStorage.setItem(PENDING_SETTINGS_KEY, JSON.stringify(pending));
    saveReminderSettings.mockResolvedValue();

    renderSettings();

    expect(screen.getByText("size:regular")).toBeInTheDocument();
    expect(screen.getByText("timezone:Europe/Kyiv")).toBeInTheDocument();
    await waitFor(() => expect(saveReminderSettings).toHaveBeenCalledWith(pending));
    await waitFor(() => expect(localStorage.getItem(PENDING_SETTINGS_KEY)).toBeNull());
  });

  it("keeps UI-only settings local and never sends them in the reminder projection", async () => {
    saveReminderSettings.mockResolvedValue();
    renderSettings();
    await waitFor(() => expect(saveReminderSettings).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByText("size:regular"));

    expect(screen.getByText("size:large")).toBeInTheDocument();
    expect(JSON.parse(localStorage.getItem(SETTINGS_KEY) ?? "null").text_size).toBe("large");
    expect(saveReminderSettings).toHaveBeenCalledTimes(1);
    expect(saveReminderSettings.mock.calls[0][0]).not.toHaveProperty("text_size");
  });

  it("keeps a failed reminder-setting update queued while updating local UI immediately", async () => {
    saveReminderSettings.mockResolvedValueOnce();
    renderSettings();
    await waitFor(() => expect(saveReminderSettings).toHaveBeenCalledTimes(1));
    saveReminderSettings.mockRejectedValueOnce(new Error("offline"));

    fireEvent.click(screen.getByText("timezone:Europe/Kyiv"));

    expect(screen.getByText("timezone:UTC")).toBeInTheDocument();
    await waitFor(() => expect(saveReminderSettings).toHaveBeenCalledTimes(2));
    expect(JSON.parse(localStorage.getItem(PENDING_SETTINGS_KEY) ?? "null").timezone).toBe("UTC");
  });
});
