// Helpers de fechas para el calendario, sin dependencias. Todo en hora local:
// las fechas viajan como "YYYY-MM-DD" y la planificacion como
// "YYYY-MM-DDTHH:MM:SS" sin zona (el backend las guarda tal cual, naive).

const pad = (n: number) => String(n).padStart(2, "0");

export function toISODate(d: Date): string {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/** "YYYY-MM-DD" -> Date a medianoche local (new Date("YYYY-MM-DD") seria UTC). */
export function parseISODate(s: string): Date {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, m - 1, d);
}

export function toLocalDateTime(d: Date): string {
  return `${toISODate(d)}T${pad(d.getHours())}:${pad(d.getMinutes())}:00`;
}

/** Instante a partir de una fecha-hora local sin zona o de un ISO con zona. */
export function parseDateTime(s: string): Date {
  return new Date(s);
}

export function addDays(d: Date, days: number): Date {
  const copy = new Date(d);
  copy.setDate(copy.getDate() + days);
  return copy;
}

export function addMinutes(d: Date, minutes: number): Date {
  return new Date(d.getTime() + minutes * 60_000);
}

/** Lunes de la semana de `d`, a medianoche. */
export function startOfWeek(d: Date): Date {
  const day = (d.getDay() + 6) % 7; // lunes = 0
  const monday = addDays(d, -day);
  monday.setHours(0, 0, 0, 0);
  return monday;
}

export function isSameDay(a: Date, b: Date): boolean {
  return toISODate(a) === toISODate(b);
}

export function minutesSinceMidnight(d: Date): number {
  return d.getHours() * 60 + d.getMinutes();
}

const timeFormat = new Intl.DateTimeFormat("es-ES", { hour: "2-digit", minute: "2-digit" });
const weekdayFormat = new Intl.DateTimeFormat("es-ES", { weekday: "short" });
const longDayFormat = new Intl.DateTimeFormat("es-ES", { weekday: "long", day: "numeric", month: "long" });
const dayMonthFormat = new Intl.DateTimeFormat("es-ES", { day: "numeric", month: "short" });

export const formatTime = (d: Date) => timeFormat.format(d);
export const formatWeekday = (d: Date) => weekdayFormat.format(d).replace(".", "");
export const formatLongDay = (d: Date) => longDayFormat.format(d);
export const formatDayMonth = (d: Date) => dayMonthFormat.format(d).replace(".", "");

/** "1 h", "1 h 30 min", "45 min". */
export function formatDuration(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h === 0) return `${m} min`;
  return m === 0 ? `${h} h` : `${h} h ${m} min`;
}
