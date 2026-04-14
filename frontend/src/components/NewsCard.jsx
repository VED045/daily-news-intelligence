import React, { useState } from 'react'
import { ExternalLink, Bookmark, BookmarkCheck, Tag, Clock } from 'lucide-react'
import { useTheme } from '../App'

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

export default function NewsCard({ article, onKeywordClick }) {
  const { dark } = useTheme()
  const [bookmarked, setBookmarked] = useState(() => {
    const saved = JSON.parse(localStorage.getItem('dv-bookmarks') || '[]')
    return saved.includes(article._id || article.url)
  })

  const toggleBookmark = (e) => {
    e.preventDefault()
    const key = article._id || article.url
    const saved = JSON.parse(localStorage.getItem('dv-bookmarks') || '[]')
    const updated = bookmarked ? saved.filter(id => id !== key) : [...saved, key]
    localStorage.setItem('dv-bookmarks', JSON.stringify(updated))
    setBookmarked(!bookmarked)
  }

  const catDef = CATEGORY_COLORS[article.category] || CATEGORY_COLORS.general
  const catColor = dark ? catDef.dark : catDef.light
  const displayTitle = article.ai_title || article.title
  const displaySummary = article.ai_summary || article.summary
  const timeLabel = formatTime(article.published_at)

  // Card styles for light/dark
  const cardBase = dark
    ? 'glass rounded-2xl p-5 flex flex-col gap-3 hover:border-primary-500/25 hover:shadow-primary-500/10 hover:shadow-lg transition-all duration-300 animate-fade-in group'
    : 'bg-white rounded-2xl p-5 flex flex-col gap-3 border border-slate-200 hover:border-primary-300 hover:shadow-lg hover:shadow-primary-500/8 transition-all duration-300 animate-fade-in group'

  return (
    <article className={cardBase}>

      {/* Header row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`badge ${catColor}`}>
            <Tag size={10} />
            {article.category}
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
            title={bookmarked ? 'Remove bookmark' : 'Bookmark'}
          >
            {bookmarked
              ? <BookmarkCheck size={16} className="text-primary-500" />
              : <Bookmark size={16} className={`${dark ? 'text-slate-600' : 'text-slate-300'} group-hover:text-primary-400 transition-colors`} />}
          </button>
        </div>
      </div>

      {/* Title */}
      <h3 className={`font-semibold text-sm leading-snug line-clamp-2 group-hover:text-primary-500 transition-colors
        ${dark ? 'text-slate-100' : 'text-slate-800'}`}>
        {displayTitle}
      </h3>

      {/* Summary */}
      {displaySummary && (
        <p className={`text-xs leading-relaxed line-clamp-3 ${dark ? 'text-slate-400' : 'text-slate-500'}`}>
          {displaySummary}
        </p>
      )}

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

      {/* Read link */}
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
