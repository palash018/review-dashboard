export type Sentiment = 'positive' | 'neutral' | 'negative'

export interface TopicTag {
  topic: string
  polarity: Sentiment | 'mixed'
  keywords: string[]
}

export interface Review {
  id: string
  property_slug: string
  reviewer_name: string | null
  reviewer_country: string | null
  rating: number | null
  title: string | null
  positive_text: string | null
  negative_text: string | null
  review_date: string | null
  stay_period: string | null
  nights: number | null
  room_type: string | null
  traveler_type: string | null
  hotel_response: string | null
  sentiment: Sentiment | null
  classified_by: string | null
  topics: TopicTag[]
}

export interface PropertyInfo {
  slug: string
  name: string
}

export interface KpiPeriod {
  avg_rating: number | null
  reviews: number
  sentiment: { positive: number; neutral: number; negative: number; total: number }
  pct_negative: number | null
}

export interface Kpis {
  period: { start: string; end: string; days: number }
  prev_period: { start: string; end: string }
  current: KpiPeriod
  previous: KpiPeriod & { has_data: boolean }
  delta: { avg_rating: number | null; reviews: number | null; pct_negative: number | null }
}

export interface PropertyBreakdownRow {
  slug: string
  name: string
  current: { avg_rating: number | null; reviews: number; negative: number; positive: number }
  previous: { avg_rating: number | null; reviews: number; negative: number; positive: number }
  delta_avg_rating: number | null
  top_issue_topic: { topic: string; mentions: number } | null
}

export interface TrendWeek {
  week_start: string
  avg_rating: number
  reviews: number
  positive: number
  neutral: number
  negative: number
  by_property: Record<string, { avg_rating: number; reviews: number }>
}

export interface InsightTopic {
  topic: string
  complaint_mentions: number
  pct_of_complaints: number | null
  prev_pct_of_complaints: number | null
  delta_pp: number | null
}

export interface Insights {
  range: { start: string; end: string }
  complaint_reviews: number
  prev_complaint_reviews: number
  topics: InsightTopic[]
}

export interface ReviewPage {
  total: number
  page: number
  size: number
  pages: number
  reviews: Review[]
}

export interface Meta {
  total_reviews: number
  date_range: { start: string | null; end: string | null }
  last_scrape_run: {
    mode: string; status: string; started_at: string | null
    finished_at: string | null; reviews_new: number
  } | null
  per_property: { slug: string; name: string; reviews: number; avg_rating: number | null }[]
  classification?: Record<string, number>
  properties: PropertyInfo[]
}
