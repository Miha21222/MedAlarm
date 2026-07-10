import { useCallback, useMemo, useRef, useState } from "react";
import type { Language } from "../types";

// Minimal shape of the (non-standard, vendor-prefixed on some engines) Web
// Speech API needed here. No transcription backend involved: this only works
// where the browser/WebView itself implements SpeechRecognition (notably not
// on iOS Safari) — callers must check `supported` and hide the mic button
// when it's false rather than assume it always works.
interface SpeechRecognitionResult {
  0: { transcript: string };
}

interface SpeechRecognitionResultEvent extends Event {
  results: ArrayLike<SpeechRecognitionResult>;
}

interface SpeechRecognitionLike extends EventTarget {
  lang: string;
  interimResults: boolean;
  maxAlternatives: number;
  start: () => void;
  stop: () => void;
  onresult: ((event: SpeechRecognitionResultEvent) => void) | null;
  onerror: (() => void) | null;
  onend: (() => void) | null;
}

type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  }
}

const LOCALE_BY_LANGUAGE: Record<Language, string> = {
  ru: "ru-RU",
  uk: "uk-UA",
  en: "en-US",
};

function getSpeechRecognitionConstructor(): SpeechRecognitionConstructor | undefined {
  if (typeof window === "undefined") return undefined;
  return window.SpeechRecognition ?? window.webkitSpeechRecognition;
}

export function isSpeechInputSupported(): boolean {
  return getSpeechRecognitionConstructor() !== undefined;
}

export function useSpeechInput(language: Language, onResult: (transcript: string) => void) {
  const [recording, setRecording] = useState(false);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const supported = useMemo(() => isSpeechInputSupported(), []);

  const stop = useCallback(() => {
    recognitionRef.current?.stop();
  }, []);

  const start = useCallback(() => {
    const Constructor = getSpeechRecognitionConstructor();
    if (!Constructor) return;
    const recognition = new Constructor();
    recognition.lang = LOCALE_BY_LANGUAGE[language];
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onresult = (event) => {
      const transcript = event.results[event.results.length - 1]?.[0]?.transcript ?? "";
      if (transcript.trim()) onResult(transcript.trim());
    };
    recognition.onerror = () => setRecording(false);
    recognition.onend = () => setRecording(false);
    recognitionRef.current = recognition;
    setRecording(true);
    recognition.start();
  }, [language, onResult]);

  const toggle = useCallback(() => {
    if (recording) {
      stop();
    } else {
      start();
    }
  }, [recording, start, stop]);

  return { supported, recording, toggle };
}
