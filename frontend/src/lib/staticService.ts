/**
 * Client-side aggregation engine for the STATIC demo (GitHub Pages).
 *
 * Ports backend/azzurro/api/service.py semantics onto the baked dataset
 * (frontend/src/data/reviews.json, produced from data/reviews_export.json).
 * Read-only: live updates only exist in the local FastAPI app.
 */
import type {
  Insights, Kpis, Meta, PropertyInfo, PropertyBreakdownRow, Review,
  ReviewPage, TopicTag, TrendWeek,
} from '../types'
import { TOPIC_LABELS } from './format'

interface ExportedReview extends Omit<Review, 'topics'> {
  topics: TopicTag[]
  first_seen_at?: string | null
  collected_at?: string | null
}

// Populated by loadDemoData(); empty until then.
let REVIEWS: ExportedReview[] = []

export function loadDemoData(data: unknown): void {
  REVIEWS = data as ExportedReview[]
}

export const hasDemoData = () => REVIEWS.length > 0

const PROPS: PropertyInfo[] = [
  { slug: 'olympic-paddington', name: 'Olympic Hotel Paddington' },
  { slug: 'potts-point', name: 'Potts Point' },
  { slug: 'central-sydney', name: 'Central Sydney' },
  { slug: 'darling-harbour', name: 'Darling Harbour' },
]

// ---- date helpers (UTC-day arithmetic, mirrors ranges.ts / service.py) ----

const toOrd = (iso: string) => Date.parse(`${iso}T12:00:00Z`)
const fromOrd = (ms: number) => new Date(ms).toISOString().slice(0, 10)
const addDays = (iso: string, n: number) => fromOrd(toOrd(iso) + n * 86_400_000)
/** Monday of the week containing iso (weekday: Mon=0..Sun=6 in this helper). */
const mondayOf = (iso: string) => {
  const d = new Date(toOrd(iso))
  const weekday = (d.getUTCDay() + 6) % 7
  return addDays(iso, -weekday)
}
const daysBetween = (a: string, b: string) =>
  Math.round((toOrd(b) - toOrd(a)) / 86_400_000)

// ---- filters -------------------------------------------------------------

function select(property?: string, start?: string, end?: string) {
  return REVIEWS.filter((r) =>
    (!property || r.property_slug === property)
    && (!start || (r.review_date ?? '') >= start)
    && (!end || (r.review_date ?? '') <= end))
}

const round2 = (n: number) => Math.round(n * 100) / 100
const round1 = (n: number) => Math.round(n * 10) / 10

const avgRating = (rows: ExportedReview[]) =>
  rows.length ? round2(rows.reduce((s, r) => s + (r.rating ?? 0), 0) / rows.length) : null

// ---- meta ------------------------------------------------------------------

export function staticMeta(): Meta {
  const dates = REVIEWS.map((r) => r.review_date ?? '').filter(Boolean).sort()
  const lastCollected = REVIEWS.map((r) => r.collected_at ?? '').sort().pop() ?? null
  const classification: Record<string, number> = {}
  for (const r of REVIEWS) {
    const k = r.classified_by ?? 'unclassified'
    classification[k] = (classification[k] ?? 0) + 1
  }
  const byProp = new Map<string, ExportedReview[]>()
  for (const r of REVIEWS) {
    byProp.set(r.property_slug, [...(byProp.get(r.property_slug) ?? []), r])
  }
  return {
    total_reviews: REVIEWS.length,
    date_range: { start: dates[0] ?? null, end: dates.at(-1) ?? null },
    last_scrape_run: lastCollected
      ? { mode: 'exported snapshot', status: 'completed',
          started_at: null, finished_at: lastCollected, reviews_new: REVIEWS.length }
      : null,
    per_property: PROPS.map((p) => {
      const rows = byProp.get(p.slug) ?? []
      return { slug: p.slug, name: p.name, reviews: rows.length,
               avg_rating: avgRating(rows) }
    }),
    classification,
    properties: PROPS,
  }
}

// ---- kpis --------------------------------------------------------------------

export function staticKpis(property: string | undefined,
                            start: string, end: string): Kpis {
  const days = daysBetween(start, end) + 1
  const pStart = addDays(start, -days)
  const pEnd = addDays(start, -1)

  const stats = (a: string, b: string) => {
    const rows = select(property, a, b)
    const sentiment = { positive: 0, neutral: 0, negative: 0, total: rows.length }
    for (const r of rows) {
      if (r.sentiment === 'positive') sentiment.positive++
      else if (r.sentiment === 'negative') sentiment.negative++
      else sentiment.neutral++
    }
    return {
      avg_rating: avgRating(rows),
      reviews: rows.length,
      sentiment,
      pct_negative: rows.length ? round1(100 * sentiment.negative / rows.length) : null,
    }
  }

  const current = stats(start, end)
  const prevStats = stats(pStart, pEnd)
  const previous = { ...prevStats, has_data: prevStats.reviews > 0 }

  const delta = previous.has_data
    ? {
        avg_rating: current.avg_rating === null || previous.avg_rating === null
          ? null : round2(current.avg_rating - previous.avg_rating),
        reviews: current.reviews - previous.reviews,
        pct_negative: current.pct_negative === null || previous.pct_negative === null
          ? null : round1(current.pct_negative - previous.pct_negative),
      }
    : { avg_rating: null, reviews: null, pct_negative: null }

  return {
    period: { start, end, days },
    prev_period: { start: pStart, end: pEnd },
    current,
    previous,
    delta,
  }
}

// ---- property breakdown --------------------------------------------------------

function topNegativeTopic(rows: ExportedReview[]): { topic: string; mentions: number } | null {
  const counts: Record<string, number> = {}
  for (const r of rows) {
    for (const t of r.topics ?? []) {
      if (t.polarity === 'negative' || t.polarity === 'mixed') {
        counts[t.topic] = (counts[t.topic] ?? 0) + 1
      }
    }
  }
  const best = Object.entries(counts).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))[0]
  return best ? { topic: best[0], mentions: best[1] } : null
}

export function staticBreakdown(property: string | undefined,
                                start: string, end: string): PropertyBreakdownRow[] {
  const days = daysBetween(start, end) + 1
  const pStart = addDays(start, -days)
  const pEnd = addDays(start, -1)
  return PROPS
    .filter((p) => !property || p.slug === property)
    .map((p) => {
      const cur = select(p.slug, start, end)
      const prev = select(p.slug, pStart, pEnd)
      const curAvg = avgRating(cur)
      const prevAvg = avgRating(prev)
      return {
        slug: p.slug,
        name: p.name,
        current: {
          avg_rating: curAvg, reviews: cur.length,
          negative: cur.filter((r) => r.sentiment === 'negative').length,
          positive: cur.filter((r) => r.sentiment === 'positive').length,
        },
        previous: {
          avg_rating: prevAvg, reviews: prev.length,
          negative: prev.filter((r) => r.sentiment === 'negative').length,
          positive: prev.filter((r) => r.sentiment === 'positive').length,
        },
        delta_avg_rating: curAvg === null || prevAvg === null ? null : round2(curAvg - prevAvg),
        top_issue_topic: topNegativeTopic(cur),
      }
    })
}

// ---- trends -----------------------------------------------------------------

export function staticTrends(property: string | undefined,
                              start: string, end: string): TrendWeek[] {
  const weeks = new Map<string, {
    propAvgs: number[]; reviews: number; positive: number; neutral: number
    negative: number; byProperty: Record<string, { avg_rating: number; reviews: number }>
  }>()
  for (const r of select(property, start, end)) {
    if (!r.review_date) continue
    const week = mondayOf(r.review_date)
    const w = weeks.get(week) ?? {
      propAvgs: [], reviews: 0, positive: 0, neutral: 0, negative: 0, byProperty: {},
    }
    w.reviews++
    if (r.sentiment === 'positive') w.positive++
    else if (r.sentiment === 'negative') w.negative++
    else w.neutral++
    weeks.set(week, w)
  }
  // second pass for per-property averages per week (mirrors service.py GROUP BY)
  for (const [week, w] of weeks) {
    const weekEnd = addDays(week, 6)
    for (const p of PROPS) {
      if (property && p.slug !== property) continue
      const rows = select(p.slug, week, weekEnd)
      if (!rows.length) continue
      const avg = avgRating(rows)
      if (avg !== null) w.propAvgs.push(avg)
      w.byProperty[p.slug] = { avg_rating: avg ?? 0, reviews: rows.length }
    }
  }
  return [...weeks.entries()]
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([week, w]) => ({
      week_start: week,
      avg_rating: round2(w.propAvgs.reduce((s, n) => s + n, 0) / Math.max(w.propAvgs.length, 1)),
      reviews: w.reviews,
      positive: w.positive,
      neutral: w.neutral,
      negative: w.negative,
      by_property: w.byProperty,
    }))
}

// ---- insights ------------------------------------------------------------------

const isComplaint = (r: ExportedReview) =>
  r.sentiment === 'negative'
  || (r.topics ?? []).some((t) => t.polarity === 'negative' || t.polarity === 'mixed')

function complaintTopicCounts(rows: ExportedReview[]) {
  const counts: Record<string, number> = {}
  let total = 0
  for (const r of rows) {
    if (!isComplaint(r)) continue
    total++
    const seen = new Set<string>()
    for (const t of r.topics ?? []) {
      if ((t.polarity === 'negative' || t.polarity === 'mixed') && !seen.has(t.topic)) {
        seen.add(t.topic)
        counts[t.topic] = (counts[t.topic] ?? 0) + 1
      }
    }
  }
  return { counts, total }
}

export function staticInsights(property: string | undefined,
                               start: string, end: string): Insights {
  const days = daysBetween(start, end) + 1
  const pStart = addDays(start, -days)
  const pEnd = addDays(start, -1)
  const cur = complaintTopicCounts(select(property, start, end))
  const prev = complaintTopicCounts(select(property, pStart, pEnd))

  const topics = [...new Set([...Object.keys(cur.counts), ...Object.keys(prev.counts)])]
    .map((topic) => {
      const n = cur.counts[topic] ?? 0
      const pct = cur.total ? round1(100 * n / cur.total) : null
      const prevPct = prev.total ? round1(100 * (prev.counts[topic] ?? 0) / prev.total) : null
      return {
        topic,
        complaint_mentions: n,
        pct_of_complaints: pct,
        prev_pct_of_complaints: prevPct,
        delta_pp: pct === null || prevPct === null ? null : round1(pct - prevPct),
      }
    })
    .sort((a, b) => b.complaint_mentions - a.complaint_mentions
      || a.topic.localeCompare(b.topic))
  return { range: { start, end }, complaint_reviews: cur.total,
           prev_complaint_reviews: prev.total, topics }
}

// ---- review feed ------------------------------------------------------------------

export function staticReviews(p: {
  property?: string; start?: string; end?: string; topic?: string
  sentiment?: string; search?: string; sort?: string; page?: number; size?: number
}): ReviewPage {
  let rows = select(p.property, p.start, p.end)
  if (p.sentiment) rows = rows.filter((r) => r.sentiment === p.sentiment)
  if (p.topic) {
    rows = rows.filter((r) => (r.topics ?? []).some((t) => t.topic === p.topic))
  }
  if (p.search) {
    const q = p.search.toLowerCase()
    rows = rows.filter((r) =>
      (r.title ?? '').toLowerCase().includes(q)
      || (r.positive_text ?? '').toLowerCase().includes(q)
      || (r.negative_text ?? '').toLowerCase().includes(q))
  }
  const byDate = (a: ExportedReview, b: ExportedReview) =>
    (b.review_date ?? '').localeCompare(a.review_date ?? '') || b.id.localeCompare(a.id)
  const sorted = [...rows].sort((a, b) => {
    switch (p.sort) {
      case 'oldest': return -byDate(a, b)
      case 'worst': return (a.rating ?? 99) - (b.rating ?? 99) || byDate(a, b)
      case 'best': return (b.rating ?? -1) - (a.rating ?? -1) || byDate(a, b)
      default: return byDate(a, b)
    }
  })
  const size = Math.max(1, Math.min(p.size ?? 20, 100))
  const page = Math.max(1, p.page ?? 1)
  const window = sorted.slice((page - 1) * size, page * size)
  return {
    total: sorted.length, page, size,
    pages: Math.max(1, Math.ceil(sorted.length / size)),
    reviews: window as Review[],
  }
}

export const STATIC_TOPIC_KEYS = Object.keys(TOPIC_LABELS)
