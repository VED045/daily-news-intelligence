import React, { createContext, useContext, useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import Navbar from './components/Navbar'
import Dashboard from './pages/Dashboard'
import NewsFeed from './pages/NewsFeed'
import Trends from './pages/Trends'
import Subscribe from './pages/Subscribe'

export const ThemeContext = createContext({ dark: true, toggle: () => {} })
export const useTheme = () => useContext(ThemeContext)

export const APP_NAME = 'Dainik-Vidya'
export const APP_TAGLINE = 'AI-Powered News Intelligence'

export default function App() {
  const [dark, setDark] = useState(() => localStorage.getItem('dv-theme') !== 'light')

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    localStorage.setItem('dv-theme', dark ? 'dark' : 'light')
    document.title = `${APP_NAME} — ${APP_TAGLINE}`
  }, [dark])

  return (
    <ThemeContext.Provider value={{ dark, toggle: () => setDark(d => !d) }}>
      <div className={`min-h-screen transition-colors duration-300 ${
        dark ? 'bg-slate-950 text-slate-100' : 'bg-[#F8FAFC] text-[#1F2937]'
      }`}>
        <Router>
          <Navbar />
          <main className="pt-16 min-h-screen">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/news" element={<NewsFeed />} />
              <Route path="/trends" element={<Trends />} />
              <Route path="/subscribe" element={<Subscribe />} />
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
        <span>Sources: BBC · Reuters · The Hindu · ESPN · TOI · Moneycontrol · CNBC · Yahoo Finance</span>
      </div>
    </footer>
  )
}
