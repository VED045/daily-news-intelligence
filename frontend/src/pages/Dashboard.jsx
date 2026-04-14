import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Star, TrendingUp, BarChart3, Newspaper, ArrowRight, RefreshCw, AlertTriangle } from 'lucide-react'
import { getTop5, getTrends } from '../services/api'
import Top5Card from '../components/Top5Card'
import { Top5Skeleton, TrendSkeleton } from '../components/Skeleton'
import { StatBar } from '../components/TrendChart'

export default function Dashboard() {
  const [top5, setTop5] = useState(null)
  const [trends, setTrends] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const [t5, tr] = await Promise.all([getTop5(), getTrends()])
      setTop5(t5)
      setTrends(tr)
    } catch {
      setError('Cannot connect to backend. Start the FastAPI server first.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const maxCat = trends ? Math.max(...Object.values(trends.category_counts || {}), 1) : 1

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">

      {/* Hero Header */}
      <div className="mb-10 animate-fade-in">
        <div className="flex items-center gap-2 text-primary-400 font-semibold text-sm mb-2">
          <Star size={16} className="fill-primary-400" />
          AI-Powered Daily Digest
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-100 tracking-tight mb-3">
          Daily News{' '}
          <span className="bg-gradient-to-r from-primary-400 to-purple-400 bg-clip-text text-transparent">
            Intelligence
          </span>
        </h1>
        <p className="text-slate-400 text-base max-w-xl">
          AI-curated headlines from BBC, Reuters, The Hindu, ESPN, Times of India &amp; Moneycontrol — summarized, ranked, and ready.
        </p>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="flex items-center gap-3 bg-red-500/10 border border-red-500/30 rounded-2xl px-5 py-4 mb-8 text-red-400 text-sm animate-fade-in">
          <AlertTriangle size={18} className="shrink-0" />
          <span>{error}</span>
          <button onClick={load} className="ml-auto btn-ghost text-red-400 hover:text-red-300">
            <RefreshCw size={14} /> Retry
          </button>
        </div>
      )}

      {/* Stats row */}
      {trends && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-10 animate-slide-up">
          {[
            { label: 'Total Articles', value: trends.total_articles, icon: Newspaper, color: 'text-cyan-400' },
            { label: 'Categories', value: Object.keys(trends.category_counts || {}).length, icon: BarChart3, color: 'text-purple-400' },
            { label: 'Top Category', value: trends.most_covered, icon: TrendingUp, color: 'text-amber-400' },
            { label: 'Trending Topics', value: trends.trending_keywords?.length || 0, icon: Star, color: 'text-primary-400' },
          ].map(({ label, value, icon: Icon, color }) => (
            <div key={label} className="glass rounded-2xl px-5 py-4 flex items-center gap-3">
              <div className={`${color} shrink-0`}><Icon size={22} /></div>
              <div>
                <div className="text-slate-400 text-xs font-medium">{label}</div>
                <div className="text-slate-100 font-bold text-lg capitalize">{value ?? '—'}</div>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="grid xl:grid-cols-3 gap-8">

        {/* Top 5 Section — 2/3 width */}
        <div className="xl:col-span-2">
          <div className="flex items-center justify-between mb-5">
            <h2 className="font-bold text-xl text-slate-100 flex items-center gap-2">
              🔥 <span>Top 5 Today</span>
            </h2>
            <Link to="/news" className="btn-ghost text-xs">
              All News <ArrowRight size={14} />
            </Link>
          </div>

          {loading ? (
            <div className="grid gap-4">
              {[...Array(3)].map((_, i) => <Top5Skeleton key={i} />)}
            </div>
          ) : top5?.items?.length > 0 ? (
            <div className="grid gap-4">
              {top5.items.map(item => <Top5Card key={item.rank} item={item} />)}
            </div>
          ) : (
            <div className="glass rounded-2xl p-10 text-center text-slate-500">
              <Star size={36} className="mx-auto mb-3 text-slate-700" />
              <p className="font-medium mb-1">No Top 5 yet</p>
              <p className="text-sm">Click <strong className="text-primary-400">Run Pipeline</strong> in the nav to fetch and process today's news.</p>
            </div>
          )}
        </div>

        {/* Sidebar — 1/3 width */}
        <div className="flex flex-col gap-6">

          {/* Category breakdown */}
          <div className="glass rounded-2xl p-5">
            <h3 className="font-semibold text-slate-200 text-sm mb-4 flex items-center gap-2">
              <BarChart3 size={15} className="text-primary-400" /> Coverage by Category
            </h3>
            {loading ? <TrendSkeleton /> : (
              <div className="flex flex-col gap-2.5">
                {Object.entries(trends?.category_counts || {})
                  .sort(([, a], [, b]) => b - a)
                  .slice(0, 8)
                  .map(([cat, count]) => (
                    <StatBar key={cat} label={cat} value={count} max={maxCat} />
                  ))}
                {!Object.keys(trends?.category_counts || {}).length && (
                  <p className="text-slate-500 text-sm">No data yet</p>
                )}
              </div>
            )}
          </div>

          {/* Trending Keywords */}
          <div className="glass rounded-2xl p-5">
            <h3 className="font-semibold text-slate-200 text-sm mb-4 flex items-center gap-2">
              <TrendingUp size={15} className="text-purple-400" /> Trending Topics
            </h3>
            {loading ? (
              <div className="flex flex-wrap gap-2">
                {[...Array(10)].map((_, i) => (
                  <div key={i} className="skeleton h-6 rounded-full" style={{ width: `${50 + i * 10}px` }} />
                ))}
              </div>
            ) : (
              <div className="flex flex-wrap gap-2">
                {(trends?.trending_keywords || []).slice(0, 15).map(({ word, count }) => (
                  <span key={word} className="px-3 py-1 rounded-full text-xs bg-primary-500/10 text-primary-300 border border-primary-500/15 hover:bg-primary-500/20 transition-colors cursor-default">
                    {word} <span className="opacity-60 ml-0.5">{count}</span>
                  </span>
                ))}
                {!(trends?.trending_keywords?.length) && (
                  <p className="text-slate-500 text-sm">No data yet</p>
                )}
              </div>
            )}
          </div>

          {/* Quick links */}
          <div className="glass rounded-2xl p-5">
            <h3 className="font-semibold text-slate-200 text-sm mb-3">Quick Links</h3>
            <div className="flex flex-col gap-2">
              {[
                { to: '/news', label: 'Browse all news', icon: Newspaper },
                { to: '/trends', label: 'View trend charts', icon: BarChart3 },
                { to: '/subscribe', label: 'Get daily digest', icon: Star },
              ].map(({ to, label, icon: Icon }) => (
                <Link key={to} to={to} className="flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-all text-sm">
                  <Icon size={15} className="text-primary-400" /> {label}
                  <ArrowRight size={12} className="ml-auto" />
                </Link>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
