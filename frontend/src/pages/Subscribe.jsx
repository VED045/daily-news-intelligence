import React, { useState } from 'react'
import { Mail, CheckCircle, XCircle, Loader2, Zap, Clock, Star } from 'lucide-react'
import { subscribe, unsubscribe } from '../services/api'
import toast from 'react-hot-toast'

export default function Subscribe() {
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [mode, setMode] = useState('subscribe') // or 'unsubscribe'
  const [status, setStatus] = useState(null) // 'success' | 'error' | null
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!email) return
    setLoading(true)
    setStatus(null)
    try {
      let res
      if (mode === 'subscribe') {
        res = await subscribe(email, name)
      } else {
        res = await unsubscribe(email)
      }
      setMessage(res.message)
      setStatus('success')
      toast.success(res.message)
      if (mode === 'subscribe') { setEmail(''); setName('') }
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Something went wrong. Try again.'
      setMessage(msg)
      setStatus('error')
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-12">

      {/* Header */}
      <div className="text-center mb-10 animate-fade-in">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-500 to-purple-600 shadow-xl shadow-primary-500/30 mb-5">
          <Mail size={28} className="text-white" />
        </div>
        <h1 className="text-3xl font-extrabold text-slate-100 tracking-tight mb-3">
          Daily Email Digest
        </h1>
        <p className="text-slate-400 leading-relaxed">
          Get the Top 10 stories, trending topics, and AI-curated headlines delivered to your inbox every morning at 7:00 AM IST.
        </p>
      </div>

      {/* Feature pills */}
      <div className="flex flex-wrap justify-center gap-3 mb-10 animate-slide-up">
        {[
          { icon: Star, label: 'Top 10 AI Stories' },
          { icon: Zap, label: 'AI Summaries' },
          { icon: Clock, label: 'Daily at 7 AM IST' },
        ].map(({ icon: Icon, label }) => (
          <div key={label} className="flex items-center gap-2 px-4 py-2 rounded-full glass text-sm text-slate-300 border border-slate-700/50">
            <Icon size={14} className="text-primary-400" />
            {label}
          </div>
        ))}
      </div>

      {/* Card */}
      <div className="glass rounded-3xl p-8 animate-slide-up">

        {/* Tab toggle */}
        <div className="flex bg-slate-900/60 rounded-xl p-1 mb-7 border border-slate-800">
          {['subscribe', 'unsubscribe'].map(m => (
            <button
              key={m}
              onClick={() => { setMode(m); setStatus(null) }}
              className={`flex-1 py-2 rounded-lg text-sm font-semibold capitalize transition-all duration-200
                ${mode === m ? 'bg-primary-500 text-white shadow-lg shadow-primary-500/25' : 'text-slate-400 hover:text-slate-200'}`}
            >
              {m}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {mode === 'subscribe' && (
            <div>
              <label className="block text-slate-400 text-xs font-medium mb-1.5 ml-1">Your name (optional)</label>
              <input
                type="text"
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder="Jane Doe"
                className="input"
              />
            </div>
          )}

          <div>
            <label className="block text-slate-400 text-xs font-medium mb-1.5 ml-1">Email address *</label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              className="input"
            />
          </div>

          {/* Status feedback */}
          {status && (
            <div className={`flex items-center gap-2.5 px-4 py-3 rounded-xl text-sm border
              ${status === 'success'
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                : 'bg-red-500/10 border-red-500/30 text-red-400'}`}>
              {status === 'success' ? <CheckCircle size={16} /> : <XCircle size={16} />}
              {message}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="btn-primary justify-center py-3 text-base rounded-xl mt-1"
          >
            {loading ? (
              <><Loader2 size={18} className="animate-spin" /> Processing...</>
            ) : mode === 'subscribe' ? (
              <><Mail size={18} /> Subscribe Now</>
            ) : (
              <><XCircle size={18} /> Unsubscribe</>
            )}
          </button>
        </form>

        <p className="text-center text-slate-600 text-xs mt-5">
          No spam. Unsubscribe anytime.
        </p>
      </div>

      {/* What to expect */}
      <div className="glass rounded-2xl p-6 mt-6 animate-fade-in">
        <h3 className="text-slate-300 font-semibold text-sm mb-4">What's in each digest?</h3>
        <ul className="flex flex-col gap-2.5 text-sm text-slate-400">
          {[
            '🔥 Top 10 AI-curated stories of the day with importance reasons',
            '📋 5–10 additional headlines from all sources',
            '📊 Trending topics and most-covered category',
            '🔗 Direct links to full articles',
          ].map(item => (
            <li key={item} className="flex items-start gap-2">{item}</li>
          ))}
        </ul>
      </div>
    </div>
  )
}
