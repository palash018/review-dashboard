import type { Insights } from '../types'
import { topicLabel } from '../lib/format'
import { EmptyState } from './common'

export default function InsightsPanel({ insights, classification, onSelectTopic }: {
  insights: Insights
  classification?: Record<string, number>
  onSelectTopic: (topic: string) => void
}) {
  const topics = insights.topics.filter((t) => t.complaint_mentions > 0).slice(0, 4)

  return (
    <section className="card p-5">
      <div className="mb-4 flex items-baseline justify-between">
        <h2 className="text-base font-semibold text-slate-800">What guests complained about</h2>
        <span className="text-xs text-slate-400">
          {insights.complaint_reviews} review{insights.complaint_reviews === 1 ? '' : 's'} with complaints in this period
        </span>
      </div>

      {topics.length === 0 ? (
        <EmptyState
          title="No complaints detected in this period 🎉"
          hint="Reviews with issues in their 'disliked' section will appear here."
        />
      ) : (
        <ul className="space-y-3">
          {topics.map((t) => {
            const pct = t.pct_of_complaints
            const delta = t.delta_pp
            return (
              <li key={t.topic}>
                <button
                  onClick={() => onSelectTopic(t.topic)}
                  title="Show reviews tagged with this topic in the feed below"
                  className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg px-2 py-2.5 text-left text-sm hover:bg-slate-50">
                  <span className="font-medium text-slate-800 underline decoration-slate-300 underline-offset-2">
                    {topicLabel(t.topic)}
                  </span>
                  <span className="text-slate-500">
                    {pct !== null ? `${pct}%` : '—'} of complaint reviews
                    mentioned this ({t.complaint_mentions}) ↗
                  </span>
                  {delta !== null && delta !== 0 && (
                    <span className={`chip ${delta > 0 ? 'bg-rose-100 text-rose-700' : 'bg-emerald-100 text-emerald-700'}`}>
                      {delta > 0 ? 'worsening' : 'improving'} {delta > 0 ? '+' : ''}{delta}pp
                    </span>
                  )}
                </button>
              </li>
            )
          })}
        </ul>
      )}
      {(() => {
        const llm = classification?.llm ?? 0
        const total = llm + (classification?.keyword ?? 0)
        return llm > 0 ? (
          <p className="mt-4 border-t border-slate-100 pt-3 text-xs text-slate-400">
            Topics are AI-assisted ({llm} of {total || '—'} reviews LLM-tagged)
            with keyword fallback; a review can mention several topics.
            Still automated — spot-check anything surprising.
          </p>
        ) : (
          <p className="mt-4 border-t border-slate-100 pt-3 text-xs text-slate-400">
            Topics come from lexical (keyword) analysis of the “disliked” part of
            each review; a review can mention several topics. Lexical analysis is
            fast and transparent but approximate — it can miss unusual phrasing
            or occasionally mis-tag a mention. For higher accuracy, an
            administrator can set <code className="rounded bg-slate-100 px-1">LLM_API_KEY</code> and
            run <code className="rounded bg-slate-100 px-1">azzurro classify --llm</code> (see README).
          </p>
        )
      })()}
    </section>
  )
}
