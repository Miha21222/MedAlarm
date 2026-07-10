import { Send } from "lucide-react";
import { translate } from "../i18n";
import type { Language } from "../types";

// New capability adopted from PocketMind: a dedicated gate screen for when the
// app is opened outside Telegram, instead of falling through to a generic
// retry error. Translations aren't loaded yet at this point in the auth flow,
// so the language is guessed from the browser locale, matching PocketMind's
// same approach in App.tsx's pre-auth error UI.
function guessLanguage(): Language {
  const locale = typeof navigator !== "undefined" ? navigator.language.toLowerCase() : "ru";
  if (locale.startsWith("uk")) return "uk";
  if (locale.startsWith("en")) return "en";
  return "ru";
}

export function OpenInTelegram() {
  const language = guessLanguage();
  const botUsername = import.meta.env.VITE_BOT_USERNAME as string | undefined;

  return (
    <main className="brand-state">
      <div className="brand-orbit">
        <img src={`${import.meta.env.BASE_URL}logo.png`} alt="MedAlarm" />
      </div>
      <h2 style={{ margin: 0 }}>{translate(language, "openInTelegramTitle")}</h2>
      <p>{translate(language, "openInTelegramHint")}</p>
      {botUsername ? (
        <a className="primary-btn" href={`https://t.me/${botUsername}`}>
          <Send size={18} />
          {translate(language, "openInTelegramButton")}
        </a>
      ) : null}
    </main>
  );
}
