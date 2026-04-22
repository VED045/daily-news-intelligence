import React, { useState, useEffect, useRef } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useTheme, APP_NAME, useAuth, useLanguage, useFilters } from '../App'
import {
  Newspaper, BarChart3, Star, Mail, Bookmark,
  Sun, Moon, Menu, X, Zap, RefreshCw, LogOut, LogIn, Settings, Filter, User, ChevronDown
} from 'lucide-react'
import { fetchLatestNews, getNewsSources } from '../services/api'
import toast from 'react-hot-toast'

export default function Navbar() {
  const { dark, toggle } = useTheme()
  const { auth, setAuth } = useAuth()
  const { language, setLanguage } = useLanguage()
  const { dateFilter, setDateFilter, specificDay, setSpecificDay, sourceFilter, setSourceFilter, category, setCategory } = useFilters()
  const { pathname } = useLocation()
  const navigate = useNavigate()

  const [open, setOpen] = useState(false)
  const [running, setRunning] = useState(false)

  // Dropdowns
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)

  const [sources, setSources] = useState([])
  useEffect(() => { getNewsSources().then(d => setSources(d.sources || [])).catch(() => { }) }, [])

  // Auto-close dropdowns on click outside
  const navRef = useRef(null)
  useEffect(() => {
    const handleClick = (e) => {
      if (navRef.current && !navRef.current.contains(e.target)) {
        setFiltersOpen(false)
        setProfileOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  const bgClass = dark
    ? 'bg-slate-950/80 border-slate-800/60 backdrop-blur-md'
    : 'bg-white/90 border-slate-200 backdrop-blur-md shadow-sm'

  const linkActive = dark ? 'bg-primary-500/15 text-primary-400' : 'bg-primary-50 text-primary-600'
  const linkInactive = dark ? 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60' : 'text-slate-500 hover:text-slate-800 hover:bg-slate-100'

  const handleTrigger = async () => {
    setRunning(true)
    try {
      await fetchLatestNews()
      toast.success('Fetching latest news! Check back in ~2 minutes.')
    } catch {
      toast.error('Could not reach the backend.')
    } finally {
      setTimeout(() => setRunning(false), 3500)
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setAuth(null)
    setProfileOpen(false)
    toast.success('Logged out successfully')
  }

  const guardedNav = (actionName, targetPath) => {
    if (auth) {
      navigate(targetPath)
    } else {
      sessionStorage.setItem('redirectAfterLogin', actionName)
      toast('Please log in to continue', { icon: '🔒' })
      navigate('/login')
    }
    setProfileOpen(false)
  }

  const publicLinks = [
    { to: '/', label: 'Dashboard', icon: Star },
    { to: '/news', label: 'News Feed', icon: Newspaper },
    { to: '/trends', label: 'Trends', icon: BarChart3 },
  ]

  const DATE_OPTIONS = [
    { id: 'today', label: 'Today' },
    { id: '3days', label: 'Last 3 Days' },
    { id: '7days', label: 'Last 7 Days' },
  ]

  return (
    <nav ref={navRef} className={`fixed top-0 left-0 right-0 z-50 border-b ${bgClass}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">

        {/* 1. Logo */}
        <Link to="/" className="flex items-center gap-2.5 group shrink-0">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 via-orange-400 to-amber-500 flex items-center justify-center shadow-lg shadow-primary-500/30 group-hover:shadow-primary-500/50 transition-shadow">
            <Zap size={15} className="text-white" />
          </div>
          <span className="font-extrabold text-base tracking-tight hidden sm:block">
            <span className="text-primary-500">Dainik</span>
            <span className={dark ? 'text-slate-100' : 'text-slate-800'}>-Vidya</span>
          </span>
        </Link>

        {/* 2. Main Tabs */}
        <div className="hidden md:flex items-center gap-1 mx-4">
          {publicLinks.map(({ to, label, icon: Icon }) => (
            <Link
              key={to}
              to={to}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200
                ${pathname === to ? linkActive : linkInactive}`}
            >
              <Icon size={15} />{label}
            </Link>
          ))}
          <button
            onClick={() => guardedNav('bookmark', '/bookmarks')}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200
              ${pathname === '/bookmarks' ? linkActive : linkInactive}`}
          >
            <Bookmark size={15} />Bookmarks
          </button>
        </div>

        {/* Right Section */}
        <div className="flex items-center gap-2 relative">

          {/* 3. Filters Dropdown */}
          <div className="relative">
            <button
              onClick={() => { setFiltersOpen(!filtersOpen); setProfileOpen(false) }}
              className={`hidden md:flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200
                ${filtersOpen || sourceFilter || dateFilter !== 'today' || category !== 'all' ? linkActive : linkInactive}`}
            >
              <Filter size={15} /> Filters <ChevronDown size={14} className={`transition-transform ${filtersOpen ? 'rotate-180' : ''}`} />
            </button>
            {filtersOpen && (
              <div className={`absolute top-full right-0 mt-2 w-72 rounded-xl shadow-xl overflow-hidden border p-4 z-50 animate-slide-up
                ${dark ? 'bg-slate-900 border-slate-700' : 'bg-white border-slate-200'}`}>
                <div className="mb-4">
                  <label className={`block text-xs font-semibold mb-2 ${dark ? 'text-slate-400' : 'text-slate-500'}`}>Date Range</label>
                  <div className="flex flex-wrap gap-2">
                    {DATE_OPTIONS.map(opt => (
                      <button
                        key={opt.id}
                        onClick={() => { setDateFilter(opt.id); setSpecificDay('') }}
                        className={`px-2 py-1.5 rounded-lg text-xs font-medium border transition-all ${dateFilter === opt.id
                            ? 'bg-primary-500 text-white border-primary-500'
                            : dark
                              ? 'bg-slate-800 text-slate-400 border-slate-700 hover:border-primary-500/40'
                              : 'bg-white text-slate-500 border-slate-200 hover:border-primary-300'
                          }`}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                  {/* Day-wise specific selector for 7 days */}
                  {dateFilter === '7days' && (
                    <div className="mt-2 flex gap-1.5 overflow-x-auto pb-1" style={{ scrollbarWidth: 'thin' }}>
                      <button onClick={() => setSpecificDay('')} className={`px-2 py-1 rounded text-[10px] font-medium border ${specificDay === '' ? 'bg-slate-600 text-white border-slate-600' : dark ? 'bg-slate-800 text-slate-400 border-slate-700' : 'bg-white text-slate-500 border-slate-200'}`}>All</button>
                      {[...Array(8)].map((_, i) => (
                        <button key={i} onClick={() => setSpecificDay(i.toString())} className={`px-2 py-1 rounded text-[10px] whitespace-nowrap font-medium border ${specificDay === i.toString() ? 'bg-slate-600 text-white border-slate-600' : dark ? 'bg-slate-800 text-slate-400 border-slate-700' : 'bg-white text-slate-500 border-slate-200'}`}>
                          {i === 0 ? 'Today' : i === 1 ? 'Yest' : `-${i}d`}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                <div>
                  <label className={`block text-xs font-semibold mb-2 ${dark ? 'text-slate-400' : 'text-slate-500'}`}>Source</label>
                  <select
                    value={sourceFilter}
                    onChange={(e) => setSourceFilter(e.target.value)}
                    className={`w-full px-3 py-2 rounded-lg text-xs border focus:outline-none mb-2 ${dark ? 'bg-slate-800 text-slate-300 border-slate-700 focus:border-primary-500' : 'bg-slate-50 text-slate-700 border-slate-200 focus:border-primary-400'
                      }`}
                  >
                    <option value="">All Sources</option>
                    {sources.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
              </div>
            )}
          </div>

          {/* 4. Language */}
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className={`cursor-pointer w-[4.5rem] h-9 px-2 flex items-center justify-center rounded-lg transition-all text-xs font-bold uppercase ${dark ? 'bg-slate-800 text-slate-200 border border-slate-700 hover:bg-slate-700' : 'bg-slate-100 text-slate-700 border border-slate-300 hover:bg-slate-200'
              }`}
            title="Language"
          >
            <option value="en">EN</option>
            <option value="hi">HI</option>
            <option value="mr">MR</option>
            <option value="te">TE</option>
          </select>

          <button
            onClick={toggle}
            className={`hidden md:flex w-9 h-9 items-center justify-center rounded-lg transition-all
              ${dark ? 'text-slate-400 hover:text-yellow-300 hover:bg-slate-800' : 'text-slate-500 hover:text-primary-600 hover:bg-slate-100'}`}
            title="Toggle theme"
          >
            {dark ? <Sun size={17} /> : <Moon size={17} />}
          </button>

          {/* 5. User/Profile Menu */}
          <div className="relative hidden md:block">
            <button
              onClick={() => { setProfileOpen(!profileOpen); setFiltersOpen(false) }}
              className={`w-9 h-9 flex items-center justify-center rounded-full transition-all border
                ${auth ? 'border-primary-500 bg-primary-50 text-primary-600 dark:bg-primary-900/30' : 'border-slate-300 border-dashed text-slate-500 hover:bg-slate-100 dark:border-slate-600 dark:hover:bg-slate-800'}`}
              title="Profile"
            >
              <User size={16} />
            </button>
            {profileOpen && (
              <div className={`absolute top-full right-0 mt-2 w-48 rounded-xl shadow-xl overflow-hidden border flex flex-col z-50 animate-slide-up
                ${dark ? 'bg-slate-900 border-slate-700' : 'bg-white border-slate-200'}`}>
                {auth ? (
                  <>
                    <button onClick={() => guardedNav('preferences', '/preferences')} className={`w-full text-left px-4 py-2.5 text-sm flex items-center gap-2 ${dark ? 'text-slate-300 hover:bg-slate-800' : 'text-slate-700 hover:bg-slate-50'}`}><Settings size={15} /> Preferences</button>
                    <button onClick={() => guardedNav('subscribe', '/subscribe')} className={`w-full text-left px-4 py-2.5 text-sm flex items-center gap-2 ${dark ? 'text-slate-300 hover:bg-slate-800' : 'text-slate-700 hover:bg-slate-50'}`}><Mail size={15} /> Subscribe</button>
                    <button onClick={handleTrigger} disabled={running} className={`w-full text-left px-4 py-2.5 text-sm flex items-center gap-2 ${dark ? 'text-primary-400 hover:bg-slate-800' : 'text-primary-600 hover:bg-slate-50'}`}><RefreshCw size={15} className={running ? 'animate-spin' : ''} /> {running ? 'Fetching...' : 'Fetch News'}</button>
                    <div className={`border-t my-1 ${dark ? 'border-slate-800' : 'border-slate-100'}`} />
                    <button onClick={handleLogout} className={`w-full text-left px-4 py-2.5 text-sm flex items-center gap-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20`}><LogOut size={15} /> Logout</button>
                  </>
                ) : (
                  <>
                    <button onClick={handleTrigger} disabled={running} className={`w-full text-left px-4 py-2.5 text-sm flex items-center gap-2 ${dark ? 'text-primary-400 hover:bg-slate-800' : 'text-primary-600 hover:bg-slate-50'}`}><RefreshCw size={15} className={running ? 'animate-spin' : ''} /> {running ? 'Fetching...' : 'Fetch News'}</button>
                    <div className={`border-t my-1 ${dark ? 'border-slate-800' : 'border-slate-100'}`} />
                    <button onClick={() => guardedNav('login', '/login')} className={`w-full text-left px-4 py-2.5 text-sm flex items-center gap-2 ${dark ? 'text-slate-300 hover:bg-slate-800' : 'text-slate-700 hover:bg-slate-50'}`}><LogIn size={15} /> Login</button>
                  </>
                )}
              </div>
            )}
          </div>

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
          {publicLinks.map(({ to, label, icon: Icon }) => (
            <Link
              key={to} to={to}
              onClick={() => setOpen(false)}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all
                ${pathname === to ? linkActive : linkInactive}`}
            >
              <Icon size={16} />{label}
            </Link>
          ))}
          <button onClick={() => { guardedNav('bookmark', '/bookmarks'); setOpen(false) }} className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium ${linkInactive}`}>
            <Bookmark size={16} />Bookmarks
          </button>
          <button onClick={() => { guardedNav('subscribe', '/subscribe'); setOpen(false) }} className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium ${linkInactive}`}>
            <Mail size={16} />Subscribe
          </button>
          {auth && (
            <Link to="/preferences" onClick={() => setOpen(false)} className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium ${linkInactive}`}>
              <Settings size={16} />Preferences
            </Link>
          )}
          <button onClick={handleTrigger} className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium ${linkInactive}`}>
            <RefreshCw size={16} />Fetch Latest News
          </button>
          {auth ? (
            <button onClick={() => { handleLogout(); setOpen(false) }} className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-red-500 hover:bg-red-50 dark:hover:bg-red-900/10`}>
              <LogOut size={16} /> Logout
            </button>
          ) : (
            <Link to="/login" onClick={() => setOpen(false)} className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-primary-500 hover:bg-primary-50 dark:hover:bg-primary-900/10`}>
              <LogIn size={16} /> Login
            </Link>
          )}
        </div>
      )}
    </nav>
  )
}
