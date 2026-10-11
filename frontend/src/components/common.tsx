import type { ReactNode } from 'react'

export function Spinner({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-10 text-slate-500">
      <span className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-indigo-600" />
      <span className="text-sm">{label}</span>
    </div>
  )
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="card flex flex-col items-center gap-3 p-8 text-center">
      <span className="text-3xl">⚠️</span>
      <p className="max-w-md text-sm text-slate-600">
        Something went wrong while loading this section.
        <span className="mt-1 block font-mono text-xs text-slate-400">{message}</span>
      </p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="rounded-lg bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-700"
        >
          Try again
        </button>
      )}
    </div>
  )
}

export function EmptyState({ title, hint }: { title: string; hint?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-1 px-6 py-10 text-center">
      <p className="text-sm font-medium text-slate-600">{title}</p>
      {hint && <p className="text-xs text-slate-400">{hint}</p>}
    </div>
  )
}

export function SectionCard({
  title, subtitle, children, className = '',
}: { title: string; subtitle?: string; children: ReactNode; className?: string }) {
  return (
    <section className={`card p-5 ${className}`}>
      <div className="mb-4 flex items-baseline justify-between gap-3">
        <h2 className="text-base font-semibold text-slate-800">{title}</h2>
        {subtitle && <span className="text-xs text-slate-400">{subtitle}</span>}
      </div>
      {children}
    </section>
  )
}
