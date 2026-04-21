import React from 'react'
import { useTheme } from '../App'

// Priority order matches backend CATEGORY_PRIORITY
const CATEGORIES = [
  { id: 'all',          label: 'All' },
  { id: 'politics',     label: 'Politics' },
  { id: 'geopolitics',  label: 'Geopolitics' },
  { id: 'business',     label: 'Business' },
  { id: 'finance',      label: 'Finance' },
  { id: 'technology',   label: 'Technology' },
  { id: 'health',       label: 'Health' },
  { id: 'science',      label: 'Science' },
  { id: 'world',        label: 'World' },
  { id: 'india',        label: 'India' },
  { id: 'general',      label: 'General' },
  { id: 'entertainment',label: 'Entertainment' },
  { id: 'sports',       label: 'Sports' },
]

export default function CategoryFilter({ active, onChange, counts }) {
  const { dark } = useTheme()

  // If counts provided, filter out categories with 0 articles (except "all")
  const visibleCategories = counts
    ? CATEGORIES.filter(cat => cat.id === 'all' || (counts[cat.id] && counts[cat.id] > 0))
    : CATEGORIES

  return (
    <div className="flex items-center gap-2 overflow-x-auto pb-2" style={{ scrollbarWidth: 'none' }}>
      {visibleCategories.map(cat => {
        const isActive = active === cat.id
        const count = counts?.[cat.id]
        return (
          <button
            key={cat.id}
            onClick={() => onChange(cat.id)}
            className={`shrink-0 px-4 py-1.5 rounded-full text-sm font-medium transition-all duration-200
              ${isActive
                ? 'bg-primary-500 text-white shadow-lg shadow-primary-500/25'
                : dark
                  ? 'bg-slate-800/80 text-slate-400 hover:bg-slate-700 hover:text-slate-200 border border-slate-700/50'
                  : 'bg-white text-slate-500 hover:bg-primary-50 hover:text-primary-600 border border-slate-200 shadow-sm'
              }`}
          >
            {cat.label}
            {count !== undefined && cat.id !== 'all' && (
              <span className={`ml-1.5 text-xs ${isActive ? 'opacity-80' : 'opacity-50'}`}>
                {count}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}
