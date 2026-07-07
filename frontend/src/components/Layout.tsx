import { Activity, ArrowLeft, History, Languages, Pill, Plus, Settings as SettingsIcon } from "lucide-react";
import type { ReactNode } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { useAppSettings } from "../contexts/AppSettingsContext";
import type { Language } from "../types";
import { hapticImpact, hapticSelection } from "../utils/haptics";

const LANGUAGE_ORDER: Language[] = ["ru", "uk", "en"];

// MedAlarm keeps its existing 4-item bottom nav (Dashboard/Medicines/History/
// Settings) rather than PocketMind's 3-icon convention — it already fits
// cleanly in the current CSS grid and demoting History to secondary
// navigation would be a regression, not parity.
const ROOT_PATHS = ["/", "/medicines", "/history", "/settings"];

export function Layout({ children }: { children: ReactNode }) {
  const { settings, t, setLanguage } = useAppSettings();
  const location = useLocation();
  const navigate = useNavigate();

  const title = location.pathname === "/"
    ? t("dashboard")
    : location.pathname.startsWith("/medicines")
      ? t("medicines")
      : location.pathname.startsWith("/history")
        ? t("history")
        : t("settings");
  const nextLanguage = LANGUAGE_ORDER[(LANGUAGE_ORDER.indexOf(settings.language) + 1) % LANGUAGE_ORDER.length];

  return (
    <div className="app-shell">
      <header className="app-header">
        <Link to="/" className="emblem" aria-label="MedAlarm">
          <img src={`${import.meta.env.BASE_URL}logo.png`} alt="" />
        </Link>
        <div>
          <span className="header-kicker">MedAlarm</span>
          <h1>{title}</h1>
        </div>
        <button
          className="language-btn"
          onClick={() => {
            hapticSelection();
            setLanguage(nextLanguage);
          }}
          aria-label={t("language")}
        >
          <Languages size={17} />
          {settings.language.toUpperCase()}
        </button>
      </header>

      <main className="app-content">{children}</main>

      {!ROOT_PATHS.includes(location.pathname) ? (
        <button
          className="floating-back"
          onClick={() => {
            hapticImpact("light");
            navigate(-1);
          }}
          aria-label={t("cancel")}
        >
          <ArrowLeft size={28} />
        </button>
      ) : null}
      {location.pathname !== "/medicines/new" ? (
        <Link className="floating-add" to="/medicines/new" aria-label={t("addMedicine")}>
          <Plus size={30} />
        </Link>
      ) : null}

      <nav className="bottom-nav">
        <NavItem to="/" label={t("dashboard")} icon={<Activity />} />
        <NavItem to="/medicines" label={t("medicines")} icon={<Pill />} />
        <NavItem to="/history" label={t("history")} icon={<History />} />
        <NavItem to="/settings" label={t("settings")} icon={<SettingsIcon />} />
      </nav>
    </div>
  );
}

function NavItem({ to, label, icon }: { to: string; label: string; icon: ReactNode }) {
  return (
    <NavLink to={to} end className={({ isActive }) => (isActive ? "active" : "")} aria-label={label}>
      {icon}
      <span>{label}</span>
    </NavLink>
  );
}
