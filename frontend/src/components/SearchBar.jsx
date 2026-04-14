import React, { useState, useRef, useEffect } from 'react'
import { Search, X } from 'lucide-react'

export default function SearchBar({ onSearch, placeholder = 'Search news...' }) {
  const [value, setValue] = useState('')
  const inputRef = useRef(null)

  const handleSubmit = (e) => {
    e.preventDefault()
    if (value.trim().length >= 2) onSearch(value.trim())
  }

  const handleClear = () => {
    setValue('')
    onSearch('')
    inputRef.current?.focus()
  }

  // Keyboard shortcut: /
  useEffect(() => {
    const handler = (e) => {
      if (e.key === '/' && document.activeElement?.tagName !== 'INPUT') {
        e.preventDefault()
        inputRef.current?.focus()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  return (
    <form onSubmit={handleSubmit} className="relative w-full max-w-xl">
      <div className="relative flex items-center">
        <Search size={16} className="absolute left-3.5 text-slate-500 pointer-events-none" />
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={e => setValue(e.target.value)}
          placeholder={placeholder}
          className="input pl-10 pr-20"
        />
        <div className="absolute right-3 flex items-center gap-2">
          {value && (
            <button type="button" onClick={handleClear} className="text-slate-500 hover:text-slate-300 transition-colors">
              <X size={15} />
            </button>
          )}
          <kbd className="hidden sm:inline-flex items-center text-[10px] text-slate-600 border border-slate-700 rounded px-1.5 py-0.5">/</kbd>
        </div>
      </div>
    </form>
  )
}
