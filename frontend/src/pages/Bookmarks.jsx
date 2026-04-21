import React, { useState, useEffect, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Bookmark, Loader2, AlertTriangle, RefreshCw, Newspaper } from 'lucide-react'
import { getBookmarks } from '../services/api'
import NewsCard from '../components/NewsCard'
import { useTheme, useAuth } from '../App'
import toast from 'react-hot-toast'

function timeAgo(isoString) {
  if (!isoString) return null
  let str = isoString.trim()
  if (!str.endsWith('Z') && !str.includes('+') && !/[+-]\d{2}:\d{2}$/.test(str)) str += 'Z'
  const date = new Date(str)
  if (isNaN(date.getTime())) return null
  const diffSec = Math.floor((Date.now() - date.getTime()) / 1000)
  if (diffSec < 60)    return `${diffSec}s ago`
  if (diffSec < 3600)  return `${Math.floor(diffSec / 60)}m ago`
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`
  return `${Math.floor(diffSec / 86400)}d ago`
}

export default function Bookmarks() {
  const { dark } = useTheme()
  const { auth } = useAuth()
  const navigate = useNavigate()
  const [articles, setArticles] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Auth guard
  useEffect(() => {
    if (!auth) {
      sessionStorage.setItem('redirectAfterLogin', 'bookmark')
      toast('Please log in to view bookmarks', { icon: '🔒' })
      navigate('/login')
    }
  }, [auth, navigate])

  const load = useCallback(async () => {
    if (!auth) return
    setLoading(true)
    setError(null)
    try {
      const data = await getBookmarks()
      setArticles(data.bookmarks || [])
    } catch {
      setError('Could not load bookmarks. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }, [auth])

  useEffect(() => { load() }, [load])

  const handleUnbookmark = (articleId) => {
    setArticles(prev => prev.filter(a => a._id !== articleId))
  }

  if (!auth) return null

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">

      {/* Header */}
      <div className="mb-8 animate-fade-in">
        <div className={`flex items-center gap-2 font-semibold text-sm mb-2 text-primary-500`}>
          <Bookmark size={16} className="fill-primary-500" /> Bookmarks
        </div>
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className={`text-2xl sm:text-3xl font-extrabold tracking-tight mb-1 ${dark ? 'text-slate-100' : 'text-slate-800'}`}>
              Saved Articles
            </h1>
            <p className={`text-sm ${dark ? 'text-slate-400' : 'text-slate-500'}`}>
              {loading ? 'Loading…' : `${articles.length} article${articles.length !== 1 ? 's' : ''} saved`}
            </p>
          </div>
          <button
            onClick={load}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all
              ${dark
                ? 'border-slate-700 text-slate-400 hover:border-primary-500/50 hover:text-primary-400 hover:bg-primary-500/5'
                : 'border-slate-200 text-slate-500 hover:border-primary-400 hover:text-primary-500 hover:bg-primary-50'}`}
          >
            <RefreshCw size={13} /> Refresh
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-3 bg-red-500/10 border border-red-500/30 rounded-2xl px-5 py-4 mb-6 text-red-400 text-sm animate-fade-in">
          <AlertTriangle size={18} className="shrink-0" />{error}
          <button onClick={load} className="ml-auto btn-ghost text-red-400">
            <RefreshCw size={14} /> Retry
          </button>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex justify-center py-20">
          <Loader2 size={32} className="text-primary-500 animate-spin" />
        </div>
      )}

      {/* Article grid */}
      {!loading && articles.length > 0 && (
        <>
          {/* Bookmark cards with saved-at info */}
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {articles.map(article => (
              <div key={article._id} className="relative">
                {/* Saved time badge */}
                {article.savedAt && (
                  <div className={`absolute -top-2 left-4 z-10 flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium border
                    ${dark
                      ? 'bg-slate-900 border-primary-500/30 text-primary-400'
                      : 'bg-white border-primary-200 text-primary-600'}`}>
                    <Bookmark size={9} className="fill-current" />
                    Saved {timeAgo(article.savedAt)}
                  </div>
                )}
                <div className="mt-2">
                  <NewsCard
                    article={article}
                    bookmarkId={article.bookmarkId}
                    onUnbookmark={handleUnbookmark}
                  />
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Empty state */}
      {!loading && articles.length === 0 && !error && (
        <div className={`rounded-2xl p-16 text-center border animate-fade-in
          ${dark ? 'glass text-slate-500 border-slate-800' : 'bg-white border-slate-200 text-slate-400 shadow-sm'}`}>
          <Bookmark size={52} className="mx-auto mb-4 opacity-20" />
          <p className={`text-xl font-bold mb-2 ${dark ? 'text-slate-300' : 'text-slate-600'}`}>
            No bookmarks yet
          </p>
          <p className={`text-sm mb-6 max-w-sm mx-auto ${dark ? 'text-slate-500' : 'text-slate-400'}`}>
            Tap the <Bookmark className="inline-block mx-1" size={14} /> icon on any article to save it here for later.
          </p>
          <Link
            to="/news"
            className={`inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold transition-all
              bg-primary-500 text-white hover:bg-primary-600 shadow-md shadow-primary-500/25`}
          >
            <Newspaper size={16} /> Browse News Feed
          </Link>
        </div>
      )}
    </div>
  )
}
