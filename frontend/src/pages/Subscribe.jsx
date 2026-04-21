import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Mail, CheckCircle, XCircle, Loader2, Zap, Clock, Star, Bell, BellOff } from 'lucide-react'
import { getMyPreferences, postMySubscribe, postMyUnsubscribe } from '../services/api'
import { useTheme, useAuth } from '../App'
import toast from 'react-hot-toast'

export default function Subscribe() {
  const { dark } = useTheme()
  const { auth } = useAuth()
  const navigate = useNavigate()

  const [isSubscribed, setIsSubscribed] = useState(null) // null = loading
  const [loading, setLoading] = useState(false)
  const [checkingState, setCheckingState] = useState(true)

  // Load subscription state on mount (auth-aware)
  useEffect(() => {
    if (!auth) {
      setCheckingState(false)
      return
    }
    const check = async () => {
      try {
        const prefs = await getMyPreferences()
        setIsSubscribed(prefs.is_subscribed_email)
      } catch {
        setIsSubscribed(true) // default assumption
      } finally {
        setCheckingState(false)
      }
    }
    check()
  }, [auth])

  const handleSubscribe = async () => {
    if (!auth) {
      sessionStorage.setItem('redirectAfterLogin', 'subscribe')
      toast('Please log in to subscribe', { icon: '🔒' })
      navigate('/login')
      return
    }
    setLoading(true)
    try {
      await postMySubscribe()
      setIsSubscribed(true)
      toast.success('Subscribed to daily email digest!')
    } catch {
      toast.error('Could not subscribe. Try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleUnsubscribe = async () => {
    setLoading(true)
    try {
      await postMyUnsubscribe()
      setIsSubscribed(false)
      toast.success('Unsubscribed from email digest.')
    } catch {
      toast.error('Could not unsubscribe. Try again.')
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
        <h1 className={`text-3xl font-extrabold tracking-tight mb-3 ${dark ? 'text-slate-100' : 'text-slate-800'}`}>
          Daily Email Digest
        </h1>
        <p className={`leading-relaxed ${dark ? 'text-slate-400' : 'text-slate-500'}`}>
          Get the Top stories, trending topics, and AI-curated headlines delivered to your inbox every morning at 7:00 AM IST.
        </p>
      </div>

      {/* Feature pills */}
      <div className="flex flex-wrap justify-center gap-3 mb-10 animate-slide-up">
        {[
          { icon: Star, label: 'Top AI Stories' },
          { icon: Zap, label: 'AI Summaries' },
          { icon: Clock, label: 'Daily at 7 AM IST' },
        ].map(({ icon: Icon, label }) => (
          <div key={label} className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm border ${
            dark ? 'glass text-slate-300 border-slate-700/50' : 'bg-white text-slate-600 border-slate-200 shadow-sm'
          }`}>
            <Icon size={14} className="text-primary-400" />
            {label}
          </div>
        ))}
      </div>

      {/* Main card */}
      <div className={`rounded-3xl p-8 animate-slide-up ${dark ? 'glass' : 'bg-white border border-slate-200 shadow-sm'}`}>

        {checkingState ? (
          <div className="flex justify-center py-8">
            <Loader2 size={24} className="text-primary-500 animate-spin" />
          </div>
        ) : auth && isSubscribed ? (
          /* Logged in + Subscribed */
          <div className="text-center">
            <div className={`inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-semibold mb-6 ${
              dark ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30' : 'bg-emerald-50 text-emerald-600 border border-emerald-200'
            }`}>
              <CheckCircle size={16} /> Subscribed
            </div>

            {/* Notice */}
            <div className={`rounded-xl px-5 py-4 mb-6 text-sm border ${
              dark ? 'bg-slate-800/50 border-slate-700/50 text-slate-300' : 'bg-blue-50 border-blue-100 text-blue-700'
            }`}>
              <p className="flex items-center gap-2 justify-center">
                <Bell size={14} className="shrink-0" />
                You are subscribed to daily news emails. You can unsubscribe anytime.
              </p>
            </div>

            <p className={`text-sm mb-6 ${dark ? 'text-slate-400' : 'text-slate-500'}`}>
              We'll send the top stories to <strong className="text-primary-500">{auth.email}</strong> every morning.
            </p>

            <button
              onClick={handleUnsubscribe}
              disabled={loading}
              className={`inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold transition-all border ${
                dark
                  ? 'border-red-900/50 text-red-400 hover:bg-red-900/20'
                  : 'border-red-200 text-red-500 hover:bg-red-50'
              }`}
            >
              {loading ? <Loader2 size={16} className="animate-spin" /> : <BellOff size={16} />}
              {loading ? 'Processing...' : 'Unsubscribe'}
            </button>
          </div>

        ) : auth && isSubscribed === false ? (
          /* Logged in + NOT subscribed */
          <div className="text-center">
            <p className={`text-sm mb-6 ${dark ? 'text-slate-400' : 'text-slate-500'}`}>
              You are not currently subscribed. Get daily AI-curated news to <strong className="text-primary-500">{auth.email}</strong>.
            </p>

            <button
              onClick={handleSubscribe}
              disabled={loading}
              className="inline-flex items-center gap-2 px-8 py-3.5 rounded-xl text-sm font-bold bg-primary-600 hover:bg-primary-500 text-white shadow-lg shadow-primary-500/25 transition-all cursor-pointer"
            >
              {loading ? <Loader2 size={16} className="animate-spin" /> : <Mail size={16} />}
              {loading ? 'Subscribing...' : 'Subscribe Now'}
            </button>
          </div>

        ) : (
          /* Guest */
          <div className="text-center">
            <p className={`text-sm mb-6 ${dark ? 'text-slate-400' : 'text-slate-500'}`}>
              Log in or create an account to subscribe to the daily email digest.
            </p>
            <button
              onClick={handleSubscribe}
              className="inline-flex items-center gap-2 px-8 py-3.5 rounded-xl text-sm font-bold bg-primary-600 hover:bg-primary-500 text-white shadow-lg shadow-primary-500/25 transition-all cursor-pointer"
            >
              <Mail size={16} /> Subscribe Now
            </button>
          </div>
        )}

        <p className={`text-center text-xs mt-6 ${dark ? 'text-slate-600' : 'text-slate-400'}`}>
          No spam. Unsubscribe anytime.
        </p>
      </div>

      {/* What to expect */}
      <div className={`rounded-2xl p-6 mt-6 animate-fade-in ${dark ? 'glass' : 'bg-white border border-slate-200 shadow-sm'}`}>
        <h3 className={`font-semibold text-sm mb-4 ${dark ? 'text-slate-300' : 'text-slate-700'}`}>What's in each digest?</h3>
        <ul className={`flex flex-col gap-2.5 text-sm ${dark ? 'text-slate-400' : 'text-slate-500'}`}>
          {[
            '🔥 Top AI-curated stories of the day with importance reasons',
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
