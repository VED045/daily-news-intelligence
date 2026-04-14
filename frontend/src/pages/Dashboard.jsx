import React, { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Star, TrendingUp, BarChart3, Newspaper, ArrowRight, RefreshCw, AlertTriangle, Clock } from 'lucide-react'
import { getTop5, getTrends, getMeta } from '../services/api'
import Top5Card from '../components/Top5Card'
import { Top5Skeleton, TrendSkeleton } from '../components/Skeleton'
import { StatBar } from '../components/TrendChart'
import { useTheme } from '../App'

/** Returns a human-readable "X minutes ago" style string from an ISO timestamp. */
function timeAgo(isoString) {
  if (!isoString) return null
  let str = isoString.trim()
  if (!str.endsWith('Z') && !str.includes('+') && !/[+-]\d{2}:\d{2}$/.test(str)) {
    str += 'Z'
  }
  const date = new Date(str)
  if (isNaN(date.getTime())) return null

  const diffSec = Math.floor((Date.now() - date.getTime()) / 1000)
  if (diffSec < 0)     return 'just now'
  if (diffSec < 60)    return `${diffSec} seconds ago`
  if (diffSec < 3600)  return `${Math.floor(diffSec / 60)} minutes ago`
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)} hours ago`
  return `${Math.floor(diffSec / 86400)} days ago`
}

export default function Dashboard() {
  const { dark } = useTheme()
  const navigate = useNavigate()
  const [top5, setTop5] = useState(null)
  const [trends, setTrends] = useState(null)
  const [meta, setMeta] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = async () => {
    setLoading(true); setError(null)
    try {
      const [t5, tr, mt] = await Promise.all([getTop5(), getTrends(), getMeta()])
      setTop5(t5); setTrends(tr); setMeta(mt)
    } catch {
      setError('Cannot connect to backend. Start the FastAPI server first.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  // Click a trending keyword → News Feed filtered by that topic
  const handleTopicClick = (word) => {
    navigate(`/news?q=${encodeURIComponent(word)}`)
  }

  const maxCat = trends ? Math.max(...Object.values(trends.category_counts || {}), 1) : 1

  const card = dark
    ? 'glass rounded-2xl px-5 py-4 flex items-center gap-3'
    : 'bg-white rounded-2xl px-5 py-4 flex items-center gap-3 border border-slate-200 shadow-sm'

  const lastUpdated = meta ? timeAgo(meta.lastFetchedAt) : null

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">

      {/* Hero */}
      <div className="mb-10 animate-fade-in">
        <div className="flex items-center gap-2 text-primary-500 font-semibold text-sm mb-2">
          <Star size={16} className="fill-primary-500" /> AI-Powered Daily Digest
        </div>
        <h1 className={`text-3xl sm:text-4xl font-extrabold tracking-tight mb-3 ${dark ? 'text-slate-100' : 'text-slate-800'}`}>
          <span className="text-primary-500">Dainik</span>
          <span className={dark ? 'text-slate-100' : 'text-slate-800'}>-Vidya</span>
        </h1>
        <p className={`text-base max-w-xl mb-3 ${dark ? 'text-slate-400' : 'text-slate-500'}`}>
          AI-curated headlines from BBC, Reuters, The Hindu, ESPN, Times of India,
          Moneycontrol, CNBC &amp; Yahoo Finance — ranked, summarised, and ready.
        </p>

        {/* Last updated badge */}
        <div className={`inline-flex items-center gap-2 text-xs px-3 py-1.5 rounded-full border font-medium transition-all
          ${dark
            ? 'bg-slate-800/60 border-slate-700 text-slate-400'
            : 'bg-slate-50 border-slate-200 text-slate-500'}`}>
          <Clock size={12} className={meta?.lastFetchedAt ? 'text-emerald-500' : 'text-slate-500'} />
          {loading
            ? 'Loading last fetch time…'
            : lastUpdated
              ? `Last updated: ${lastUpdated}`
              : `Total articles: ${meta?.totalArticles ?? '—'} — click "Fetch Latest News" to refresh`}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-3 bg-red-500/10 border border-red-500/30 rounded-2xl px-5 py-4 mb-8 text-red-400 text-sm animate-fade-in">
          <AlertTriangle size={18} className="shrink-0" />
          <span>{error}</span>
          <button onClick={load} className="ml-auto btn-ghost text-red-400 hover:text-red-300">
            <RefreshCw size={14} /> Retry
          </button>
        </div>
      )}

      {/* Stat cards */}
      {trends && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-10 animate-slide-up">
          {[
            { label: 'Total Articles', value: meta?.totalArticles ?? trends.total_articles, icon: Newspaper, color: 'text-cyan-500' },
            { label: 'Categories',     value: Object.keys(trends.category_counts || {}).length, icon: BarChart3, color: 'text-purple-500' },
            { label: 'Top Category',   value: trends.most_covered, icon: TrendingUp, color: 'text-amber-500' },
            { label: 'Trending Topics',value: trends.trending_keywords?.length || 0, icon: Star, color: 'text-primary-500' },
          ].map(({ label, value, icon: Icon, color }) => (
            <div key={label} className={card}>
              <div className={`${color} shrink-0`}><Icon size={22} /></div>
              <div>
                <div className={`text-xs font-medium ${dark ? 'text-slate-400' : 'text-slate-500'}`}>{label}</div>
                <div className={`font-bold text-lg capitalize ${dark ? 'text-slate-100' : 'text-slate-800'}`}>{value ?? '—'}</div>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="grid xl:grid-cols-3 gap-8">

        {/* Top 5 — 2/3 width */}
        <div className="xl:col-span-2">
          <div className="flex items-center justify-between mb-5">
            <h2 className={`font-bold text-xl flex items-center gap-2 ${dark ? 'text-slate-100' : 'text-slate-800'}`}>
              🔥 <span>Top 5 Today</span>
            </h2>
            <Link to="/news" className="btn-ghost text-xs">All News <ArrowRight size={14} /></Link>
          </div>

          {loading ? (
            <div className="grid gap-4">{[...Array(3)].map((_, i) => <Top5Skeleton key={i} />)}</div>
          ) : top5?.items?.length > 0 ? (
            <div className="grid gap-4">
              {top5.items.map(item => <Top5Card key={item.rank} item={item} />)}
            </div>
          ) : (
            <div className={`rounded-2xl p-10 text-center ${dark ? 'glass text-slate-500' : 'bg-white border border-slate-200 text-slate-400 shadow-sm'}`}>
              <Star size={36} className="mx-auto mb-3 opacity-30" />
              <p className="font-medium mb-1">No Top 5 yet</p>
              <p className="text-sm">Click <strong className="text-primary-500">Fetch Latest News</strong> in the navbar to get today's headlines.</p>
            </div>
          )}
        </div>

        {/* Sidebar — 1/3 width */}
        <div className="flex flex-col gap-6">

          {/* Category breakdown */}
          <div className={`rounded-2xl p-5 ${dark ? 'glass' : 'bg-white border border-slate-200 shadow-sm'}`}>
            <h3 className={`font-semibold text-sm mb-4 flex items-center gap-2 ${dark ? 'text-slate-200' : 'text-slate-700'}`}>
              <BarChart3 size={15} className="text-primary-500" /> Coverage by Category
            </h3>
            {loading ? <TrendSkeleton /> : (
              <div className="flex flex-col gap-2.5">
                {Object.entries(trends?.category_counts || {})
                  .sort(([, a], [, b]) => b - a).slice(0, 8)
                  .map(([cat, count]) => <StatBar key={cat} label={cat} value={count} max={maxCat} />)}
                {!Object.keys(trends?.category_counts || {}).length && (
                  <p className={`text-sm ${dark ? 'text-slate-500' : 'text-slate-400'}`}>No data yet</p>
                )}
              </div>
            )}
          </div>

          {/* Trending Keywords — clickable */}
          <div className={`rounded-2xl p-5 ${dark ? 'glass' : 'bg-white border border-slate-200 shadow-sm'}`}>
            <h3 className={`font-semibold text-sm mb-1 flex items-center gap-2 ${dark ? 'text-slate-200' : 'text-slate-700'}`}>
              <TrendingUp size={15} className="text-purple-500" /> Trending Topics
            </h3>
            <p className={`text-xs mb-3 ${dark ? 'text-slate-600' : 'text-slate-400'}`}>Click any topic to filter the news feed</p>
            {loading ? (
              <div className="flex flex-wrap gap-2">
                {[...Array(10)].map((_, i) => <div key={i} className="skeleton h-6 rounded-full" style={{ width: `${50 + i * 10}px` }} />)}
              </div>
            ) : (
              <div className="flex flex-wrap gap-2">
                {(trends?.trending_keywords || []).slice(0, 15).map(({ word, count }) => (
                  <button
                    key={word}
                    onClick={() => handleTopicClick(word)}
                    title={`Filter news by "${word}"`}
                    className={`px-3 py-1 rounded-full text-xs font-medium border transition-all cursor-pointer hover:scale-105 active:scale-95
                      ${dark
                        ? 'bg-primary-500/10 text-primary-300 border-primary-500/15 hover:bg-primary-500/25 hover:border-primary-500/40'
                        : 'bg-primary-50 text-primary-600 border-primary-200 hover:bg-primary-100 hover:border-primary-300'}`}
                  >
                    {word} <span className="opacity-60 ml-0.5">{count}</span>
                  </button>
                ))}
                {!(trends?.trending_keywords?.length) && (
                  <p className={`text-sm ${dark ? 'text-slate-500' : 'text-slate-400'}`}>No data yet</p>
                )}
              </div>
            )}
          </div>

          {/* Quick Links */}
          <div className={`rounded-2xl p-5 ${dark ? 'glass' : 'bg-white border border-slate-200 shadow-sm'}`}>
            <h3 className={`font-semibold text-sm mb-3 ${dark ? 'text-slate-200' : 'text-slate-700'}`}>Quick Links</h3>
            <div className="flex flex-col gap-2">
              {[
                { to: '/news',      label: 'Browse all news',   icon: Newspaper },
                { to: '/bookmarks', label: 'Saved bookmarks',   icon: Star },
                { to: '/trends',    label: 'View trend charts', icon: BarChart3 },
              ].map(({ to, label, icon: Icon }) => (
                <Link key={to} to={to} className={`flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-sm transition-all
                  ${dark ? 'text-slate-400 hover:text-slate-200 hover:bg-slate-800' : 'text-slate-500 hover:text-slate-800 hover:bg-slate-50'}`}>
                  <Icon size={15} className="text-primary-500" /> {label}
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
