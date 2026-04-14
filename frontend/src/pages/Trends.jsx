import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { BarChart3, TrendingUp, RefreshCw, AlertTriangle, Layers } from 'lucide-react'
import { getTrends, getTrendHistory } from '../services/api'
import { CategoryBarChart, KeywordCloud } from '../components/TrendChart'
import { TrendSkeleton } from '../components/Skeleton'
import { useTheme } from '../App'

export default function Trends() {
  const { dark } = useTheme()
  const navigate = useNavigate()
  const [trends, setTrends] = useState(null)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = async () => {
    setLoading(true); setError(null)
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

  // Click a trending keyword → go to News Feed filtered by that topic
  const handleKeywordClick = (word) => {
    navigate(`/news?q=${encodeURIComponent(word)}`)
  }

  const panel = dark
    ? 'glass rounded-2xl p-6 animate-fade-in'
    : 'bg-white rounded-2xl p-6 border border-slate-200 shadow-sm animate-fade-in'

  const statCard = dark
    ? 'glass rounded-2xl px-5 py-4'
    : 'bg-white rounded-2xl px-5 py-4 border border-slate-200 shadow-sm'

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">

      {/* Header */}
      <div className="mb-8 animate-fade-in">
        <div className="flex items-center gap-2 text-purple-500 font-semibold text-sm mb-2">
          <BarChart3 size={16} /> Analytics
        </div>
        <div className="flex items-center justify-between">
          <div>
            <h1 className={`text-2xl sm:text-3xl font-extrabold tracking-tight mb-1 ${dark ? 'text-slate-100' : 'text-slate-800'}`}>
              Trends &amp; Insights
            </h1>
            {trends?.date && (
              <p className={`text-sm ${dark ? 'text-slate-500' : 'text-slate-400'}`}>Last updated: {trends.date}</p>
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

      {/* Summary stats */}
      {!loading && trends && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-8 animate-slide-up">
          {[
            { label: 'Total Articles',    value: trends.total_articles,                 color: 'text-cyan-500' },
            { label: 'Most Covered',      value: trends.most_covered,                   color: 'text-amber-500' },
            { label: 'Trending Keywords', value: trends.trending_keywords?.length || 0, color: 'text-primary-500' },
          ].map(({ label, value, color }) => (
            <div key={label} className={statCard}>
              <div className={`text-xs font-medium mb-1 ${dark ? 'text-slate-500' : 'text-slate-400'}`}>{label}</div>
              <div className={`font-bold text-xl capitalize ${color}`}>{value ?? '—'}</div>
            </div>
          ))}
        </div>
      )}

      <div className="grid lg:grid-cols-2 gap-6">

        {/* Category Bar Chart */}
        <div className={panel}>
          <h2 className={`font-semibold text-base mb-5 flex items-center gap-2 ${dark ? 'text-slate-200' : 'text-slate-700'}`}>
            <BarChart3 size={17} className="text-primary-500" /> Articles by Category
          </h2>
          {loading ? <TrendSkeleton /> : <CategoryBarChart data={trends?.category_counts} />}
        </div>

        {/* Trending Keywords — clickable */}
        <div className={panel}>
          <h2 className={`font-semibold text-base mb-1 flex items-center gap-2 ${dark ? 'text-slate-200' : 'text-slate-700'}`}>
            <TrendingUp size={17} className="text-purple-500" /> Trending Keywords
          </h2>
          <p className={`text-xs mb-4 ${dark ? 'text-slate-600' : 'text-slate-400'}`}>
            Click any keyword to filter the news feed by that topic
          </p>
          {loading ? (
            <div className="flex flex-wrap gap-2">
              {[...Array(14)].map((_, i) => (
                <div key={i} className="skeleton h-7 rounded-full" style={{ width: `${60 + (i % 4) * 20}px` }} />
              ))}
            </div>
          ) : (
            <KeywordCloud
              keywords={trends?.trending_keywords}
              onKeywordClick={handleKeywordClick}
            />
          )}
        </div>

        {/* 7-day history table */}
        {history.length > 0 && (
          <div className={`${panel} lg:col-span-2`}>
            <h2 className={`font-semibold text-base mb-5 flex items-center gap-2 ${dark ? 'text-slate-200' : 'text-slate-700'}`}>
              <Layers size={17} className="text-cyan-500" /> 7-Day History
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className={`border-b ${dark ? 'border-slate-800' : 'border-slate-200'}`}>
                    {['Date', 'Total Articles', 'Top Category', 'Categories'].map(h => (
                      <th key={h} className={`text-left py-2 px-3 font-medium ${dark ? 'text-slate-500' : 'text-slate-400'}`}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {history.map(row => (
                    <tr key={row.date} className={`border-b transition-colors
                      ${dark ? 'border-slate-800/40 hover:bg-slate-800/30' : 'border-slate-100 hover:bg-slate-50'}`}>
                      <td className={`py-2.5 px-3 font-medium ${dark ? 'text-slate-300' : 'text-slate-700'}`}>{row.date}</td>
                      <td className="py-2.5 px-3 text-cyan-500 font-semibold">{row.total_articles}</td>
                      <td className="py-2.5 px-3 text-amber-500 capitalize">{row.most_covered}</td>
                      <td className={`py-2.5 px-3 ${dark ? 'text-slate-400' : 'text-slate-500'}`}>{Object.keys(row.category_counts || {}).length}</td>
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
