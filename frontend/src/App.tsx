import { useCallback, useEffect, useMemo, useState } from 'react'
import { api, isStaticDemo } from './api'
import { buildRange, CUSTOM_KEY, shiftISO } from './lib/ranges'
import { fmtDate } from './lib/format'
import Header from './components/Header'
import KpiCards from './components/KpiCards'
import InsightsPanel from './components/InsightsPanel'
import TrendCharts from './components/TrendCharts'
import PropertyCards from './components/PropertyCards'
import ReviewFeed from './components/ReviewFeed'
import { ErrorState, Spinner } from './components/common'
import { DEFAULT_TZ, todayInTz } from './lib/time'

function useApi<T>(fetcher: () => Promise<T>, deps: unknown[]) {
  const [state, setState] = useState<{ data: T | null; loading: boolean; error: string | null; nonce: number }>(
    { data: null, loading: true, error: null, nonce: 0 })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const memoFetcher = useCallback(fetcher, deps)
  useEffect(() => {
    let cancelled = false
    setState((s) => ({ ...s, loading: true, error: null }))
    memoFetcher()
      .then((data) => { if (!cancelled) setState({ data, loading: false, error: null, nonce: 0 }) })
      .catch((e) => { if (!cancelled) setState((s) => ({ ...s, loading: false, error: String(e), nonce: s.nonce })) })
    return () => { cancelled = true }
  }, [memoFetcher, state.nonce])
  const retry = useCallback(() => setState((s) => ({ ...s, nonce: s.nonce + 1 })), [])
  return { ...state, retry }
}

export const REPO_URL = 'https://github.com/palash018/review-dashboard'

export default function App() {
  const [property, setProperty] = useState('')
  const [staticDemo, setStaticDemo] = useState(false)
  const [tz, setTz] = useState(() => localStorage.getItem('tz') ?? DEFAULT_TZ)
  const [preset, setPreset] = useState('thisWeek')
  const [custom, setCustom] = useState(() => {
    const today = new Date()
    const start = new Date(today)
    start.setDate(today.getDate() - 27)
    return { start: start.toISOString().slice(0, 10), end: today.toISOString().slice(0, 10) }
  })

  const metaQ = useApi(() => api.meta(), [])
  const meta = metaQ.data

  useEffect(() => {
    isStaticDemo().then(setStaticDemo)
  }, [])

  const [ignoreWeekFallback, setIgnoreWeekFallback] = useState(false)

  // Persist the display timezone; "today" is computed in that timezone so
  // week boundaries follow the selected zone, not the browser's clock.
  const resetWeekFallback = useCallback(() => setIgnoreWeekFallback(false), [])
  const handleTz = useCallback((next: string) => {
    localStorage.setItem('tz', next)
    setTz(next)
    resetWeekFallback()
  }, [resetWeekFallback])
  const handlePreset = useCallback((key: string) => {
    setPreset(key)
    resetWeekFallback()
  }, [resetWeekFallback])

  const todayISO = useMemo(() => todayInTz(tz), [tz])

  const { range: rawRange } = useMemo(
    () => buildRange(preset, todayISO, meta?.date_range.start ?? null, custom),
    [preset, custom, todayISO, meta?.date_range.start],
  )

  // Early in a new week the current week may have no reviews yet (e.g. Monday
  // 00:05). Rather than an empty dashboard, fall back to the previous week
  // with a clear notice — unless the user opts to see the empty week.
  const lastDataDate = meta?.date_range.end ?? null
  const weekFallbackActive =
    preset === 'thisWeek' && !ignoreWeekFallback
    && lastDataDate !== null && rawRange.start > lastDataDate

  const range = useMemo(
    () => (weekFallbackActive
      ? { start: shiftISO(rawRange.start, -7), end: shiftISO(rawRange.end, -7) }
      : rawRange),
    [weekFallbackActive, rawRange],
  )

  const rangeLabel = `${fmtDate(range.start)} – ${fmtDate(range.end)}`

  const kpisQ = useApi(
    () => api.kpis({ property: property || undefined, start: range.start, end: range.end }),
    [property, range.start, range.end],
  )
  const breakdownQ = useApi(
    () => api.breakdown({ property: property || undefined, start: range.start, end: range.end }),
    [property, range.start, range.end],
  )
  const trendsQ = useApi(
    () => api.trends({ property: property || undefined, start: range.start, end: range.end }),
    [property, range.start, range.end],
  )
  const insightsQ = useApi(
    () => api.insights({ property: property || undefined, start: range.start, end: range.end }),
    [property, range.start, range.end],
  )

  const refreshAll = useCallback(() => {
    metaQ.retry()
    kpisQ.retry()
    breakdownQ.retry()
    trendsQ.retry()
    insightsQ.retry()
  }, [metaQ, kpisQ, breakdownQ, trendsQ, insightsQ])

  const feedFilters = useMemo(
    () => ({ property, start: range.start, end: range.end }),
    [property, range.start, range.end],
  )

  // Cross-filtering: clicking a topic anywhere (insights, property top-issue)
  // filters the review feed to that topic and scrolls to it.
  const [feedTopic, setFeedTopic] = useState('')
  const scrollToFeed = useCallback(() => {
    document.getElementById('review-feed')
      ?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [])
  const handleSelectTopic = useCallback((slug: string | undefined, topic: string) => {
    if (slug) setProperty(slug)
    setFeedTopic(topic)
    scrollToFeed()
  }, [scrollToFeed])

  return (
    <div className="min-h-screen bg-slate-100 pb-16 font-sans text-slate-900">
      <Header
        meta={meta}
        preset={preset}
        onPreset={handlePreset}
        custom={custom}
        onCustom={(c) => { setCustom(c); setPreset(CUSTOM_KEY) }}
        property={property}
        onProperty={setProperty}
        onRefresh={refreshAll}
        tz={tz}
        onTz={handleTz}
      />

      <main className="mx-auto max-w-7xl space-y-6 px-4 py-5 sm:px-6 sm:py-6">
        {staticDemo && (
          <div className="card flex flex-wrap items-center justify-between gap-3 border-sky-200 bg-sky-50 p-4 text-sm text-sky-900">
            <p>
              🌐 <span className="font-semibold">Online demo</span> — a read-only
              snapshot of the review data
              {meta?.date_range.end && <> (collected up to {fmtDate(meta.date_range.end)})</>}.
              Everything is fully interactive; run the app locally for live collection.
            </p>
            <a href={REPO_URL} target="_blank" rel="noreferrer"
              className="rounded-lg border border-sky-300 bg-white px-3 py-2.5 text-xs font-semibold text-sky-800 hover:bg-sky-100">
              Source code ↗
            </a>
          </div>
        )}
        {weekFallbackActive && (
          <div className="card flex flex-wrap items-center justify-between gap-3 border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
            <p>
              The current week ({fmtDate(rawRange.start)} – {fmtDate(rawRange.end)}) has no
              guest reviews yet — showing the previous week instead.
            </p>
            <button
              onClick={() => setIgnoreWeekFallback(true)}
              className="rounded-lg border border-amber-300 bg-white px-3 py-2.5 text-xs font-semibold text-amber-800 hover:bg-amber-100">
              Show current week anyway
            </button>
          </div>
        )}
        {kpisQ.loading ? (
          <Spinner label="Loading the numbers…" />
        ) : kpisQ.error ? (
          <ErrorState message={kpisQ.error} onRetry={kpisQ.retry} />
        ) : kpisQ.data ? (
          <KpiCards kpis={kpisQ.data} />
        ) : null}

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
          {insightsQ.data ? (
            <InsightsPanel
              insights={insightsQ.data}
              classification={meta?.classification}
              onSelectTopic={(topic) => handleSelectTopic(undefined, topic)} />
          ) : (
            insightsQ.loading ? <Spinner /> : <ErrorState message={insightsQ.error ?? ''} onRetry={insightsQ.retry} />
          )}
          {breakdownQ.data ? (
            <PropertyCards
              rows={breakdownQ.data}
              rangeLabel={rangeLabel}
              onSelectTopic={(slug, topic) => handleSelectTopic(slug, topic)} />
          ) : (
            breakdownQ.loading ? <Spinner /> : <ErrorState message={breakdownQ.error ?? ''} onRetry={breakdownQ.retry} />
          )}
        </div>

        {trendsQ.loading ? <Spinner /> : trendsQ.error ? (
          <ErrorState message={trendsQ.error} onRetry={trendsQ.retry} />
        ) : (
          <TrendCharts trends={trendsQ.data ?? []} />
        )}

        <div id="review-feed">
          <ReviewFeed filters={feedFilters} meta={meta} topic={feedTopic} onTopic={setFeedTopic} />
        </div>

        <footer className="pt-4 text-center text-xs text-slate-400">
          Reviews are collected from public Booking.com property pages.
          {' '}Ratings use Booking.com's 1–10 scale. Sentiment: 8+ positive, 6 or less negative.
        </footer>
      </main>
    </div>
  )
}
