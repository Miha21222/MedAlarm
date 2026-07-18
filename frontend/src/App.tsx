import { RotateCcw } from "lucide-react";
import { Route, Routes, useLocation } from "react-router-dom";
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
  const location = useLocation();
  const storedLanguage = readSettings().language;

  // Full-screen auth states normally exist only briefly or require a failed
  // Telegram launch. Keep stable, development-only URLs for visual review;
  // production builds compile this branch out via Vite's DEV constant.
  if (import.meta.env.DEV) {
    if (location.pathname === "/dev/loading") {
      return <LoadingState label={translate(storedLanguage, "loading")} />;
    }
    if (location.pathname === "/dev/error") {
      return (
        <LoadingState label={translate(storedLanguage, "syncError")}>
          <button className="primary-btn" onClick={auth.retry}>
            <RotateCcw size={18} />
            {translate(storedLanguage, "retry")}
          </button>
        </LoadingState>
      );
    }
    if (location.pathname === "/dev/open-in-telegram") {
      return <OpenInTelegram />;
    }
  }

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
    <ToastProvider>
      <AppSettingsProvider initialSettings={initialSettings}>
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
      </AppSettingsProvider>
    </ToastProvider>
  );
}
