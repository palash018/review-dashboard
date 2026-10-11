import type { Sentiment } from '../types'

export const TOPIC_LABELS: Record<string, string> = {
  cleanliness: 'Cleanliness',
  'check-in': 'Check-in',
  staff: 'Staff & reception',
  noise: 'Noise',
  facilities: 'Facilities',
  location: 'Location',
  'room-condition': 'Room condition',
  value: 'Value for money',
}

export const TOPIC_COLORS: Record<string, string> = {
  cleanliness: 'bg-rose-100 text-rose-800',
  'check-in': 'bg-sky-100 text-sky-800',
  staff: 'bg-violet-100 text-violet-800',
  noise: 'bg-amber-100 text-amber-800',
  facilities: 'bg-teal-100 text-teal-800',
  location: 'bg-emerald-100 text-emerald-800',
  'room-condition': 'bg-indigo-100 text-indigo-800',
  value: 'bg-fuchsia-100 text-fuchsia-800',
}

export const topicLabel = (t: string) => TOPIC_LABELS[t] ?? t

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const [y, m, d] = iso.split('-').map(Number)
  if (!y || !m || !d) return iso
  return `${d} ${MONTHS[m - 1]} ${y}`
}

export function fmtDateShort(iso: string | null | undefined): string {
  if (!iso) return ''
  const [, m, d] = iso.split('-').map(Number)
  return `${d} ${MONTHS[(m ?? 1) - 1]}`
}

export function fmtStayPeriod(ym: string | null): string {
  if (!ym) return ''
  const [y, m] = ym.split('-').map(Number)
  return `${MONTHS[m - 1]} ${y}`
}

export const SENTIMENT_STYLES: Record<string, string> = {
  positive: 'bg-emerald-100 text-emerald-800',
  neutral: 'bg-slate-100 text-slate-700',
  negative: 'bg-rose-100 text-rose-800',
}

export const SENTIMENT_ICONS: Record<string, string> = {
  positive: '▲', neutral: '■', negative: '▼',
}

export function ratingColor(rating: number | null): string {
  if (rating === null) return 'text-slate-400'
  if (rating >= 8.5) return 'text-emerald-600'
  if (rating >= 7) return 'text-emerald-500'
  if (rating >= 5) return 'text-amber-600'
  return 'text-rose-600'
}

export function deltaText(delta: number | null | undefined,
  opts: { higherIsBetter?: boolean } = {}): { label: string; cls: string } {
  if (delta === null || delta === undefined) return { label: 'no data', cls: 'text-slate-400' }
  const higherIsBetter = opts.higherIsBetter ?? true
  if (delta === 0) return { label: 'no change', cls: 'text-slate-500' }
  const up = delta > 0
  const good = higherIsBetter ? up : !up
  return {
    label: `${up ? '+' : ''}${delta}`,
    cls: good ? 'text-emerald-600' : 'text-rose-600',
  }
}

export function sentimentOf(s: Sentiment | null | undefined): string {
  if (s === 'positive') return 'Positive'
  if (s === 'negative') return 'Negative'
  return 'Neutral'
}
