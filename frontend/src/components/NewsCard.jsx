import React, { useState } from 'react'
import { ExternalLink, Bookmark, BookmarkCheck, Tag, Clock } from 'lucide-react'

const CATEGORY_COLORS = {
  general:       'bg-slate-700/60 text-slate-300',
  world:         'bg-blue-500/15 text-blue-400',
  politics:      'bg-red-500/15 text-red-400',
  geopolitics:   'bg-orange-500/15 text-orange-400',
  sports:        'bg-green-500/15 text-green-400',
  business:      'bg-yellow-500/15 text-yellow-400',
  technology:    'bg-cyan-500/15 text-cyan-400',
  science:       'bg-purple-500/15 text-purple-400',
  health:        'bg-emerald-500/15 text-emerald-400',
  entertainment: 'bg-pink-500/15 text-pink-400',
  india:         'bg-amber-500/15 text-amber-400',
  markets:       'bg-teal-500/15 text-teal-400',
}

function timeAgo(iso) {
  if (!iso) return ''
  const diff = Math.floor((Date.now() - new Date(iso)) / 1000)
  if (diff < 60) return `${diff}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

export default function NewsCard({ article }) {
  const [bookmarked, setBookmarked] = useState(() => {
    const saved = JSON.parse(localStorage.getItem('bookmarks') || '[]')
    return saved.includes(article._id || article.url)
  })

  const toggleBookmark = (e) => {
    e.preventDefault()
    const key = article._id || article.url
    const saved = JSON.parse(localStorage.getItem('bookmarks') || '[]')
    const updated = bookmarked ? saved.filter(id => id !== key) : [...saved, key]
    localStorage.setItem('bookmarks', JSON.stringify(updated))
    setBookmarked(!bookmarked)
  }

  const catColor = CATEGORY_COLORS[article.category] || CATEGORY_COLORS.general
  const displayTitle = article.ai_title || article.title
  const displaySummary = article.ai_summary || article.summary

  return (
    <article className="glass rounded-2xl p-5 flex flex-col gap-3 hover:border-primary-500/25 hover:shadow-primary-500/10 hover:shadow-lg transition-all duration-300 animate-fade-in group">

      {/* Header row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`badge ${catColor}`}>
            <Tag size={10} />
            {article.category}
          </span>
          <span className="text-xs text-slate-500 font-medium">{article.source}</span>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          {article.published_at && (
            <span className="flex items-center gap-1 text-xs text-slate-600">
              <Clock size={11} />
              {timeAgo(article.published_at)}
            </span>
          )}
          <button
            onClick={toggleBookmark}
            className="p-1.5 rounded-lg hover:bg-slate-800 transition-colors ml-1"
            title={bookmarked ? 'Remove bookmark' : 'Bookmark'}
          >
            {bookmarked
              ? <BookmarkCheck size={16} className="text-primary-400" />
              : <Bookmark size={16} className="text-slate-600 group-hover:text-slate-400 transition-colors" />}
          </button>
        </div>
      </div>

      {/* Title */}
      <h3 className="text-slate-100 font-semibold text-sm leading-snug line-clamp-2 group-hover:text-primary-300 transition-colors">
        {displayTitle}
      </h3>

      {/* Summary */}
      {displaySummary && (
        <p className="text-slate-400 text-xs leading-relaxed line-clamp-3">
          {displaySummary}
        </p>
      )}

      {/* Keywords */}
      {article.keywords?.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {article.keywords.slice(0, 4).map(kw => (
            <span key={kw} className="text-xs px-2 py-0.5 rounded-md bg-slate-800 text-slate-500 border border-slate-700/50">
              #{kw}
            </span>
          ))}
        </div>
      )}

      {/* Footer */}
      <a
        href={article.url}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-1.5 text-primary-400 text-xs font-semibold mt-auto hover:text-primary-300 transition-colors w-fit"
      >
        Read full article <ExternalLink size={12} />
      </a>
    </article>
  )
}
