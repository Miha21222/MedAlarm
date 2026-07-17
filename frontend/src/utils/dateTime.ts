// Timezone-aware date math, ported from PocketMind's utils/dateTime.ts. Only the
// subset MedAlarm needs is kept: schedules are daily/day-of-week only (no
// recurrence-rule or deadline timing engine), so the recurrence/deadline-input
// helpers from the original file are intentionally not ported.

export function formatInTimezone(value: string | null, timezone: string, locale: string, withYear = false): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat(locale, {
    timeZone: timezone,
    day: "2-digit",
    month: "short",
    ...(withYear ? { year: "numeric" } : {}),
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function formatTimeInTimezone(value: string | null, timezone: string, locale: string): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat(locale, {
    timeZone: timezone,
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function formatDayInTimezone(value: string | null, timezone: string, locale: string): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat(locale, {
    timeZone: timezone,
    weekday: "short",
    day: "numeric",
    month: "short",
  }).format(date);
}

// Stable YYYY-MM-DD key for the given instant in the user's timezone, used to
// bucket doses into day groups.
export function dayKeyInTimezone(value: string | null, timezone: string): string {
  if (!value) return "none";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "none";
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: timezone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(date);
}

type ZonedParts = {
  year: number;
  month: number;
  day: number;
  hour: number;
  minute: number;
  second: number;
};

function zonedPartNumber(parts: Intl.DateTimeFormatPart[], type: Intl.DateTimeFormatPartTypes): number {
  return Number(parts.find((part) => part.type === type)?.value ?? 0);
}

function getZonedParts(date: Date, timezone: string): ZonedParts {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: timezone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
    hourCycle: "h23",
  }).formatToParts(date);

  return {
    year: zonedPartNumber(parts, "year"),
    month: zonedPartNumber(parts, "month"),
    day: zonedPartNumber(parts, "day"),
    hour: zonedPartNumber(parts, "hour"),
    minute: zonedPartNumber(parts, "minute"),
    second: zonedPartNumber(parts, "second"),
  };
}

function getTimezoneOffsetMs(date: Date, timezone: string): number {
  const zoned = getZonedParts(date, timezone);
  const zonedAsUtc = Date.UTC(zoned.year, zoned.month - 1, zoned.day, zoned.hour, zoned.minute, zoned.second, 0);
  return zonedAsUtc - date.getTime();
}

function splitDayKey(dayKey: string): [number, number, number] | null {
  const match = dayKey.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) return null;
  return [Number(match[1]), Number(match[2]), Number(match[3])];
}

export function zonedDayKeyFromTimestamp(timestamp: number, timezone: string): string {
  const zoned = getZonedParts(new Date(timestamp), timezone);
  return `${String(zoned.year).padStart(4, "0")}-${String(zoned.month).padStart(2, "0")}-${String(zoned.day).padStart(2, "0")}`;
}

export function addDaysToDayKey(dayKey: string, days: number): string {
  const parts = splitDayKey(dayKey);
  if (!parts) return dayKey;
  const [year, month, day] = parts;
  const date = new Date(Date.UTC(year, month - 1, day, 0, 0, 0, 0));
  date.setUTCDate(date.getUTCDate() + days);
  return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, "0")}-${String(date.getUTCDate()).padStart(2, "0")}`;
}

export function zonedDateTimeToUtcTimestamp(dayKey: string, hhmm: string, timezone: string): number | null {
  const dateParts = splitDayKey(dayKey);
  if (!dateParts) return null;
  const timeParts = hhmm.match(/^(\d{2}):(\d{2})$/);
  if (!timeParts) return null;
  const [year, month, day] = dateParts;
  const hours = Number(timeParts[1]);
  const minutes = Number(timeParts[2]);
  const utcGuess = Date.UTC(year, month - 1, day, hours, minutes, 0, 0);
  const firstPass = utcGuess - getTimezoneOffsetMs(new Date(utcGuess), timezone);
  const secondPass = utcGuess - getTimezoneOffsetMs(new Date(firstPass), timezone);
  return secondPass;
}

export function getZonedDayRange(now: Date, timezone: string): { start: number; end: number } {
  const todayKey = zonedDayKeyFromTimestamp(now.getTime(), timezone);
  const tomorrowKey = addDaysToDayKey(todayKey, 1);
  return {
    start: zonedDateTimeToUtcTimestamp(todayKey, "00:00", timezone) ?? now.getTime(),
    end: zonedDateTimeToUtcTimestamp(tomorrowKey, "00:00", timezone) ?? now.getTime(),
  };
}

export function getZonedCalendarPeriodRange(
  now: Date,
  timezone: string,
  period: "today" | "week" | "month",
): { start: number; end: number } {
  if (period === "today") return getZonedDayRange(now, timezone);

  const todayKey = zonedDayKeyFromTimestamp(now.getTime(), timezone);
  const parts = splitDayKey(todayKey);
  if (!parts) return { start: now.getTime(), end: now.getTime() };
  const [year, month, day] = parts;

  let startKey: string;
  let endKey: string;
  if (period === "week") {
    const sundayBasedWeekday = new Date(Date.UTC(year, month - 1, day)).getUTCDay();
    const daysSinceMonday = sundayBasedWeekday === 0 ? 6 : sundayBasedWeekday - 1;
    startKey = addDaysToDayKey(todayKey, -daysSinceMonday);
    endKey = addDaysToDayKey(startKey, 7);
  } else {
    startKey = `${year}-${String(month).padStart(2, "0")}-01`;
    const nextMonth = new Date(Date.UTC(year, month, 1));
    endKey = `${nextMonth.getUTCFullYear()}-${String(nextMonth.getUTCMonth() + 1).padStart(2, "0")}-01`;
  }

  return {
    start: zonedDateTimeToUtcTimestamp(startKey, "00:00", timezone) ?? now.getTime(),
    end: zonedDateTimeToUtcTimestamp(endKey, "00:00", timezone) ?? now.getTime(),
  };
}
