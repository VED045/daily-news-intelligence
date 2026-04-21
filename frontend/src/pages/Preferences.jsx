import React, { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Settings, ChevronUp, ChevronDown, Save, Loader2, CheckCircle } from 'lucide-react'
import { getMyPreferences, updateMyPreferences } from '../services/api'
import { useTheme, useAuth } from '../App'
import toast from 'react-hot-toast'

const ALL_TOPICS = [
  { id: 'politics',      label: 'Politics',      emoji: '🏛️' },
  { id: 'geopolitics',   label: 'Geopolitics',   emoji: '🌍' },
  { id: 'business',      label: 'Business',      emoji: '💼' },
  { id: 'finance',       label: 'Finance',       emoji: '💰' },
  { id: 'technology',    label: 'Technology',     emoji: '💻' },
  { id: 'health',        label: 'Health',         emoji: '🏥' },
  { id: 'science',       label: 'Science',        emoji: '🔬' },
  { id: 'world',         label: 'World',          emoji: '🗺️' },
  { id: 'india',         label: 'India',          emoji: '🇮🇳' },
  { id: 'general',       label: 'General',        emoji: '📰' },
  { id: 'entertainment', label: 'Entertainment',  emoji: '🎬' },
  { id: 'sports',        label: 'Sports',         emoji: '⚽' },
]

const TOP_N_OPTIONS = [5, 10, 20]

export default function Preferences() {
  const { dark } = useTheme()
  const { auth } = useAuth()
  const navigate = useNavigate()

  const [selectedTopics, setSelectedTopics] = useState([])
  const [topN, setTopN] = useState(10)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  // Auth guard
  useEffect(() => {
    if (!auth) {
      sessionStorage.setItem('redirectAfterLogin', 'personalize')
      toast('Please log in to set preferences', { icon: '🔒' })
      navigate('/login')
    }
  }, [auth, navigate])

  const loadPrefs = useCallback(async () => {
    if (!auth) return
    setLoading(true)
    try {
      const data = await getMyPreferences()
      setSelectedTopics(data.preferred_topics || [])
      setTopN(data.top_n_preference || 10)
    } catch {
      toast.error('Could not load preferences')
    } finally {
      setLoading(false)
    }
  }, [auth])

  useEffect(() => { loadPrefs() }, [loadPrefs])

  const toggleTopic = (topicId) => {
    setSaved(false)
    setSelectedTopics(prev => {
      if (prev.includes(topicId)) {
        return prev.filter(t => t !== topicId)
      }
      return [...prev, topicId]
    })
  }

  const moveTopic = (index, direction) => {
    setSaved(false)
    setSelectedTopics(prev => {
      const arr = [...prev]
      const newIndex = index + direction
      if (newIndex < 0 || newIndex >= arr.length) return arr
      ;[arr[index], arr[newIndex]] = [arr[newIndex], arr[index]]
      return arr
    })
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await updateMyPreferences({
        preferred_topics: selectedTopics,
        top_n_preference: topN,
      })
      toast.success('Preferences saved!')
      setSaved(true)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  if (!auth) return null

  const cardClass = dark
    ? 'glass rounded-2xl p-6'
    : 'bg-white rounded-2xl p-6 border border-slate-200 shadow-sm'

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
      {/* Header */}
      <div className="mb-8 animate-fade-in">
        <div className="flex items-center gap-2 font-semibold text-sm mb-2 text-primary-500">
          <Settings size={16} /> Preferences
        </div>
        <h1 className={`text-2xl sm:text-3xl font-extrabold tracking-tight mb-2 ${dark ? 'text-slate-100' : 'text-slate-800'}`}>
          Personalize Your Feed
        </h1>
        <p className={`text-sm ${dark ? 'text-slate-400' : 'text-slate-500'}`}>
          Select and order topics by priority. Your feed will show these first.
        </p>
      </div>

      {loading ? (
        <div className="flex justify-center py-20">
          <Loader2 size={32} className="text-primary-500 animate-spin" />
        </div>
      ) : (
        <div className="flex flex-col gap-6 animate-slide-up">

          {/* Top N selector */}
          <div className={cardClass}>
            <h2 className={`font-semibold text-sm mb-4 ${dark ? 'text-slate-200' : 'text-slate-700'}`}>
              🏆 Top N Articles on Dashboard
            </h2>
            <p className={`text-xs mb-4 ${dark ? 'text-slate-500' : 'text-slate-400'}`}>
              Choose how many top stories to show on the dashboard.
            </p>
            <div className="flex gap-3">
              {TOP_N_OPTIONS.map(n => (
                <button
                  key={n}
                  onClick={() => { setTopN(n); setSaved(false) }}
                  className={`flex-1 py-3 rounded-xl text-sm font-bold transition-all duration-200 border
                    ${topN === n
                      ? 'bg-primary-500 text-white border-primary-500 shadow-lg shadow-primary-500/25'
                      : dark
                        ? 'bg-slate-800 text-slate-400 border-slate-700 hover:border-primary-500/50 hover:text-primary-400'
                        : 'bg-slate-50 text-slate-500 border-slate-200 hover:border-primary-300 hover:text-primary-600'
                    }`}
                >
                  Top {n}
                </button>
              ))}
            </div>
          </div>

          {/* Topic selection */}
          <div className={cardClass}>
            <h2 className={`font-semibold text-sm mb-2 ${dark ? 'text-slate-200' : 'text-slate-700'}`}>
              🎯 Preferred Topics
            </h2>
            <p className={`text-xs mb-4 ${dark ? 'text-slate-500' : 'text-slate-400'}`}>
              Click to select topics. Use arrows to reorder your priorities (first = highest priority).
            </p>

            {/* Available topics */}
            <div className="flex flex-wrap gap-2 mb-6">
              {ALL_TOPICS.map(t => {
                const isSelected = selectedTopics.includes(t.id)
                return (
                  <button
                    key={t.id}
                    onClick={() => toggleTopic(t.id)}
                    className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-sm font-medium transition-all duration-200 border
                      ${isSelected
                        ? 'bg-primary-500 text-white border-primary-500 shadow-md shadow-primary-500/20'
                        : dark
                          ? 'bg-slate-800/80 text-slate-400 border-slate-700/50 hover:border-primary-500/40 hover:text-primary-400'
                          : 'bg-white text-slate-500 border-slate-200 hover:border-primary-300 hover:text-primary-600 shadow-sm'
                      }`}
                  >
                    <span>{t.emoji}</span>
                    {t.label}
                    {isSelected && <CheckCircle size={14} className="ml-0.5" />}
                  </button>
                )
              })}
            </div>

            {/* Priority order */}
            {selectedTopics.length > 0 && (
              <div>
                <h3 className={`text-xs font-semibold mb-3 uppercase tracking-wide ${dark ? 'text-slate-500' : 'text-slate-400'}`}>
                  Priority Order (drag to reorder)
                </h3>
                <div className="flex flex-col gap-1.5">
                  {selectedTopics.map((topicId, idx) => {
                    const t = ALL_TOPICS.find(a => a.id === topicId)
                    if (!t) return null
                    return (
                      <div key={topicId} className={`flex items-center gap-3 px-4 py-2.5 rounded-xl transition-all ${
                        dark ? 'bg-slate-800/50 border border-slate-700/30' : 'bg-slate-50 border border-slate-100'
                      }`}>
                        <span className={`text-xs font-bold w-5 text-center ${dark ? 'text-primary-400' : 'text-primary-500'}`}>
                          {idx + 1}
                        </span>
                        <span className="text-sm">{t.emoji}</span>
                        <span className={`text-sm font-medium flex-1 ${dark ? 'text-slate-200' : 'text-slate-700'}`}>
                          {t.label}
                        </span>
                        <div className="flex gap-1">
                          <button
                            onClick={() => moveTopic(idx, -1)}
                            disabled={idx === 0}
                            className={`p-1 rounded-md transition-colors disabled:opacity-20 ${
                              dark ? 'hover:bg-slate-700 text-slate-400' : 'hover:bg-slate-200 text-slate-500'
                            }`}
                          >
                            <ChevronUp size={16} />
                          </button>
                          <button
                            onClick={() => moveTopic(idx, 1)}
                            disabled={idx === selectedTopics.length - 1}
                            className={`p-1 rounded-md transition-colors disabled:opacity-20 ${
                              dark ? 'hover:bg-slate-700 text-slate-400' : 'hover:bg-slate-200 text-slate-500'
                            }`}
                          >
                            <ChevronDown size={16} />
                          </button>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Save button */}
          <button
            onClick={handleSave}
            disabled={saving}
            className={`w-full py-3.5 rounded-xl text-sm font-bold transition-all duration-200 flex items-center justify-center gap-2
              ${saved
                ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/25'
                : 'bg-primary-600 hover:bg-primary-500 text-white shadow-lg shadow-primary-500/25 cursor-pointer'
              }`}
          >
            {saving ? (
              <><Loader2 size={16} className="animate-spin" /> Saving...</>
            ) : saved ? (
              <><CheckCircle size={16} /> Saved!</>
            ) : (
              <><Save size={16} /> Save Preferences</>
            )}
          </button>
        </div>
      )}
    </div>
  )
}
