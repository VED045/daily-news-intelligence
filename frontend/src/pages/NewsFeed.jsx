import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Newspaper, AlertTriangle, RefreshCw, Loader2, X, Filter, Sparkles } from 'lucide-react'
import { getNews, searchNews, getMyFeed, getNewsSources, getCategoryCounts, getMeta } from '../services/api'
import NewsCard from '../components/NewsCard'
import CategoryFilter from '../components/CategoryFilter'
import SearchBar from '../components/SearchBar'
import { CardSkeleton } from '../components/Skeleton'
import { useTheme, useAuth, useLanguage, useFilters } from '../App'

const PAGE_SIZE = 10

const DATE_OPTIONS = [
  { id: 'today',  label: 'Today' },
  { id: '3days',  label: 'Last 3 Days' },
  { id: '7days',  label: 'Last 7 Days' },
]

function getDateRange(option, specificDay = '') {
  const now = new Date()
  const today = new Date(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()))

  if (specificDay !== '') {
    const dStart = new Date(today)
    dStart.setUTCDate(dStart.getUTCDate() - parseInt(specificDay))
    const dEnd = new Date(dStart)
    dEnd.setUTCDate(dEnd.getUTCDate() + 1)
    return { 
      date_from: dStart.toISOString().split('T')[0],
      date_to: dEnd.toISOString().split('T')[0]
    }
  }

  if (option === '3days') {
    const dStart = new Date(today)
    dStart.setUTCDate(dStart.getUTCDate() - 2)
    const dEnd = new Date(today)
    dEnd.setUTCDate(dEnd.getUTCDate() + 1)
    return { date_from: dStart.toISOString().split('T')[0], date_to: dEnd.toISOString().split('T')[0] }
  }
  if (option === '7days') {
    const dStart = new Date(today)
    dStart.setUTCDate(dStart.getUTCDate() - 6)
    const dEnd = new Date(today)
    dEnd.setUTCDate(dEnd.getUTCDate() + 1)
    return { date_from: dStart.toISOString().split('T')[0], date_to: dEnd.toISOString().split('T')[0] }
  }
  
  // today
  const dEnd = new Date(today)
  dEnd.setUTCDate(dEnd.getUTCDate() + 1)
  return { 
    date_from: today.toISOString().split('T')[0],
    date_to: dEnd.toISOString().split('T')[0]
  }
}

export default function NewsFeed() {
  const { dark } = useTheme()
  const { auth } = useAuth()
  const { language } = useLanguage()
  const { dateFilter, setDateFilter, specificDay, setSpecificDay, sourceFilter, setSourceFilter, category, setCategory } = useFilters()
  const [searchParams, setSearchParams] = useSearchParams()

  const urlQuery = searchParams.get('q') || ''

  const [searchQuery, setSearchQuery] = useState(urlQuery)
  const [articles, setArticles] = useState([])
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [activeTopic, setActiveTopic] = useState(urlQuery)

  // Filters
  const [sources, setSources] = useState([])
  const [categoryCounts, setCategoryCounts] = useState(null)
  const [showFilters, setShowFilters] = useState(false)
  const [usePersonalized, setUsePersonalized] = useState(!!auth)
  const [metaStats, setMetaStats] = useState(null)

  // Load sources list once
  useEffect(() => {
    getNewsSources().then(d => setSources(d.sources || [])).catch(() => {})
    getMeta().then(m => setMetaStats(m)).catch(() => {})
  }, [])

  useEffect(() => {
    const range = getDateRange(dateFilter, specificDay)
    getCategoryCounts({ ...range, language }).then(d => setCategoryCounts(d.category_counts || {})).catch(() => {})
  }, [dateFilter, specificDay, language])

  // Sync personalized toggle with auth
  useEffect(() => {
    setUsePersonalized(!!auth)
  }, [auth])

  // When URL ?q changes, sync state
  useEffect(() => {
    const q = searchParams.get('q') || ''
    setSearchQuery(q)
    setActiveTopic(q)
    setArticles([])
    setPage(1)
    setHasMore(true)
  }, [urlQuery]) // eslint-disable-line

  const fetchArticles = useCallback(async (pg, cat, q) => {
    setLoading(true); setError(null)
    try {
      let data
      if (q && q.length >= 2) {
        data = await searchNews(q, pg) // note: search doesn't accept language right now, kept as is
      } else if (auth && usePersonalized) {
        const filters = { ...getDateRange(dateFilter, specificDay) }
        if (sourceFilter) filters.source = sourceFilter
        data = await getMyFeed({
          page: pg,
          limit: PAGE_SIZE,
          category: cat === 'all' ? undefined : cat,
          source: sourceFilter || undefined,
          date_from: filters.date_from || undefined,
          date_to: filters.date_to || undefined
        })
      } else {
        const filters = getDateRange(dateFilter, specificDay)
        if (sourceFilter) filters.source = sourceFilter
        data = await getNews(cat === 'all' ? '' : cat, pg, PAGE_SIZE, '', filters, language)
      }
      setArticles(prev => pg === 1 ? data.articles : [...prev, ...data.articles])
      setHasMore(data.has_more)
    } catch {
      setError('Failed to load news. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }, [auth, usePersonalized, dateFilter, specificDay, sourceFilter, language])

  // Fetch when page / category / query / filters change
  useEffect(() => {
    fetchArticles(page, category, searchQuery)
  }, [page, category, searchQuery, fetchArticles])

  // Infinite scroll
  const sentinelRef = useRef(null)
  useEffect(() => {
    if (!sentinelRef.current) return
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting && hasMore && !loading) setPage(p => p + 1) },
      { threshold: 0.5 }
    )
    obs.observe(sentinelRef.current)
    return () => obs.disconnect()
  }, [hasMore, loading])

  const handleSearch = (q) => {
    setSearchQuery(q)
    setActiveTopic(q)
    setArticles([])
    setPage(1)
    setHasMore(true)
    if (q) setSearchParams({ q })
    else setSearchParams({})
  }

  const handleCategoryChange = (cat) => {
    setCategory(cat)
    setSearchQuery('')
    setActiveTopic('')
    setSearchParams({})
    setArticles([])
    setPage(1)
    setHasMore(true)
  }

  const resetFilters = () => {
    setDateFilter('today')
    setSpecificDay('')
    setSourceFilter('')
    setArticles([])
    setPage(1)
    setHasMore(true)
  }

  const clearTopic = () => {
    handleSearch('')
    setSearchParams({})
  }

  const handleKeywordClick = (kw) => handleSearch(kw)

  const isSearchMode = !!searchQuery
  const hasActiveFilters = dateFilter !== 'today' || sourceFilter

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">

      {/* Header */}
      <div className="mb-8 animate-fade-in">
        <div className={`flex items-center gap-2 font-semibold text-sm mb-2 text-primary-500`}>
          <Newspaper size={16} /> News Feed
          {auth && usePersonalized && (
            <span className="flex items-center gap-1 ml-2 px-2 py-0.5 rounded-full text-xs bg-purple-500/15 text-purple-400 border border-purple-500/25">
              <Sparkles size={10} /> Personalized
            </span>
          )}
        </div>
        <h1 className={`text-2xl sm:text-3xl font-extrabold tracking-tight mb-3 ${dark ? 'text-slate-100' : 'text-slate-800'}`}>
          Latest Headlines
        </h1>
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
          <SearchBar onSearch={handleSearch} placeholder="Search articles… (press /)" />
          <div className="flex items-center gap-2">
            {!isSearchMode && (
              <button onClick={() => { setArticles([]); setPage(1); setHasMore(true) }} className="btn-ghost text-xs shrink-0">
                <RefreshCw size={14} /> Refresh
              </button>
            )}
            <button
              onClick={() => setShowFilters(f => !f)}
              className={`btn-ghost text-xs shrink-0 ${showFilters || hasActiveFilters ? 'text-primary-500' : ''}`}
            >
              <Filter size={14} /> Filters {hasActiveFilters && '•'}
            </button>
            {auth && (
              <button
                onClick={() => { setUsePersonalized(p => !p); setArticles([]); setPage(1); setHasMore(true) }}
                className={`btn-ghost text-xs shrink-0 ${usePersonalized ? 'text-purple-400' : ''}`}
              >
                <Sparkles size={14} /> {usePersonalized ? 'Default Feed' : 'My Feed'}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Meta Stats tracking UI */}
      {metaStats && !isSearchMode && (
        <div className="flex gap-4 mb-4 text-xs font-semibold animate-fade-in text-slate-500">
           {metaStats.news_api_count > 0 && <span className="bg-blue-50 text-blue-600 px-2.5 py-1 rounded-full border border-blue-200">NewsAPI Articles: {metaStats.news_api_count}</span>}
           {metaStats.rss_count > 0 && <span className="bg-orange-50 text-orange-600 px-2.5 py-1 rounded-full border border-orange-200">RSS Articles: {metaStats.rss_count}</span>}
           {metaStats.news_api_count === 0 && <span className="bg-slate-100 text-slate-500 px-2.5 py-1 rounded-full border border-slate-200">NewsAPI Count: 0</span>}
        </div>
      )}

      {/* Filter panel handled by Navbar on Desktop, but kept for non-navbar overrides or mobile */}
      {showFilters && !isSearchMode && (
        <div className={`mb-6 rounded-2xl p-5 animate-fade-in ${dark ? 'glass' : 'bg-white border border-slate-200 shadow-sm'}`}>
          <div className="flex flex-wrap items-end gap-4">
            {/* Date filter */}
            <div>
              <label className={`block text-xs font-medium mb-1.5 ${dark ? 'text-slate-400' : 'text-slate-500'}`}>Date Range</label>
              <div className="flex gap-2">
                {DATE_OPTIONS.map(opt => (
                  <button
                    key={opt.id}
                    onClick={() => { setDateFilter(opt.id); setSpecificDay(''); setArticles([]); setPage(1); setHasMore(true) }}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                      dateFilter === opt.id
                        ? 'bg-primary-500 text-white border-primary-500'
                        : dark
                          ? 'bg-slate-800 text-slate-400 border-slate-700 hover:border-primary-500/40'
                          : 'bg-white text-slate-500 border-slate-200 hover:border-primary-300'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
              
              {/* Day-wise exact filter */}
              {dateFilter === '7days' && (
                <div className="mt-2 flex gap-2 overflow-x-auto pb-1" style={{ scrollbarWidth: 'thin' }}>
                  <button
                    onClick={() => { setSpecificDay(''); setArticles([]); setPage(1); setHasMore(true) }}
                    className={`px-2 py-1 rounded text-[10px] font-medium border transition-all ${
                      specificDay === ''
                        ? 'bg-slate-600 text-white border-slate-600'
                        : dark ? 'bg-slate-800 text-slate-400 border-slate-700' : 'bg-white text-slate-500 border-slate-200'
                    }`}
                  >
                    All 7 Days
                  </button>
                  {[...Array(8)].map((_, i) => {
                    const label = i === 0 ? 'Today' : i === 1 ? 'Yesterday' : `${i} days ago`
                    return (
                      <button
                        key={i}
                        onClick={() => { setSpecificDay(i.toString()); setArticles([]); setPage(1); setHasMore(true) }}
                        className={`px-2 py-1 rounded text-[10px] font-medium border transition-all whitespace-nowrap ${
                          specificDay === i.toString()
                            ? 'bg-slate-600 text-white border-slate-600'
                            : dark ? 'bg-slate-800 text-slate-400 border-slate-700' : 'bg-white text-slate-500 border-slate-200'
                        }`}
                      >
                        {label}
                      </button>
                    )
                  })}
                </div>
              )}
            </div>
            {/* Source filter */}
            <div>
              <label className={`block text-xs font-medium mb-1.5 ${dark ? 'text-slate-400' : 'text-slate-500'}`}>Source</label>
              <select
                value={sourceFilter}
                onChange={(e) => { setSourceFilter(e.target.value); setArticles([]); setPage(1); setHasMore(true) }}
                className={`px-3 py-1.5 rounded-lg text-xs border ${
                  dark ? 'bg-slate-800 text-slate-300 border-slate-700' : 'bg-white text-slate-700 border-slate-200'
                }`}
              >
                <option value="">All Sources</option>
                {sources.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            {hasActiveFilters && (
              <button onClick={resetFilters} className="btn-ghost text-xs text-red-400">
                <X size={12} /> Clear
              </button>
            )}
          </div>
        </div>
      )}

      {/* Active topic chip */}
      {activeTopic && (
        <div className="flex items-center gap-2 mb-4 animate-fade-in">
          <span className={`text-sm ${dark ? 'text-slate-400' : 'text-slate-500'}`}>Filtered by topic:</span>
          <span className={`flex items-center gap-2 px-3 py-1 rounded-full text-sm font-semibold border
            ${dark ? 'bg-primary-500/10 text-primary-300 border-primary-500/25' : 'bg-primary-50 text-primary-600 border-primary-200'}`}>
            {activeTopic}
            <button onClick={clearTopic} className="hover:opacity-60 transition-opacity">
              <X size={13} />
            </button>
          </span>
          <span className={`text-xs ${dark ? 'text-slate-600' : 'text-slate-400'}`}>
            {articles.length} article{articles.length !== 1 ? 's' : ''} found
          </span>
        </div>
      )}

      {/* Category filter */}
      {!isSearchMode && (
        <div className="mb-6">
          <CategoryFilter active={category} onChange={handleCategoryChange} counts={categoryCounts} />
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="flex items-center gap-3 bg-red-500/10 border border-red-500/30 rounded-2xl px-5 py-4 mb-6 text-red-400 text-sm">
          <AlertTriangle size={18} className="shrink-0" />{error}
          <button onClick={() => fetchArticles(1, category, searchQuery)} className="ml-auto btn-ghost text-red-400">
            <RefreshCw size={14} /> Retry
          </button>
        </div>
      )}

      {/* Articles grid */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {loading && !articles.length
          ? [...Array(PAGE_SIZE)].map((_, i) => <CardSkeleton key={i} />)
          : articles.slice(0, PAGE_SIZE * page).map((article, i) => (
              <NewsCard
                key={article._id || article.url || i}
                article={article}
                onKeywordClick={handleKeywordClick}
              />
            ))}
      </div>

      {/* Empty state */}
      {!loading && !articles.length && (
        <div className="text-center py-20 animate-fade-in">
          <Newspaper size={48} className="mx-auto mb-4 opacity-20" />
          <p className={`text-lg font-medium mb-1 ${dark ? 'text-slate-400' : 'text-slate-500'}`}>No articles found</p>
          <p className={`text-sm ${dark ? 'text-slate-600' : 'text-slate-400'}`}>
            {isSearchMode ? `No results for "${searchQuery}". Try another term.` : 'Click "Fetch Latest News" in the navbar to get today\'s headlines.'}
          </p>
        </div>
      )}

      {/* Infinite scroll sentinel */}
      {!isSearchMode && (
        <div ref={sentinelRef} className="flex justify-center py-8">
          {loading && articles.length > 0 && <Loader2 size={24} className="text-primary-500 animate-spin" />}
          {!loading && !hasMore && articles.length > 0 && (
            <p className={`text-sm ${dark ? 'text-slate-600' : 'text-slate-400'}`}>You've reached the end</p>
          )}
        </div>
      )}
    </div>
  )
}
