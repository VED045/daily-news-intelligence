import React, { useEffect, useState } from 'react'
import { BarChart3, TrendingUp, RefreshCw, AlertTriangle, Layers } from 'lucide-react'
import { getTrends, getTrendHistory } from '../services/api'
import { CategoryBarChart, KeywordCloud } from '../components/TrendChart'
import { TrendSkeleton } from '../components/Skeleton'

export default function Trends() {
  const [trends, setTrends] = useState(null)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const [tr, hist] = await Promise.all([getTrends(), getTrendHistory(7)])
      setTrends(tr)
      setHistory(hist.history || [])
    } catch {
      setError('Cannot connect to backend.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">

      {/* Header */}
      <div className="mb-8 animate-fade-in">
        <div className="flex items-center gap-2 text-purple-400 font-semibold text-sm mb-2">
          <BarChart3 size={16} /> Analytics
        </div>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-100 tracking-tight mb-1">
              Trends &amp; Insights
            </h1>
            {trends?.date && (
              <p className="text-slate-500 text-sm">Last updated: {trends.date}</p>
            )}
          </div>
          <button onClick={load} className="btn-ghost text-sm">
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-3 bg-red-500/10 border border-red-500/30 rounded-2xl px-5 py-4 mb-8 text-red-400 text-sm">
          <AlertTriangle size={18} /> {error}
        </div>
      )}

      {/* Summary Stats */}
      {!loading && trends && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-8 animate-slide-up">
          {[
            { label: 'Total Articles', value: trends.total_articles, color: 'text-cyan-400' },
            { label: 'Most Covered', value: trends.most_covered, color: 'text-amber-400' },
            { label: 'Trending Keywords', value: trends.trending_keywords?.length || 0, color: 'text-primary-400' },
          ].map(({ label, value, color }) => (
            <div key={label} className="glass rounded-2xl px-5 py-4">
              <div className="text-slate-500 text-xs font-medium mb-1">{label}</div>
              <div className={`font-bold text-xl capitalize ${color}`}>{value ?? '—'}</div>
            </div>
          ))}
        </div>
      )}

      <div className="grid lg:grid-cols-2 gap-6">

        {/* Category Bar Chart */}
        <div className="glass rounded-2xl p-6 animate-fade-in">
          <h2 className="font-semibold text-slate-200 text-base mb-5 flex items-center gap-2">
            <BarChart3 size={17} className="text-primary-400" />
            Articles by Category
          </h2>
          {loading ? <TrendSkeleton /> : (
            <CategoryBarChart data={trends?.category_counts} />
          )}
        </div>

        {/* Trending Keywords */}
        <div className="glass rounded-2xl p-6 animate-fade-in">
          <h2 className="font-semibold text-slate-200 text-base mb-5 flex items-center gap-2">
            <TrendingUp size={17} className="text-purple-400" />
            Trending Keywords
          </h2>
          {loading ? (
            <div className="flex flex-wrap gap-2">
              {[...Array(14)].map((_, i) => (
                <div key={i} className="skeleton h-7 rounded-full" style={{ width: `${60 + (i % 4) * 20}px` }} />
              ))}
            </div>
          ) : (
            <KeywordCloud keywords={trends?.trending_keywords} />
          )}
        </div>

        {/* History table */}
        {history.length > 0 && (
          <div className="glass rounded-2xl p-6 lg:col-span-2 animate-fade-in">
            <h2 className="font-semibold text-slate-200 text-base mb-5 flex items-center gap-2">
              <Layers size={17} className="text-cyan-400" />
              7-Day History
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-800">
                    <th className="text-left py-2 px-3 text-slate-500 font-medium">Date</th>
                    <th className="text-left py-2 px-3 text-slate-500 font-medium">Total Articles</th>
                    <th className="text-left py-2 px-3 text-slate-500 font-medium">Top Category</th>
                    <th className="text-left py-2 px-3 text-slate-500 font-medium">Categories</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map(row => (
                    <tr key={row.date} className="border-b border-slate-800/40 hover:bg-slate-800/30 transition-colors">
                      <td className="py-2.5 px-3 text-slate-300 font-medium">{row.date}</td>
                      <td className="py-2.5 px-3 text-cyan-400 font-semibold">{row.total_articles}</td>
                      <td className="py-2.5 px-3 text-amber-400 capitalize">{row.most_covered}</td>
                      <td className="py-2.5 px-3 text-slate-400">{Object.keys(row.category_counts || {}).length}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
