import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SettingsPage } from "../../src/pages/SettingsPage";

const { fetchBackendVersion, resetLocalAppData, showConfirm } = vi.hoisted(() => ({
  fetchBackendVersion: vi.fn<() => Promise<string>>(),
  resetLocalAppData: vi.fn(),
  showConfirm: vi.fn<() => Promise<boolean>>(),
}));

vi.mock("../../src/api/version", () => ({
  FRONTEND_VERSION: "2.0.0",
  fetchBackendVersion,
}));
vi.mock("../../src/contexts/AppSettingsContext", () => ({
  useAppSettings: () => ({
    settings: {
      language: "en",
      text_size: "regular",
      timezone: "UTC",
      default_snooze_minutes: 10,
      remind_until_confirmed: true,
    },
    updateSettings: vi.fn(),
    t: (key: string) => key,
  }),
}));
vi.mock("../../src/utils/haptics", () => ({
  useHapticsEnabled: () => [true, vi.fn()],
}));
vi.mock("../../src/features/resetLocalData", () => ({ resetLocalAppData }));
vi.mock("../../src/telegramWebApp", () => ({ showConfirm }));

describe("SettingsPage versions", () => {
  beforeEach(() => {
    fetchBackendVersion.mockReset();
    resetLocalAppData.mockReset();
    showConfirm.mockReset();
  });

  it("shows the versions loaded by the frontend and backend", async () => {
    fetchBackendVersion.mockResolvedValue("2.0.0");

    render(
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>,
    );

    expect(screen.getByText("frontendVersion").nextSibling).toHaveTextContent("v2.0.0");
    await waitFor(() => expect(screen.getByText("backendVersion").nextSibling).toHaveTextContent("v2.0.0"));
    expect(screen.getByText("versionMatch")).toBeInTheDocument();
  });

  it("makes a partially loaded deployment visible", async () => {
    fetchBackendVersion.mockResolvedValue("1.3.0");

    render(
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByText("versionMismatch")).toBeInTheDocument());
  });

  it("shows when the backend version cannot be determined", async () => {
    fetchBackendVersion.mockResolvedValue("unknown");

    render(
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getAllByText("versionUnavailable")).toHaveLength(2));
  });

  it("clears local data only after the warning is confirmed", async () => {
    fetchBackendVersion.mockResolvedValue("2.0.0");
    showConfirm.mockResolvedValue(false);
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>,
    );

    await user.click(screen.getByRole("button", { name: "clearLocalData" }));
    expect(showConfirm).toHaveBeenCalledWith("clearLocalDataConfirm");
    expect(resetLocalAppData).not.toHaveBeenCalled();

    showConfirm.mockResolvedValue(true);
    await user.click(screen.getByRole("button", { name: "clearLocalData" }));
    expect(resetLocalAppData).toHaveBeenCalledOnce();
  });
});
