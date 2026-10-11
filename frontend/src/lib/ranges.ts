export interface DateRange {
  start: string
  end: string
}

export interface RangePreset {
  key: string
  label: string
  build: (today: string, dataStart: string | null) => DateRange
}

// All arithmetic happens on UTC-noon dates so preset ranges depend ONLY on
// the anchor date (already computed in the selected timezone), never on the
// browser's local timezone.
const parseISO = (s: string) => new Date(`${s}T12:00:00Z`)
const iso = (d: Date) => d.toISOString().slice(0, 10)
const addDays = (d: Date, n: number) => {
  const c = new Date(d)
  c.setUTCDate(c.getUTCDate() + n)
  return c
}

/** Monday of d's week (getUTCDay: Sunday=0 .. Saturday=6). */
const mondayOf = (d: Date) => addDays(d, -((d.getUTCDay() + 6) % 7))

/** Shift an ISO date by n days (UTC arithmetic, timezone-independent). */
export const shiftISO = (s: string, n: number) => iso(addDays(parseISO(s), n))

export const PRESETS: RangePreset[] = [
  {
    key: 'thisWeek',
    label: 'This week',
    build: (today) => {
      const monday = mondayOf(parseISO(today))
      return { start: iso(monday), end: iso(addDays(monday, 6)) }
    },
  },
  {
    key: 'lastWeek',
    label: 'Last week',
    build: (today) => {
      const monday = addDays(mondayOf(parseISO(today)), -7)
      return { start: iso(monday), end: iso(addDays(monday, 6)) }
    },
  },
  {
    key: 'last4',
    label: 'Last 4 weeks',
    build: (today) => ({ start: iso(addDays(parseISO(today), -27)), end: today }),
  },
  {
    key: 'last12',
    label: 'Last 12 weeks',
    build: (today) => ({ start: iso(addDays(parseISO(today), -83)), end: today }),
  },
  {
    key: 'all',
    label: 'All time',
    build: (today, dataStart) => ({
      start: dataStart ?? iso(addDays(parseISO(today), -180)),
      end: today,
    }),
  },
]

export const CUSTOM_KEY = 'custom'

export function buildRange(
  presetKey: string,
  today: string,
  dataStart: string | null,
  custom?: DateRange,
): { range: DateRange; preset: string } {
  if (presetKey === CUSTOM_KEY && custom) {
    return { range: custom, preset: CUSTOM_KEY }
  }
  const preset = PRESETS.find((p) => p.key === presetKey) ?? PRESETS[0]
  return { range: preset.build(today, dataStart), preset: preset.key }
}
