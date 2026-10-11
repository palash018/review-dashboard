import type { PropertyBreakdownRow } from '../types'
import { topicLabel } from '../lib/format'
import { EmptyState, SectionCard } from './common'

function PropertyRow({ row, onSelectTopic }: {
  row: PropertyBreakdownRow
  onSelectTopic: (slug: string, topic: string) => void
}) {
  const cur = row.current
  const prev = row.previous
  return (
    <div className="flex flex-col gap-3 rounded-lg border border-slate-100 p-4 sm:grid sm:grid-cols-[1.4fr_repeat(3,1fr)] sm:items-center sm:gap-x-4 sm:gap-y-2">
      <div className="flex items-center justify-between gap-3 sm:block">
        <div className="min-w-0">
          <p className="font-semibold text-slate-800">{row.name}</p>
          {row.top_issue_topic ? (
            <button
              onClick={() => onSelectTopic(row.slug, row.top_issue_topic!.topic)}
              title={`Show the ${row.top_issue_topic.mentions} review${row.top_issue_topic.mentions === 1 ? '' : 's'} tagged with this topic`}
              className="mt-1 rounded-md py-2 text-left text-xs text-rose-600 underline decoration-rose-300 underline-offset-2 hover:decoration-rose-600">
              Top issue: {topicLabel(row.top_issue_topic.topic)} ({row.top_issue_topic.mentions}) ↗
            </button>
          ) : (
            <p className="mt-1 text-xs text-slate-400">No issues flagged in this period</p>
          )}
        </div>
      </div>
      <div className="flex items-baseline justify-between gap-3 sm:block">
        <p className={`text-3xl font-bold sm:text-2xl ${cur.avg_rating !== null ? 'text-slate-900' : 'text-slate-300'}`}>
          {cur.avg_rating !== null ? cur.avg_rating.toFixed(1) : '—'}
        </p>
        <p className="text-xs text-slate-400">
          avg score ({cur.reviews} reviews)
        </p>
      </div>
      <div>
        {row.delta_avg_rating === null ? (
          <span className="text-xs text-slate-400">no previous period</span>
        ) : row.delta_avg_rating === 0 ? (
          <span className="text-xs text-slate-500">no change</span>
        ) : (
          <span className={`text-sm font-semibold ${row.delta_avg_rating > 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
            {row.delta_avg_rating > 0 ? '▲' : '▼'} {row.delta_avg_rating > 0 ? '+' : ''}{row.delta_avg_rating}
            <span className="ml-1 text-xs font-normal text-slate-400">
              (prev {prev.avg_rating !== null ? prev.avg_rating.toFixed(1) : '—'})
            </span>
          </span>
        )}
        <p className="text-xs text-slate-400">vs previous period</p>
      </div>
      <div>
        <div className="flex h-2.5 w-full max-w-48 overflow-hidden rounded-full bg-slate-100 sm:max-w-32">
          {cur.reviews > 0 && (
            <>
              <div className="bg-emerald-500"
                style={{ width: `${(100 * cur.positive) / cur.reviews}%` }} />
              <div className="bg-slate-300"
                style={{ width: `${(100 * (cur.reviews - cur.positive - cur.negative)) / cur.reviews}%` }} />
              <div className="bg-rose-500"
                style={{ width: `${(100 * cur.negative) / cur.reviews}%` }} />
            </>
          )}
        </div>
        <p className="mt-1 text-xs text-slate-400">
          {cur.positive} positive · {cur.negative} negative
        </p>
      </div>
    </div>
  )
}

export default function PropertyCards({ rows, rangeLabel, onSelectTopic }:
  { rows: PropertyBreakdownRow[]; rangeLabel: string
    onSelectTopic: (slug: string, topic: string) => void }) {
  return (
    <SectionCard title="Property breakdown" subtitle={rangeLabel}>
      {rows.length === 0 ? (
        <EmptyState title="No properties match the current filters" />
      ) : (
        <div className="space-y-3">
          {rows.map((r) => <PropertyRow key={r.slug} row={r} onSelectTopic={onSelectTopic} />)}
        </div>
      )}
    </SectionCard>
  )
}
