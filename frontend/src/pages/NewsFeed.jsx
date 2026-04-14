import React, { useState, useEffect, useRef } from 'react'
import { Newspaper, AlertTriangle, RefreshCw, Loader2 } from 'lucide-react'
import { searchNews } from '../services/api'
import { useNews } from '../hooks/useNews'
import NewsCard from '../components/NewsCard'
import CategoryFilter from '../components/CategoryFilter'
import SearchBar from '../components/SearchBar'
import { CardSkeleton } from '../components/Skeleton'

export default function NewsFeed() {
  const [category, setCategory] = useState('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState(null)
  const [searching, setSearching] = useState(false)

  const { articles, loading, error, hasMore, loadMore, refresh } = useNews(
    searchQuery ? '' : (category === 'all' ? '' : category)
  )

  // Infinite scroll sentinel
  const sentinelRef = useRef(null)
  useEffect(() => {
    if (!sentinelRef.current) return
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting && hasMore && !loading) loadMore() },
      { threshold: 0.5 }
    )
    obs.observe(sentinelRef.current)
    return () => obs.disconnect()
  }, [hasMore, loading, loadMore])

  const handleSearch = async (q) => {
    setSearchQuery(q)
    if (!q) { setSearchResults(null); return }
    setSearching(true)
    try {
      const data = await searchNews(q)
      setSearchResults(data.articles)
    } catch { setSearchResults([]) }
    finally { setSearching(false) }
  }

  const handleCategoryChange = (cat) => {
    setCategory(cat)
    setSearchQuery('')
    setSearchResults(null)
  }

  const displayed = searchResults ?? articles
  const isSearchMode = !!searchQuery

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">

      {/* Header */}
      <div className="mb-8 animate-fade-in">
        <div className="flex items-center gap-2 text-primary-400 font-semibold text-sm mb-2">
          <Newspaper size={16} /> News Feed
        </div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-100 tracking-tight mb-3">
          Latest Headlines
        </h1>
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
          <SearchBar onSearch={handleSearch} placeholder="Search articles... (press /)" />
          {!isSearchMode && (
            <button onClick={refresh} className="btn-ghost text-xs shrink-0">
              <RefreshCw size={14} /> Refresh
            </button>
          )}
        </div>
      </div>

      {/* Category filter — hide in search mode */}
      {!isSearchMode && (
        <div className="mb-6">
          <CategoryFilter active={category} onChange={handleCategoryChange} />
        </div>
      )}

      {/* Search badge */}
      {isSearchMode && (
        <div className="mb-4 flex items-center gap-2 text-sm text-slate-400">
          <span>Showing results for</span>
          <span className="px-3 py-1 rounded-full bg-primary-500/10 text-primary-300 border border-primary-500/20 font-medium">
            "{searchQuery}"
          </span>
          <span className="text-slate-600">— {searchResults?.length ?? 0} found</span>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="flex items-center gap-3 bg-red-500/10 border border-red-500/30 rounded-2xl px-5 py-4 mb-6 text-red-400 text-sm">
          <AlertTriangle size={18} className="shrink-0" />
          {error}
          <button onClick={refresh} className="ml-auto btn-ghost text-red-400">
            <RefreshCw size={14} /> Retry
          </button>
        </div>
      )}

      {/* Grid */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {(loading && !articles.length) || searching
          ? [...Array(12)].map((_, i) => <CardSkeleton key={i} />)
          : displayed.map((article, i) => (
              <NewsCard key={article._id || article.url || i} article={article} />
            ))}
      </div>

      {/* Empty state */}
      {!loading && !searching && !displayed.length && (
        <div className="text-center py-20 text-slate-500 animate-fade-in">
          <Newspaper size={48} className="mx-auto mb-4 text-slate-700" />
          <p className="text-lg font-medium mb-1">No articles found</p>
          <p className="text-sm">
            {isSearchMode ? 'Try a different search term.' : 'Run the pipeline to fetch today\'s news.'}
          </p>
        </div>
      )}

      {/* Infinite scroll sentinel */}
      {!isSearchMode && (
        <div ref={sentinelRef} className="flex justify-center py-8">
          {loading && articles.length > 0 && (
            <Loader2 size={24} className="text-primary-400 animate-spin" />
          )}
          {!loading && !hasMore && articles.length > 0 && (
            <p className="text-slate-600 text-sm">You've reached the end</p>
          )}
        </div>
      )}
    </div>
  )
}
