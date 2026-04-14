import React from 'react'

// ─── Card Skeleton ───────────────────────────────────────────
export function CardSkeleton() {
  return (
    <div className="glass rounded-2xl p-5 flex flex-col gap-3 animate-pulse">
      <div className="flex gap-2">
        <div className="skeleton h-5 w-16 rounded-full" />
        <div className="skeleton h-5 w-20 rounded-full" />
      </div>
      <div className="skeleton h-4 w-full rounded-md" />
      <div className="skeleton h-4 w-3/4 rounded-md" />
      <div className="skeleton h-3 w-full rounded-md" />
      <div className="skeleton h-3 w-5/6 rounded-md" />
      <div className="skeleton h-3 w-4/6 rounded-md" />
      <div className="flex gap-1.5 mt-1">
        <div className="skeleton h-4 w-12 rounded-md" />
        <div className="skeleton h-4 w-14 rounded-md" />
        <div className="skeleton h-4 w-10 rounded-md" />
      </div>
    </div>
  )
}

// ─── Top5 Skeleton ───────────────────────────────────────────
export function Top5Skeleton() {
  return (
    <div className="glass rounded-2xl p-6 flex flex-col gap-4 animate-pulse">
      <div className="flex items-center gap-3">
        <div className="skeleton w-10 h-10 rounded-xl" />
        <div className="skeleton h-4 w-24 rounded-md" />
      </div>
      <div className="skeleton h-5 w-full rounded-md" />
      <div className="skeleton h-5 w-2/3 rounded-md" />
      <div className="skeleton h-3 w-full rounded-md" />
      <div className="skeleton h-3 w-5/6 rounded-md" />
      <div className="skeleton h-3 w-4/6 rounded-md" />
      <div className="skeleton h-10 rounded-xl" />
    </div>
  )
}

// ─── Trend Skeleton ──────────────────────────────────────────
export function TrendSkeleton() {
  return (
    <div className="glass rounded-2xl p-6 animate-pulse">
      <div className="skeleton h-5 w-40 rounded-md mb-6" />
      <div className="flex flex-col gap-3">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="flex items-center gap-3">
            <div className="skeleton h-4 w-20 rounded-md" />
            <div className="skeleton h-4 rounded-md flex-1" style={{ width: `${80 - i * 12}%` }} />
          </div>
        ))}
      </div>
    </div>
  )
}
