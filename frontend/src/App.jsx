import React, { createContext, useContext, useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import Navbar from './components/Navbar'
import Dashboard from './pages/Dashboard'
import NewsFeed from './pages/NewsFeed'
import Trends from './pages/Trends'
import Subscribe from './pages/Subscribe'
import Bookmarks from './pages/Bookmarks'
import Preferences from './pages/Preferences'
import Login from './pages/Login'
import Signup from './pages/Signup'

export const ThemeContext = createContext({ dark: true, toggle: () => {} })
export const useTheme = () => useContext(ThemeContext)

export const AuthContext = createContext({ auth: null, setAuth: () => {} })
export const useAuth = () => useContext(AuthContext)

export const LanguageContext = createContext({ language: 'en', setLanguage: () => {} })
export const useLanguage = () => useContext(LanguageContext)

export const FilterContext = createContext({
  dateFilter: 'today', setDateFilter: () => {},
  specificDay: '', setSpecificDay: () => {},
  sourceFilter: '', setSourceFilter: () => {},
  category: 'all', setCategory: () => {}
})
export const useFilters = () => useContext(FilterContext)

export const APP_NAME = 'Dainik-Vidya'
export const APP_TAGLINE = 'AI-Powered News Intelligence'

export default function App() {
  const [dark, setDark] = useState(() => localStorage.getItem('dv-theme') !== 'light')
  const [auth, setAuth] = useState(() => {
    try {
      const saved = localStorage.getItem('user')
      return saved ? JSON.parse(saved) : null
    } catch {
      return null
    }
  })
  
  const [language, setLanguage] = useState(() => localStorage.getItem('dv-lang') || 'en')
  
  const [dateFilter, setDateFilter] = useState('today')
  const [specificDay, setSpecificDay] = useState('')
  const [sourceFilter, setSourceFilter] = useState('')
  const [category, setCategory] = useState('all')

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    localStorage.setItem('dv-theme', dark ? 'dark' : 'light')
    document.title = `${APP_NAME} — ${APP_TAGLINE}`
  }, [dark])

  useEffect(() => {
    localStorage.setItem('dv-lang', language)
  }, [language])

  // Listen for token expiry events from api interceptor
  useEffect(() => {
    const handler = () => setAuth(null)
    window.addEventListener('auth-expired', handler)
    return () => window.removeEventListener('auth-expired', handler)
  }, [])

  return (
    <ThemeContext.Provider value={{ dark, toggle: () => setDark(d => !d) }}>
      <AuthContext.Provider value={{ auth, setAuth }}>
        <LanguageContext.Provider value={{ language, setLanguage }}>
          <FilterContext.Provider value={{
            dateFilter, setDateFilter, specificDay, setSpecificDay,
            sourceFilter, setSourceFilter, category, setCategory
          }}>
          <div className={`min-h-screen transition-colors duration-300 ${
          dark ? 'bg-slate-950 text-slate-100' : 'bg-[#F8FAFC] text-[#1F2937]'
        }`}>
          <Router>
            <Navbar />
            <main className="pt-16 min-h-screen">
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/news" element={<NewsFeed />} />
                <Route path="/bookmarks" element={<Bookmarks />} />
                <Route path="/trends" element={<Trends />} />
                <Route path="/subscribe" element={<Subscribe />} />
                <Route path="/preferences" element={<Preferences />} />
                <Route path="/login" element={<Login />} />
                <Route path="/signup" element={<Signup />} />
              </Routes>
            </main>
            <Footer />
          </Router>
          <Toaster
            position="bottom-right"
            toastOptions={{
              style: {
                background: dark ? '#1e293b' : '#ffffff',
                color: dark ? '#f1f5f9' : '#1F2937',
                border: `1px solid ${dark ? 'rgba(99,102,241,0.2)' : 'rgba(99,102,241,0.15)'}`,
                borderRadius: '12px',
                boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
              },
            }}
          />
        </div>
          </FilterContext.Provider>
        </LanguageContext.Provider>
      </AuthContext.Provider>
    </ThemeContext.Provider>
  )
}

function Footer() {
  const { dark } = useTheme()
  return (
    <footer className={`border-t py-6 mt-8 ${dark ? 'border-slate-800 text-slate-600' : 'border-slate-200 text-slate-400'}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs">
        <span>
          <strong className="text-primary-500">Dainik-Vidya</strong> — AI-Powered News Intelligence
        </span>
        <span>Sources: BBC · Reuters · NYT · 1stPost · Aaj Tak · Dainik Bhaskar · Lokmat · Sakal · Eenadu · Sakshi</span>
      </div>
    </footer>
  )
}
