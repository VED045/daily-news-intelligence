import React, { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useTheme, APP_NAME } from '../App'
import {
  Newspaper, BarChart3, Star, Mail,
  Sun, Moon, Menu, X, Zap, RefreshCw
} from 'lucide-react'
import { triggerPipeline } from '../services/api'
import toast from 'react-hot-toast'

const NAV_LINKS = [
  { to: '/',          label: 'Dashboard',  icon: Star },
  { to: '/news',      label: 'News Feed',  icon: Newspaper },
  { to: '/trends',    label: 'Trends',     icon: BarChart3 },
  { to: '/subscribe', label: 'Subscribe',  icon: Mail },
]

export default function Navbar() {
  const { dark, toggle } = useTheme()
  const { pathname } = useLocation()
  const [open, setOpen] = useState(false)
  const [running, setRunning] = useState(false)

  const bgClass = dark
    ? 'bg-slate-950/80 border-slate-800/60 backdrop-blur-md'
    : 'bg-white/90 border-slate-200 backdrop-blur-md shadow-sm'

  const linkActive   = dark ? 'bg-primary-500/15 text-primary-400' : 'bg-primary-50 text-primary-600'
  const linkInactive = dark ? 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60' : 'text-slate-500 hover:text-slate-800 hover:bg-slate-100'

  const handleTrigger = async () => {
    setRunning(true)
    try {
      await triggerPipeline()
      toast.success('Pipeline triggered! Check back in ~2 minutes.')
    } catch {
      toast.error('Could not reach the backend.')
    } finally {
      setTimeout(() => setRunning(false), 3500)
    }
  }

  return (
    <nav className={`fixed top-0 left-0 right-0 z-50 border-b ${bgClass}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">

        {/* Logo */}
        <Link to="/" className="flex items-center gap-2.5 group shrink-0">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 via-orange-400 to-amber-500 flex items-center justify-center shadow-lg shadow-primary-500/30 group-hover:shadow-primary-500/50 transition-shadow">
            <Zap size={15} className="text-white" />
          </div>
          <span className="font-extrabold text-base tracking-tight">
            <span className="text-primary-500">Dainik</span>
            <span className={dark ? 'text-slate-100' : 'text-slate-800'}>-Vidya</span>
          </span>
        </Link>

        {/* Desktop links */}
        <div className="hidden md:flex items-center gap-0.5">
          {NAV_LINKS.map(({ to, label, icon: Icon }) => (
            <Link
              key={to}
              to={to}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all duration-200
                ${pathname === to ? linkActive : linkInactive}`}
            >
              <Icon size={15} />{label}
            </Link>
          ))}
        </div>

        {/* Right controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleTrigger}
            disabled={running}
            title="Trigger news pipeline manually"
            className={`hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all
              ${running
                ? 'border-primary-500/40 text-primary-400 bg-primary-500/10 cursor-not-allowed'
                : dark
                  ? 'border-slate-700 text-slate-400 hover:border-primary-500/50 hover:text-primary-400 hover:bg-primary-500/5'
                  : 'border-slate-200 text-slate-500 hover:border-primary-400 hover:text-primary-500 hover:bg-primary-50'
              }`}
          >
            <RefreshCw size={13} className={running ? 'animate-spin' : ''} />
            {running ? 'Running…' : 'Run Pipeline'}
          </button>

          <button
            onClick={toggle}
            className={`w-9 h-9 flex items-center justify-center rounded-lg transition-all
              ${dark ? 'text-slate-400 hover:text-yellow-300 hover:bg-slate-800' : 'text-slate-500 hover:text-primary-600 hover:bg-slate-100'}`}
            title="Toggle theme"
          >
            {dark ? <Sun size={18} /> : <Moon size={18} />}
          </button>

          <button
            onClick={() => setOpen(o => !o)}
            className={`md:hidden w-9 h-9 flex items-center justify-center rounded-lg transition-all
              ${dark ? 'text-slate-400 hover:bg-slate-800' : 'text-slate-500 hover:bg-slate-100'}`}
          >
            {open ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {open && (
        <div className={`md:hidden border-t px-4 py-3 flex flex-col gap-1 animate-fade-in
          ${dark ? 'border-slate-800 bg-slate-950/95' : 'border-slate-200 bg-white/95'}`}>
          {NAV_LINKS.map(({ to, label, icon: Icon }) => (
            <Link
              key={to} to={to}
              onClick={() => setOpen(false)}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all
                ${pathname === to ? linkActive : linkInactive}`}
            >
              <Icon size={16} />{label}
            </Link>
          ))}
          <button onClick={handleTrigger} className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium ${linkInactive}`}>
            <RefreshCw size={16} />Run Pipeline
          </button>
        </div>
      )}
    </nav>
  )
}
