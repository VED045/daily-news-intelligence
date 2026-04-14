import React from 'react'

const CATEGORIES = [
  { id: 'all', label: 'All' },
  { id: 'general', label: 'General' },
  { id: 'world', label: 'World' },
  { id: 'india', label: 'India' },
  { id: 'politics', label: 'Politics' },
  { id: 'geopolitics', label: 'Geopolitics' },
  { id: 'business', label: 'Business' },
  { id: 'sports', label: 'Sports' },
  { id: 'technology', label: 'Technology' },
  { id: 'health', label: 'Health' },
  { id: 'science', label: 'Science' },
  { id: 'entertainment', label: 'Entertainment' },
]

export default function CategoryFilter({ active, onChange }) {
  return (
    <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none">
      {CATEGORIES.map(cat => (
        <button
          key={cat.id}
          onClick={() => onChange(cat.id)}
          className={`shrink-0 px-4 py-1.5 rounded-full text-sm font-medium transition-all duration-200
            ${active === cat.id
              ? 'bg-primary-500 text-white shadow-lg shadow-primary-500/25'
              : 'bg-slate-800/80 text-slate-400 hover:bg-slate-700 hover:text-slate-200 border border-slate-700/50'
            }`}
        >
          {cat.label}
        </button>
      ))}
    </div>
  )
}
