import React from 'react'
import { ExternalLink, TrendingUp, AlertCircle } from 'lucide-react'
import { useTheme } from '../App'

const RANK_STYLES = [
  'from-amber-500 to-orange-500 shadow-amber-500/30',    // #1
  'from-slate-400 to-slate-500 shadow-slate-400/20',     // #2
  'from-amber-700 to-amber-800 shadow-amber-700/20',      // #3
  'from-primary-500 to-primary-600 shadow-primary-500/20', // #4
  'from-primary-500 to-primary-600 shadow-primary-500/20', // #5
]

export default function Top10Card({ item }) {
  const { dark } = useTheme()
  const rankStyle = RANK_STYLES[(item.rank || 1) - 1] || RANK_STYLES[4]
  const hasUrl = !!item.url

  const cardContent = (
    <>
      {/* Rank + Source row */}
      <div className="flex items-center justify-between">
        <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${rankStyle} flex items-center justify-center shadow-lg text-white font-bold text-lg shrink-0`}>
          {item.rank}
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-xs font-medium ${dark ? 'text-slate-500' : 'text-slate-400'}`}>{item.source}</span>
          <span className={`text-[10px] px-2 py-0.5 rounded-full border uppercase tracking-wide ${
            dark ? 'border-slate-700 text-slate-500' : 'border-slate-200 text-slate-400'
          }`}>
            {item.category}
          </span>
        </div>
      </div>

      {/* AI Title (original title preserved, AI title shown as display) */}
      <h2 className={`font-bold text-base leading-snug ${dark ? 'text-slate-100' : 'text-slate-800'}`}>
        {item.ai_title || item.title}
      </h2>

      {/* Original title subtitle if AI title exists and differs */}
      {item.ai_title && item.title && item.ai_title !== item.title && (
        <p className={`text-xs italic ${dark ? 'text-slate-500' : 'text-slate-400'}`}>
          Original: {item.title}
        </p>
      )}

      {/* Summary */}
      <p className={`text-sm leading-relaxed ${dark ? 'text-slate-400' : 'text-slate-500'}`}>
        {item.summary}
      </p>

      {/* Why important */}
      {item.importance_reason && (
        <div className={`flex gap-2.5 rounded-xl px-4 py-3 ${
          dark ? 'bg-primary-500/8 border border-primary-500/20' : 'bg-primary-50 border border-primary-100'
        }`}>
          <TrendingUp size={15} className="text-primary-400 shrink-0 mt-0.5" />
          <p className={`text-xs leading-relaxed font-medium ${dark ? 'text-primary-300' : 'text-primary-600'}`}>
            {item.importance_reason}
          </p>
        </div>
      )}

      {/* Keywords */}
      {item.keywords?.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {item.keywords.map(kw => (
            <span key={kw} className={`text-[11px] px-2 py-0.5 rounded-md border ${
              dark ? 'bg-slate-800 text-slate-500 border-slate-700/40' : 'bg-slate-50 text-slate-400 border-slate-200'
            }`}>
              #{kw}
            </span>
          ))}
        </div>
      )}

      {/* Read full article — prominent button */}
      <div className="flex items-center gap-2 mt-auto pt-1">
        {hasUrl ? (
          <span className="flex items-center gap-1.5 text-primary-400 text-xs font-semibold hover:text-primary-300 transition-colors">
            Read full story <ExternalLink size={12} />
          </span>
        ) : (
          <span className={`flex items-center gap-1.5 text-xs ${dark ? 'text-slate-600' : 'text-slate-400'}`}>
            <AlertCircle size={12} /> Source link unavailable
          </span>
        )}
      </div>
    </>
  )

  // Wrap entire card in a link if URL exists
  if (hasUrl) {
    return (
      <a
        href={item.url}
        target="_blank"
        rel="noopener noreferrer"
        className={`block rounded-2xl p-6 flex flex-col gap-4 transition-all duration-300 animate-slide-up cursor-pointer ${
          dark
            ? 'glass hover:border-primary-500/30 hover:shadow-xl hover:shadow-primary-500/10'
            : 'bg-white border border-slate-200 shadow-sm hover:border-primary-300 hover:shadow-lg hover:shadow-primary-500/8'
        }`}
      >
        {cardContent}
      </a>
    )
  }

  return (
    <article className={`rounded-2xl p-6 flex flex-col gap-4 transition-all duration-300 animate-slide-up ${
      dark
        ? 'glass opacity-70'
        : 'bg-white border border-slate-200 shadow-sm opacity-70'
    }`}>
      {cardContent}
    </article>
  )
}
