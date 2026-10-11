/** Timezone helpers: selectable display zone + TZ-aware "today" anchor. */

export const TIMEZONES = [
  { key: 'Australia/Sydney', label: 'Sydney (AEST/AEDT)' },
  { key: 'Asia/Kolkata', label: 'India (IST)' },
  { key: 'UTC', label: 'UTC' },
] as const

export type TzKey = (typeof TIMEZONES)[number]['key']

export const DEFAULT_TZ: string = 'Australia/Sydney'

/** Current calendar date (yyyy-mm-dd) in the given timezone. */
export function todayInTz(tz: string): string {
  // en-CA yields ISO-style YYYY-MM-DD
  return new Intl.DateTimeFormat('en-CA', { timeZone: tz }).format(new Date())
}

/** Format a UTC instant (e.g. 2026-10-11T16:33:37Z) in the given timezone. */
export function formatInstant(iso: string | null | undefined, tz: string): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return new Intl.DateTimeFormat('en-AU', {
    timeZone: tz,
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hourCycle: 'h23',
    timeZoneName: 'short',
  }).format(d)
}

export function tzLabel(key: string): string {
  return TIMEZONES.find((t) => t.key === key)?.label ?? key
}
