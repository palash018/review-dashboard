import type { Kpis } from '../types'
import { fmtDate } from '../lib/format'

function DeltaBadge({ delta, higherIsBetter = true, suffix = '' }:
  { delta: number | null; higherIsBetter?: boolean; suffix?: string }) {
  if (delta === null || delta === undefined) {
    return <span className="text-xs text-slate-400">no data for comparison</span>
  }
  if (delta === 0) {
    return <span className="text-xs font-medium text-slate-500">no change vs previous period</span>
  }
  const up = delta > 0
  const good = higherIsBetter ? up : !up
  return (
    <span className={`text-xs font-semibold ${good ? 'text-emerald-600' : 'text-rose-600'}`}>
      {up ? '▲' : '▼'} {up ? '+' : ''}{delta}{suffix} vs previous period
    </span>
  )
}

function KpiCard({ label, value, sub, delta, higherIsBetter, suffix }:
  {
    label: string
    value: string
    sub?: string
    delta: number | null
    higherIsBetter?: boolean
    suffix?: string
  }) {
  return (
    <div className="card p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</p>
      <p className="mt-1 text-3xl font-bold text-slate-900">{value}</p>
      <div className="mt-1.5"><DeltaBadge delta={delta} higherIsBetter={higherIsBetter} suffix={suffix} /></div>
      {sub && <p className="mt-1 text-xs text-slate-400">{sub}</p>}
    </div>
  )
}

export default function KpiCards({ kpis }: { kpis: Kpis }) {
  const c = kpis.current
  const p = kpis.period
  const rangeText = `${fmtDate(p.start)} – ${fmtDate(p.end)}`
  const periodLabel = p.days === 7 ? `Week of ${rangeText}` : rangeText
  const prevText = kpis.previous.has_data
    ? `Previous period: ${kpis.previous.reviews}`
    : 'No earlier data to compare'
  return (
    <div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          label="Average score"
          value={c.avg_rating !== null ? `${c.avg_rating.toFixed(1)} / 10` : '—'}
          delta={kpis.delta.avg_rating}
          sub={periodLabel}
        />
        <KpiCard
          label="Reviews received"
          value={String(c.reviews)}
          delta={kpis.delta.reviews}
          sub={prevText}
        />
        <KpiCard
          label="Negative share"
          value={c.pct_negative !== null ? `${c.pct_negative}%` : '—'}
          delta={kpis.delta.pct_negative}
          higherIsBetter={false}
          suffix="pp"
          sub={`${c.sentiment.negative} of ${c.reviews} reviews rated negatively`}
        />
        <div className="card p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
            Guest sentiment mix
          </p>
          {c.reviews > 0 ? (
            <div className="mt-2">
              <div className="flex h-3 overflow-hidden rounded-full">
                <div className="bg-emerald-500" title={`Positive: ${c.sentiment.positive}`}
                  style={{ width: `${(100 * c.sentiment.positive) / c.reviews}%` }} />
                <div className="bg-slate-300" title={`Neutral: ${c.sentiment.neutral}`}
                  style={{ width: `${(100 * c.sentiment.neutral) / c.reviews}%` }} />
                <div className="bg-rose-500" title={`Negative: ${c.sentiment.negative}`}
                  style={{ width: `${(100 * c.sentiment.negative) / c.reviews}%` }} />
              </div>
              <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
                <span><span className="mr-1 inline-block h-2 w-2 rounded-full bg-emerald-500" />Positive {c.sentiment.positive}</span>
                <span><span className="mr-1 inline-block h-2 w-2 rounded-full bg-slate-300" />Neutral {c.sentiment.neutral}</span>
                <span><span className="mr-1 inline-block h-2 w-2 rounded-full bg-rose-500" />Negative {c.sentiment.negative}</span>
              </div>
            </div>
          ) : (
            <p className="mt-3 text-sm text-slate-400">No reviews in this period.</p>
          )}
        </div>
      </div>
    </div>
  )
}
