import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { Newspaper, AlertTriangle, RefreshCw, Loader2, X } from 'lucide-react'
import { getNews, searchNews } from '../services/api'
import NewsCard from '../components/NewsCard'
import CategoryFilter from '../components/CategoryFilter'
import SearchBar from '../components/SearchBar'
import { CardSkeleton } from '../components/Skeleton'
import { useTheme } from '../App'

const PAGE_SIZE = 10   // strict max 10 articles per page

export default function NewsFeed() {
  const { dark } = useTheme()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  // Read ?q= from URL (set by Dashboard trending click or direct link)
  const urlQuery = searchParams.get('q') || ''

  const [category, setCategory] = useState('all')
  const [searchQuery, setSearchQuery] = useState(urlQuery)
  const [articles, setArticles] = useState([])
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [activeTopic, setActiveTopic] = useState(urlQuery)  // shown as chip

  // When URL ?q changes (e.g. from Dashboard), sync state
  useEffect(() => {
    const q = searchParams.get('q') || ''
    setSearchQuery(q)
    setActiveTopic(q)
    setArticles([])
    setPage(1)
    setHasMore(true)
  }, [urlQuery])  // eslint-disable-line

  const fetchArticles = useCallback(async (pg, cat, q) => {
    setLoading(true); setError(null)
    try {
      let data
      if (q && q.length >= 2) {
        data = await searchNews(q, pg)
      } else {
        data = await getNews(cat === 'all' ? '' : cat, pg, PAGE_SIZE)
      }
      setArticles(prev => pg === 1 ? data.articles : [...prev, ...data.articles])
      setHasMore(data.has_more)
    } catch {
      setError('Failed to load news. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }, [])

  // Fetch when page / category / query changes
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

  const clearTopic = () => {
    handleSearch('')
    setSearchParams({})
  }

  // Keyword click on NewsCard → filter by that keyword
  const handleKeywordClick = (kw) => handleSearch(kw)

  const isSearchMode = !!searchQuery

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">

      {/* Header */}
      <div className="mb-8 animate-fade-in">
        <div className={`flex items-center gap-2 font-semibold text-sm mb-2 text-primary-500`}>
          <Newspaper size={16} /> News Feed
        </div>
        <h1 className={`text-2xl sm:text-3xl font-extrabold tracking-tight mb-3 ${dark ? 'text-slate-100' : 'text-slate-800'}`}>
          Latest Headlines
        </h1>
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
          <SearchBar onSearch={handleSearch} placeholder="Search articles… (press /)" />
          {!isSearchMode && (
            <button onClick={() => { setArticles([]); setPage(1); setHasMore(true) }} className="btn-ghost text-xs shrink-0">
              <RefreshCw size={14} /> Refresh
            </button>
          )}
        </div>
      </div>

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
          <CategoryFilter active={category} onChange={handleCategoryChange} />
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

      {/* Articles grid — strictly max 10 visible on screen */}
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
