import type {
  Insights, Kpis, Meta, PropertyBreakdownRow, ReviewPage, TrendWeek,
} from './types'
import reviewsJson from './data/reviews.json'
import {
  loadDemoData, staticBreakdown, staticInsights, staticKpis, staticMeta,
  staticReviews, staticTrends,
} from './lib/staticService'

/**
 * API layer with two modes:
 *  - live:   local deployment (FastAPI on :8000, or `npm run dev` proxy)
 *  - static: GitHub Pages demo — aggregation runs client-side on the baked
 *            dataset (read-only snapshot).
 * The mode is probed once by requesting /api/meta.
 */
let mode: 'live' | 'static' | null = null
let modeProbe: Promise<'live' | 'static'> | null = null

async function probe(): Promise<'live' | 'static'> {
  try {
    const res = await fetch('/api/meta', { signal: AbortSignal.timeout(3000) })
    return res.ok ? 'live' : 'static'
  } catch {
    return 'static'
  }
}

/** Resolve once and share the in-flight probe across concurrent callers. */
function detectMode(): Promise<'live' | 'static'> {
  if (mode) return Promise.resolve(mode)
  modeProbe ??= probe().then((m) => {
    mode = m
    if (m === 'static') loadDemoData(reviewsJson)
    return m
  })
  return modeProbe
}

export async function isStaticDemo(): Promise<boolean> {
  return (await detectMode()) === 'static'
}

async function getJson<T>(url: string, staticFn: () => T): Promise<T> {
  if ((await detectMode()) === 'static') return staticFn()
  const res = await fetch(url)
  if (!res.ok) {
    let detail = res.statusText
    try { detail = (await res.json()).detail ?? detail } catch { /* keep */ }
    throw new Error(`Request failed (${res.status}): ${detail}`)
  }
  return res.json() as Promise<T>
}

const qs = (params: Record<string, string | number | undefined | null>) => {
  const u = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') u.set(k, String(v))
  }
  const s = u.toString()
  return s ? `?${s}` : ''
}

export const api = {
  meta: () => getJson<Meta>('/api/meta', () => staticMeta()),
  kpis: (p: { property?: string; start?: string; end?: string }) =>
    getJson<Kpis>(`/api/kpis${qs(p as Record<string, string>)}`,
      () => staticKpis(p.property, p.start ?? '', p.end ?? '')),
  breakdown: (p: { property?: string; start?: string; end?: string }) =>
    getJson<PropertyBreakdownRow[]>(`/api/properties/breakdown${qs(p as Record<string, string>)}`,
      () => staticBreakdown(p.property, p.start ?? '', p.end ?? '')),
  trends: (p: { property?: string; start?: string; end?: string }) =>
    getJson<TrendWeek[]>(`/api/trends${qs(p as Record<string, string>)}`,
      () => staticTrends(p.property, p.start ?? '', p.end ?? '')),
  insights: (p: { property?: string; start?: string; end?: string }) =>
    getJson<Insights>(`/api/insights${qs(p as Record<string, string>)}`,
      () => staticInsights(p.property, p.start ?? '', p.end ?? '')),
  reviews: (p: {
    property?: string; start?: string; end?: string; topic?: string
    sentiment?: string; search?: string; sort?: string; page?: number; size?: number
  }) => getJson<ReviewPage>(`/api/reviews${qs(p as Record<string, string | number>)}`,
    () => staticReviews(p)),
}
