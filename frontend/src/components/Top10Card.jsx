import React from 'react'
import { ExternalLink, AlertCircle, TrendingUp } from 'lucide-react'

const RANK_STYLES = [
  'from-amber-500 to-orange-500 shadow-amber-500/30',    // #1
  'from-slate-400 to-slate-500 shadow-slate-400/20',     // #2
  'from-amber-700 to-amber-800 shadow-amber-700/20',      // #3
  'from-primary-500 to-primary-600 shadow-primary-500/20', // #4
  'from-primary-500 to-primary-600 shadow-primary-500/20', // #5
]

export default function Top10Card({ item }) {
  const rankStyle = RANK_STYLES[(item.rank || 1) - 1] || RANK_STYLES[4]

  return (
    <article className="glass rounded-2xl p-6 flex flex-col gap-4 hover:border-primary-500/30 hover:shadow-xl hover:shadow-primary-500/10 transition-all duration-300 animate-slide-up">

      {/* Rank + Source row */}
      <div className="flex items-center justify-between">
        <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${rankStyle} flex items-center justify-center shadow-lg text-white font-bold text-lg shrink-0`}>
          {item.rank}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500 font-medium">{item.source}</span>
          <span className="text-[10px] px-2 py-0.5 rounded-full border border-slate-700 text-slate-500 uppercase tracking-wide">
            {item.category}
          </span>
        </div>
      </div>

      {/* AI Title */}
      <h2 className="text-slate-100 font-bold text-base leading-snug">
        {item.ai_title || item.title}
      </h2>

      {/* Summary */}
      <p className="text-slate-400 text-sm leading-relaxed">
        {item.summary}
      </p>

      {/* Why important */}
      {item.importance_reason && (
        <div className="flex gap-2.5 bg-primary-500/8 border border-primary-500/20 rounded-xl px-4 py-3">
          <TrendingUp size={15} className="text-primary-400 shrink-0 mt-0.5" />
          <p className="text-primary-300 text-xs leading-relaxed font-medium">
            {item.importance_reason}
          </p>
        </div>
      )}

      {/* Keywords */}
      {item.keywords?.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {item.keywords.map(kw => (
            <span key={kw} className="text-[11px] px-2 py-0.5 rounded-md bg-slate-800 text-slate-500 border border-slate-700/40">
              #{kw}
            </span>
          ))}
        </div>
      )}

      {/* Link */}
      <a
        href={item.url}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-1.5 text-primary-400 text-xs font-semibold hover:text-primary-300 transition-colors w-fit mt-auto"
      >
        Read full story <ExternalLink size={12} />
      </a>
    </article>
  )
}
