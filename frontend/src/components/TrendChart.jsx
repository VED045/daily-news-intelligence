import React from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  Cell, PieChart, Pie, Legend
} from 'recharts'

// ─── Category Bar Chart ──────────────────────────────────────
const BAR_COLORS = [
  '#6366f1', '#8b5cf6', '#06b6d4', '#10b981',
  '#f59e0b', '#ef4444', '#ec4899', '#14b8a6',
]

export function CategoryBarChart({ data }) {
  const chartData = Object.entries(data || {})
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 10)

  if (!chartData.length) return (
    <div className="flex items-center justify-center h-40 text-slate-500 text-sm">
      No category data yet
    </div>
  )

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
        <XAxis
          dataKey="name"
          tick={{ fill: '#64748b', fontSize: 12 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: '#64748b', fontSize: 12 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          contentStyle={{
            background: '#1e293b',
            border: '1px solid rgba(99,102,241,0.2)',
            borderRadius: '10px',
            color: '#f1f5f9',
            fontSize: '13px',
          }}
          cursor={{ fill: 'rgba(99,102,241,0.08)' }}
        />
        <Bar dataKey="count" radius={[6, 6, 0, 0]}>
          {chartData.map((_, i) => (
            <Cell key={i} fill={BAR_COLORS[i % BAR_COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

// ─── Keywords Word Cloud (tag list) ─────────────────────────
export function KeywordCloud({ keywords, onKeywordClick }) {
  if (!keywords?.length) return (
    <div className="flex items-center justify-center h-24 text-slate-500 text-sm">
      No keyword data yet
    </div>
  )
  const max = keywords[0]?.count || 1

  return (
    <div className="flex flex-wrap gap-2 items-center">
      {keywords.slice(0, 20).map(({ word, count }) => {
        const size = 11 + Math.round((count / max) * 10)
        const opacity = 0.4 + (count / max) * 0.6
        return (
          <button
            key={word}
            onClick={() => onKeywordClick?.(word)}
            style={{ fontSize: size, opacity }}
            className="px-3 py-1 rounded-full bg-primary-500/10 text-primary-300 border border-primary-500/20
              hover:bg-primary-500/25 hover:opacity-100 transition-all cursor-pointer active:scale-95"
            title={`Filter news by "${word}" (${count} mentions)`}
          >
            {word}
            <span className="ml-1 text-primary-500/60 text-[10px]">{count}</span>
          </button>
        )
      })}
    </div>
  )
}


// ─── Mini stat bar ────────────────────────────────────────────
export function StatBar({ label, value, max, color = '#6366f1' }) {
  const pct = max ? Math.round((value / max) * 100) : 0
  return (
    <div className="flex items-center gap-3">
      <span className="text-slate-400 text-xs w-24 shrink-0 capitalize">{label}</span>
      <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
      <span className="text-slate-500 text-xs w-6 text-right">{value}</span>
    </div>
  )
}
