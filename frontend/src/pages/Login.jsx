import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { login, addBookmark, postMySubscribe } from '../services/api'
import { useTheme, useAuth } from '../App'
import { LogIn, Eye, EyeOff } from 'lucide-react'
import toast from 'react-hot-toast'

export default function Login() {
  const { dark } = useTheme()
  const { setAuth } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      const data = await login(email, password)
      localStorage.setItem('token', data.access_token)
      localStorage.setItem('user', JSON.stringify(data.user))
      setAuth(data.user)
      toast.success('Logged in successfully')

      // Post-login continuation
      const pending = sessionStorage.getItem('redirectAfterLogin')
      sessionStorage.removeItem('redirectAfterLogin')

      if (pending === 'subscribe') {
        // Auto-subscribe (signup already sets it, but ensure)
        try { await postMySubscribe() } catch {}
        toast.success('You are subscribed to daily emails!')
        navigate('/subscribe')
      } else if (pending === 'personalize') {
        navigate('/preferences')
      } else if (pending === 'bookmark') {
        const articleId = sessionStorage.getItem('pendingBookmarkId')
        sessionStorage.removeItem('pendingBookmarkId')
        if (articleId) {
          try {
            await addBookmark(articleId)
            toast.success('Article bookmarked!')
          } catch {
            toast.error('Could not bookmark article')
          }
        }
        navigate(-1)
      } else {
        navigate('/')
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  const inputClass = `w-full px-4 py-3 rounded-lg border focus:ring-2 focus:ring-primary-500 transition-all ${
    dark ? 'bg-slate-900 border-slate-700 text-slate-100 placeholder-slate-500' : 'bg-slate-50 border-slate-300 text-slate-900 placeholder-slate-400'
  }`

  return (
    <div className="max-w-md mx-auto mt-20 px-4 animate-fade-in">
      <div className={`rounded-2xl p-8 ${dark ? 'glass text-slate-100' : 'bg-white border border-slate-200 shadow-sm text-slate-800'}`}>
        <div className="flex justify-center mb-6 text-primary-500">
          <LogIn size={40} />
        </div>
        <h2 className="text-2xl font-bold text-center mb-6">Welcome Back</h2>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <input
            type="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            placeholder="Email"
            required
            id="login-email"
            className={inputClass}
          />
          <div className="relative">
            <input
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="Password"
              required
              id="login-password"
              className={inputClass}
            />
            <button
              type="button"
              onClick={() => setShowPassword(s => !s)}
              className={`absolute right-3 top-1/2 -translate-y-1/2 p-1 rounded transition-colors ${
                dark ? 'text-slate-500 hover:text-slate-300' : 'text-slate-400 hover:text-slate-600'
              }`}
              tabIndex={-1}
              title={showPassword ? 'Hide password' : 'Show password'}
            >
              {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>
          <button
            type="submit"
            disabled={loading}
            id="login-submit"
            className="w-full mt-2 bg-primary-600 hover:bg-primary-500 text-white font-semibold py-3 rounded-lg transition-colors cursor-pointer"
          >
            {loading ? 'Logging in...' : 'Log In'}
          </button>
        </form>
        <p className={`text-center mt-6 text-sm ${dark ? 'text-slate-400' : 'text-slate-500'}`}>
          Don't have an account? <Link to="/signup" className="text-primary-500 font-medium hover:underline">Sign up</Link>
        </p>
      </div>
    </div>
  )
}
