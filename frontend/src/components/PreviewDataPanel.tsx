import { Database } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { MEDICINES_ALL_QUERY_KEY, MEDICINES_SYNC_QUERY_KEY } from "../features/medicines/cache";
import { clearDemoIntakeHistory } from "../features/medicines/localIntakeHistory";
import { useDemoModeEnabled } from "../features/demo/demoMode";
import { useAppSettings } from "../contexts/AppSettingsContext";
import { useToast } from "../contexts/ToastContext";

// A read-only sandbox toggle, not a one-shot seeding action: flipping it on
// makes every medicine/dashboard/history read serve generated fixtures
// instead of real storage (see demoMode.ts + the isDemoModeEnabled() checks
// across the medicines/history feature modules); flipping it off instantly
// restores the user's real data, which was never touched while it was on.
export function PreviewDataPanel() {
  const queryClient = useQueryClient();
  const { t } = useAppSettings();
  const { showToast } = useToast();
  const [demoEnabled, setDemoEnabled] = useDemoModeEnabled();

  const toggle = (next: boolean) => {
    setDemoEnabled(next);
    clearDemoIntakeHistory();
    void queryClient.invalidateQueries({ queryKey: MEDICINES_ALL_QUERY_KEY });
    void queryClient.invalidateQueries({ queryKey: MEDICINES_SYNC_QUERY_KEY });
    showToast({ message: t(next ? "demoModeOnToast" : "demoModeOffToast"), tone: "success" });
  };

  return (
    <div className="preview-data-panel">
      <Database size={18} />
      <span className="preview-data-label">
        <strong>{t("previewDataHint")}</strong>
        <small>{t("demoModeHint")}</small>
      </span>
      <span className="toggle-switch">
        <input type="checkbox" checked={demoEnabled} onChange={(event) => toggle(event.target.checked)} />
        <span className="toggle-slider" />
      </span>
    </div>
  );
}
