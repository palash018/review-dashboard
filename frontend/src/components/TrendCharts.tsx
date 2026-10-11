import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { TrendWeek } from '../types'
import { fmtDateShort } from '../lib/format'
import { EmptyState, SectionCard } from './common'

export default function TrendCharts({ trends }: { trends: TrendWeek[] }) {
  const data = trends.map((w) => ({
    ...w,
    label: fmtDateShort(w.week_start),
  }))

  if (data.length === 0) {
    return (
      <SectionCard title="Rating & review trends" subtitle="per calendar week">
        <EmptyState title="No reviews in this period" />
      </SectionCard>
    )
  }

  return (
    <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
      <SectionCard title="Average rating per week" subtitle="score out of 10">
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 5, right: 10, bottom: 0, left: -20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="label" tick={{ fontSize: 12, fill: '#64748b' }} />
              <YAxis domain={[0, 10]} ticks={[0, 2, 4, 6, 8, 10]}
                tick={{ fontSize: 12, fill: '#64748b' }} />
              <Tooltip formatter={(value) => [value as string | number, 'Avg score']} />
              <Line type="monotone" dataKey="avg_rating" name="Avg score"
                stroke="#4f46e5" strokeWidth={2.5} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </SectionCard>

      <SectionCard title="Positive / neutral / negative reviews" subtitle="per calendar week">
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 5, right: 10, bottom: 0, left: -20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="label" tick={{ fontSize: 12, fill: '#64748b' }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: '#64748b' }} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="positive" name="Positive" stackId="s" fill="#10b981" radius={0} />
              <Bar dataKey="neutral" name="Neutral" stackId="s" fill="#cbd5e1" />
              <Bar dataKey="negative" name="Negative" stackId="s" fill="#f43f5e" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </SectionCard>
    </div>
  )
}
