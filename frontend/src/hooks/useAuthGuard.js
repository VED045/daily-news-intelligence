import { useNavigate } from 'react-router-dom'
import { useAuth } from '../App'
import toast from 'react-hot-toast'

/**
 * Hook for protecting actions that require auth.
 *
 * Usage:
 *   const guard = useAuthGuard()
 *   guard("bookmark", { articleId: "123" })
 *   // If not logged in → redirects to /login with pending action stored
 *   // If logged in → returns true (caller can proceed)
 */
export default function useAuthGuard() {
  const { auth } = useAuth()
  const navigate = useNavigate()

  return (actionName, meta = {}) => {
    if (auth) return true

    // Store pending action
    sessionStorage.setItem('redirectAfterLogin', actionName)
    if (meta.articleId) {
      sessionStorage.setItem('pendingBookmarkId', meta.articleId)
    }

    toast('Please log in to continue', { icon: '🔒' })
    navigate('/login')
    return false
  }
}
