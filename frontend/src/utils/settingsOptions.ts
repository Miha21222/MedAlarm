// Curated pickers for the Settings page. The user's current saved value is
// always included even if it isn't in the curated list, so an unusual
// existing value (e.g. imported from an older free-text field) never
// silently disappears from the selector.

export const COMMON_TIMEZONES = [
  "UTC",
  "Europe/Kaliningrad",
  "Europe/Kyiv",
  "Europe/Minsk",
  "Europe/Chisinau",
  "Europe/Moscow",
  "Europe/Warsaw",
  "Europe/Berlin",
  "Europe/London",
  "Asia/Baku",
  "Asia/Yerevan",
  "Asia/Tbilisi",
  "Asia/Yekaterinburg",
  "Asia/Almaty",
  "Asia/Tashkent",
] as const;

export function timezoneLabel(timezone: string): string {
  try {
    const parts = new Intl.DateTimeFormat("en-US", {
      timeZone: timezone,
      timeZoneName: "shortOffset",
    }).formatToParts(new Date());
    const offset = parts.find((part) => part.type === "timeZoneName")?.value ?? "";
    return offset ? `${timezone} (${offset})` : timezone;
  } catch {
    return timezone;
  }
}

export function timezoneOptions(current: string): string[] {
  const known: string[] = [...COMMON_TIMEZONES];
  return current && !known.includes(current) ? [current, ...known] : known;
}

export const SNOOZE_MINUTE_OPTIONS = [5, 10, 15, 20, 25, 30, 45, 60, 90, 120] as const;

export function snoozeOptions(current: number): number[] {
  const known: number[] = [...SNOOZE_MINUTE_OPTIONS];
  return known.includes(current) ? known : [current, ...known].sort((a, b) => a - b);
}
