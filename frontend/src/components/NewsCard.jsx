import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ExternalLink, Bookmark, BookmarkCheck, Tag, Clock, Rss, Globe } from 'lucide-react'
import { useTheme, useAuth } from '../App'
import { addBookmark, removeBookmarkByArticle } from '../services/api'
import toast from 'react-hot-toast'

// ── Priority order: politics first, sports last ──────────────
const CATEGORY_COLORS = {
  politics:      { dark: 'bg-red-500/15 text-red-400',     light: 'bg-red-50 text-red-600 border border-red-200' },
  geopolitics:   { dark: 'bg-orange-500/15 text-orange-400', light: 'bg-orange-50 text-orange-600 border border-orange-200' },
  business:      { dark: 'bg-yellow-500/15 text-yellow-400', light: 'bg-yellow-50 text-yellow-700 border border-yellow-200' },
  finance:       { dark: 'bg-emerald-500/15 text-emerald-400', light: 'bg-emerald-50 text-emerald-700 border border-emerald-200' },
  technology:    { dark: 'bg-cyan-500/15 text-cyan-400',    light: 'bg-cyan-50 text-cyan-700 border border-cyan-200' },
  health:        { dark: 'bg-green-500/15 text-green-400',  light: 'bg-green-50 text-green-700 border border-green-200' },
  science:       { dark: 'bg-purple-500/15 text-purple-400', light: 'bg-purple-50 text-purple-700 border border-purple-200' },
  world:         { dark: 'bg-blue-500/15 text-blue-400',    light: 'bg-blue-50 text-blue-700 border border-blue-200' },
  india:         { dark: 'bg-amber-500/15 text-amber-400',  light: 'bg-amber-50 text-amber-700 border border-amber-200' },
  general:       { dark: 'bg-slate-700/60 text-slate-300',  light: 'bg-slate-100 text-slate-600 border border-slate-200' },
  entertainment: { dark: 'bg-pink-500/15 text-pink-400',    light: 'bg-pink-50 text-pink-700 border border-pink-200' },
  sports:        { dark: 'bg-lime-500/15 text-lime-400',    light: 'bg-lime-50 text-lime-700 border border-lime-200' },
  markets:       { dark: 'bg-teal-500/15 text-teal-400',    light: 'bg-teal-50 text-teal-700 border border-teal-200' },
}

/**
 * Robust timestamp display.
 * - Handles ISO strings with or without timezone suffix
 * - Shows "X min ago" for recent, "HH:MM, DD MMM" for older
 */
function formatTime(isoString) {
  if (!isoString) return ''

  // Ensure the string is treated as UTC if no timezone info present
  let str = isoString.trim()
  if (!str.endsWith('Z') && !str.includes('+') && !/[+-]\d{2}:\d{2}$/.test(str)) {
    str += 'Z'
  }

  const date = new Date(str)
  if (isNaN(date.getTime())) return ''

  const diffMs = Date.now() - date.getTime()
  const diffSec = Math.floor(diffMs / 1000)

  if (diffSec < 0)     return 'just now'          // future date guard
  if (diffSec < 60)    return `${diffSec}s ago`
  if (diffSec < 3600)  return `${Math.floor(diffSec / 60)}m ago`
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`
  if (diffSec < 604800) return `${Math.floor(diffSec / 86400)}d ago`

  // Older than a week — show "HH:MM, DD Mon"
  return date.toLocaleString(undefined, {
    hour: '2-digit', minute: '2-digit',
    day: '2-digit', month: 'short',
    hour12: false,
  })
}

export default function NewsCard({ article, onKeywordClick, bookmarkId: initialBookmarkId, onUnbookmark }) {
  const { dark } = useTheme()
  const { auth } = useAuth()
  const navigate = useNavigate()

  const [bookmarked, setBookmarked] = useState(() => {
    if (initialBookmarkId) return true
    if (!auth) return false
    const saved = JSON.parse(localStorage.getItem('dv-bookmarks') || '{}')
    return !!saved[article._id || article.url]
  })
  const [bmId, setBmId] = useState(initialBookmarkId || null)

  // Sync local storage bookmark map on mount
  useEffect(() => {
    if (!auth) { setBookmarked(false); return }
    const saved = JSON.parse(localStorage.getItem('dv-bookmarks') || '{}')
    const key = article._id || article.url
    if (saved[key]) {
      setBookmarked(true)
      setBmId(saved[key])
    }
  }, [article._id, article.url, auth])

  const toggleBookmark = async (e) => {
    e.preventDefault()

    // Auth guard — redirect guests to login
    if (!auth) {
      sessionStorage.setItem('redirectAfterLogin', 'bookmark')
      sessionStorage.setItem('pendingBookmarkId', article._id)
      toast('Please log in to bookmark articles', { icon: '🔒' })
      navigate('/login')
      return
    }

    const key = article._id || article.url

    if (bookmarked) {
      // Remove
      try {
        await removeBookmarkByArticle(article._id)
        const saved = JSON.parse(localStorage.getItem('dv-bookmarks') || '{}')
        delete saved[key]
        localStorage.setItem('dv-bookmarks', JSON.stringify(saved))
        setBookmarked(false)
        setBmId(null)
        toast.success('Bookmark removed')
        onUnbookmark?.(article._id)
      } catch {
        // Fallback: just remove from localStorage
        const saved = JSON.parse(localStorage.getItem('dv-bookmarks') || '{}')
        delete saved[key]
        localStorage.setItem('dv-bookmarks', JSON.stringify(saved))
        setBookmarked(false)
        toast('Bookmark removed (offline)')
      }
    } else {
      // Add
      try {
        const res = await addBookmark(article._id)
        const saved = JSON.parse(localStorage.getItem('dv-bookmarks') || '{}')
        saved[key] = res.id || true
        localStorage.setItem('dv-bookmarks', JSON.stringify(saved))
        setBmId(res.id)
        setBookmarked(true)
        toast.success('Article bookmarked!')
      } catch {
        toast.error('Could not bookmark — try again')
      }
    }
  }

  const catDef = CATEGORY_COLORS[article.category] || CATEGORY_COLORS.general
  const catColor = dark ? catDef.dark : catDef.light
  const displayTitle = article.ai_title || article.title
  const displaySummary = article.ai_summary || article.summary
  const contentPreview = article.contentPreview || article.content_preview || ''
  const timeLabel = formatTime(article.published_at || article.publishedAt)
  const sourceType = article.sourceType || (article.source_type === 'newsapi' ? 'News API' : 'Scraped')

  // Card styles for light/dark
  const cardBase = dark
    ? 'glass rounded-2xl p-5 flex flex-col gap-3 hover:border-primary-500/25 hover:shadow-primary-500/10 hover:shadow-lg transition-all duration-300 animate-fade-in group'
    : 'bg-white rounded-2xl p-5 flex flex-col gap-3 border border-slate-200 hover:border-primary-300 hover:shadow-lg hover:shadow-primary-500/8 transition-all duration-300 animate-fade-in group'

  return (
    <article className={cardBase}>

      {/* Header row: category + source type + time + bookmark */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`badge ${catColor}`}>
            <Tag size={10} />
            {article.category}
          </span>
          {/* Source type badge */}
          <span className={`flex items-center gap-1 text-xs px-2 py-0.5 rounded-md font-medium
            ${sourceType === 'News API'
              ? (dark ? 'bg-blue-500/15 text-blue-400' : 'bg-blue-50 text-blue-600 border border-blue-200')
              : (dark ? 'bg-emerald-500/15 text-emerald-400' : 'bg-emerald-50 text-emerald-700 border border-emerald-200')
            }`}>
            {sourceType === 'News API' ? <Globe size={10} /> : <Rss size={10} />}
            {sourceType}
          </span>
          <span className={`text-xs font-medium ${dark ? 'text-slate-500' : 'text-slate-400'}`}>
            {article.source}
          </span>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          {timeLabel && (
            <span className={`flex items-center gap-1 text-xs ${dark ? 'text-slate-600' : 'text-slate-400'}`}>
              <Clock size={11} />{timeLabel}
            </span>
          )}
          <button
            onClick={toggleBookmark}
            className={`p-1.5 rounded-lg transition-colors ml-1 ${dark ? 'hover:bg-slate-800' : 'hover:bg-slate-100'}`}
            title={!auth ? 'Log in to bookmark' : bookmarked ? 'Remove bookmark' : 'Bookmark this article'}
          >
            {bookmarked
              ? <BookmarkCheck size={16} className="text-primary-500" />
              : <Bookmark size={16} className={`${dark ? 'text-slate-600' : 'text-slate-300'} group-hover:text-primary-400 transition-colors`} />}
          </button>
        </div>
      </div>

      {/* Title — clickable link (always shows original title) */}
      <h3 className={`font-semibold text-sm leading-snug line-clamp-2 transition-colors
        ${dark ? 'text-slate-100' : 'text-slate-800'}`}>
        <a
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
          className="hover:text-primary-500 transition-colors"
        >
          {displayTitle}
        </a>
      </h3>

      {/* Content preview (5-6 lines from article body) */}
      {contentPreview ? (
        <p className={`text-xs leading-relaxed line-clamp-4 ${dark ? 'text-slate-400' : 'text-slate-500'}`}>
          {contentPreview}
        </p>
      ) : displaySummary ? (
        <p className={`text-xs leading-relaxed line-clamp-3 ${dark ? 'text-slate-400' : 'text-slate-500'}`}>
          {displaySummary}
        </p>
      ) : null}

      {/* Keywords — clickable */}
      {article.keywords?.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {article.keywords.slice(0, 4).map(kw => (
            <button
              key={kw}
              onClick={() => onKeywordClick?.(kw)}
              className={`text-xs px-2 py-0.5 rounded-md border transition-colors
                ${dark
                  ? 'bg-slate-800 text-slate-500 border-slate-700/50 hover:text-primary-400 hover:border-primary-500/40'
                  : 'bg-slate-50 text-slate-400 border-slate-200 hover:text-primary-600 hover:border-primary-300'}`}
            >
              #{kw}
            </button>
          ))}
        </div>
      )}

      {/* Read full article link */}
      <a
        href={article.url}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-1.5 text-primary-500 text-xs font-semibold mt-auto hover:text-primary-600 transition-colors w-fit"
      >
        Read full article <ExternalLink size={12} />
      </a>
    </article>
  )
}
