import { RotateCcw } from "lucide-react";
import { Route, Routes } from "react-router-dom";
import { hasTelegramLaunchData, shouldShowTelegramGate } from "./authGate";
import { Layout } from "./components/Layout";
import { LoadingState } from "./components/LoadingState";
import { OpenInTelegram } from "./components/OpenInTelegram";
import { AppSettingsProvider } from "./contexts/AppSettingsContext";
import { ToastProvider } from "./contexts/ToastContext";
import { readSettings } from "./features/storage";
import { useTelegramAuth } from "./hooks/useTelegramAuth";
import { translate } from "./i18n";
import { DashboardPage } from "./pages/DashboardPage";
import { HistoryPage } from "./pages/HistoryPage";
import { MedicineCreatePage } from "./pages/MedicineCreatePage";
import { MedicineDetailPage } from "./pages/MedicineDetailPage";
import { MedicineEditPage } from "./pages/MedicineEditPage";
import { MedicineListPage } from "./pages/MedicineListPage";
import { SettingsPage } from "./pages/SettingsPage";
import { BugReportPage } from "./pages/BugReportPage";
import { FeedbackRatingPage } from "./pages/FeedbackRatingPage";

export default function App() {
  const auth = useTelegramAuth();
  const storedLanguage = readSettings().language;

  if (auth.loading) {
    return <LoadingState label={translate(storedLanguage, "loading")} />;
  }

  if (auth.error) {
    if (shouldShowTelegramGate({ authError: auth.error, hasTelegramInitData: hasTelegramLaunchData() })) {
      return <OpenInTelegram />;
    }
    return (
      <LoadingState label={auth.error}>
        <button className="primary-btn" onClick={auth.retry}>
          <RotateCcw size={18} />
          {translate(storedLanguage, "retry")}
        </button>
      </LoadingState>
    );
  }

  const initialSettings = { ...readSettings(), ...auth.settings };

  return (
    <AppSettingsProvider initialSettings={initialSettings}>
      <ToastProvider>
        <Layout>
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/medicines" element={<MedicineListPage />} />
            <Route path="/medicines/new" element={<MedicineCreatePage />} />
            <Route path="/medicines/:medicineId" element={<MedicineDetailPage />} />
            <Route path="/medicines/:medicineId/edit" element={<MedicineEditPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/settings/feedback" element={<FeedbackRatingPage />} />
            <Route path="/settings/bug-report" element={<BugReportPage />} />
          </Routes>
        </Layout>
      </ToastProvider>
    </AppSettingsProvider>
  );
}
