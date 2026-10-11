import { useEffect, useState } from 'react'
import { api } from '../api'
import type { Meta, Review } from '../types'
import {
  fmtDate, fmtStayPeriod, ratingColor, SENTIMENT_ICONS, SENTIMENT_STYLES,
  sentimentOf, TOPIC_COLORS, TOPIC_LABELS, topicLabel,
} from '../lib/format'
import { EmptyState, ErrorState, SectionCard, Spinner } from './common'

interface FeedFilters {
  property: string
  start: string
  end: string
}

const SORTS = [
  { key: 'newest', label: 'Newest first' },
  { key: 'oldest', label: 'Oldest first' },
  { key: 'worst', label: 'Lowest rated' },
  { key: 'best', label: 'Highest rated' },
]

const PAGE_SIZE = 10

function ReviewCard({ review, propertyName }: { review: Review; propertyName: string }) {
  return (
    <article className="card p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="chip bg-indigo-100 text-indigo-800">{propertyName}</span>
        <span className={`chip ${SENTIMENT_STYLES[review.sentiment ?? 'neutral']}`}>
          {SENTIMENT_ICONS[review.sentiment ?? 'neutral']} {sentimentOf(review.sentiment)}
        </span>
        <span className={`text-sm font-bold ${ratingColor(review.rating)}`}>
          {review.rating !== null ? `${review.rating.toFixed(1)}/10` : '—'}
        </span>
        <span className="ml-auto text-xs text-slate-400">
          {fmtDate(review.review_date)}
        </span>
      </div>

      {review.title && (
        <h3 className="mt-2 font-semibold text-slate-800">{review.title}</h3>
      )}

      <div className="mt-2 space-y-2 text-sm">
        {review.positive_text && (
          <p className="flex gap-2">
            <span className="shrink-0 font-medium text-emerald-600">Liked</span>
            <span className="whitespace-pre-line text-slate-600">{review.positive_text}</span>
          </p>
        )}
        {review.negative_text && (
          <p className="flex gap-2">
            <span className="shrink-0 font-medium text-rose-600">Disliked</span>
            <span className="whitespace-pre-line text-slate-600">{review.negative_text}</span>
          </p>
        )}
        {!review.positive_text && !review.negative_text && (
          <p className="text-slate-400 italic">No written comments (rating only)</p>
        )}
      </div>

      {review.topics.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {review.topics.map((t) => (
            <span key={t.topic}
              title={`Tagged because the review mentions: ${t.keywords.join(', ')}`}
              className={`chip ${TOPIC_COLORS[t.topic] ?? 'bg-slate-100 text-slate-700'}`}>
              {topicLabel(t.topic)}
              {t.polarity === 'negative' ? ' −' : t.polarity === 'positive' ? ' +' : ' ±'}
            </span>
          ))}
        </div>
      )}

      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 border-t border-slate-100 pt-2 text-xs text-slate-400">
        {review.reviewer_name && <span>{review.reviewer_name}</span>}
        {review.reviewer_country && <span>{review.reviewer_country}</span>}
        {review.traveler_type && <span>{review.traveler_type}</span>}
        {review.nights !== null && <span>{review.nights} night{review.nights === 1 ? '' : 's'}</span>}
        {review.room_type && <span>{review.room_type}</span>}
        {review.stay_period && <span>Stayed {fmtStayPeriod(review.stay_period)}</span>}
      </div>

      {review.hotel_response && (
        <div className="mt-3 rounded-lg bg-slate-50 p-3 text-xs text-slate-500">
          <span className="font-semibold text-slate-600">Hotel response: </span>
          {review.hotel_response}
        </div>
      )}
    </article>
  )
}

export default function ReviewFeed({ filters, meta, topic, onTopic }: {
  filters: FeedFilters
  meta: Meta | null
  topic: string
  onTopic: (topic: string) => void
}) {
  const [sentiment, setSentiment] = useState('')
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState('newest')
  const [page, setPage] = useState(1)
  const [data, setData] = useState<{ loading: boolean; error: string | null;
    total: number; pages: number; page: number; reviews: Review[] }>({
      loading: true, error: null, total: 0, pages: 1, page: 1, reviews: [],
    })

  const nameOf = (slug: string) =>
    meta?.properties.find((p) => p.slug === slug)?.name ?? slug

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      setData((d) => ({ ...d, loading: true, error: null }))
      try {
        const res = await api.reviews({
          property: filters.property || undefined,
          start: filters.start || undefined,
          end: filters.end || undefined,
          topic: topic || undefined,
          sentiment: sentiment || undefined,
          search: search.trim() || undefined,
          sort, page, size: PAGE_SIZE,
        })
        if (!cancelled) {
          setData({ loading: false, error: null, total: res.total,
            pages: res.pages, page: res.page, reviews: res.reviews })
        }
      } catch (e) {
        if (!cancelled) {
          setData((d) => ({ ...d, loading: false, error: String(e) }))
        }
      }
    }
    load()
    return () => { cancelled = true }
  }, [filters.property, filters.start, filters.end, topic, sentiment, search, sort, page])

  const resetToPage1 = <T,>(setter: (v: T) => void) => (v: T) => {
    setter(v)
    setPage(1)
  }

  const resetTopic = (next: string) => {
    onTopic(next)
    setPage(1)
  }

  return (
    <SectionCard
      title="Review feed"
      subtitle={`${data.total.toLocaleString()} review${data.total === 1 ? '' : 's'} match the filters`}
    >
      <div className="mb-4 grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4">
        <input
          value={search}
          onChange={(e) => resetToPage1(setSearch)(e.target.value)}
          placeholder="Search review text…"
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none"
        />
        <select value={topic} onChange={(e) => resetTopic(e.target.value)}
          className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm">
          <option value="">All topics</option>
          {Object.entries(TOPIC_LABELS).map(([k, label]) => (
            <option key={k} value={k}>{label}</option>
          ))}
        </select>
        <select value={sentiment} onChange={(e) => resetToPage1(setSentiment)(e.target.value)}
          className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm">
          <option value="">All sentiments</option>
          <option value="positive">Positive</option>
          <option value="neutral">Neutral</option>
          <option value="negative">Negative</option>
        </select>
        <select value={sort} onChange={(e) => resetToPage1(setSort)(e.target.value)}
          className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm">
          {SORTS.map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
        </select>
      </div>

      {topic && (
        <p className="-mt-2 mb-3 text-xs text-slate-400">
          Topic tags are phrase-based (e.g. "far from" → Location), so text
          search may not find these reviews by the topic name itself — this
          filter shows every review tagged with {topicLabel(topic)}.
        </p>
      )}

      {data.loading ? (
        <Spinner label="Loading reviews…" />
      ) : data.error ? (
        <ErrorState message={data.error} />
      ) : data.reviews.length === 0 ? (
        <EmptyState
          title="No reviews match these filters"
          hint="Try widening the date range or clearing a filter."
        />
      ) : (
        <div className="space-y-3">
          {data.reviews.map((r) => (
            <ReviewCard key={r.id} review={r} propertyName={nameOf(r.property_slug)} />
          ))}
        </div>
      )}

      {data.pages > 1 && (
        <div className="mt-4 flex items-center justify-center gap-3 text-sm">
          <button
            disabled={data.page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            className="rounded-lg border border-slate-200 px-4 py-2.5 font-medium text-slate-600 disabled:opacity-40 hover:bg-slate-50">
            ← Previous
          </button>
          <span className="text-slate-500">
            Page {data.page} of {data.pages}
          </span>
          <button
            disabled={data.page >= data.pages}
            onClick={() => setPage((p) => Math.min(data.pages, p + 1))}
            className="rounded-lg border border-slate-200 px-4 py-2.5 font-medium text-slate-600 disabled:opacity-40 hover:bg-slate-50">
            Next →
          </button>
        </div>
      )}
    </SectionCard>
  )
}
