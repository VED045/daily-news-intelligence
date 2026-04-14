import { useState, useEffect, useCallback, useRef } from 'react'
import { getNews } from '../services/api'

export function useNews(category = '') {
  const [articles, setArticles] = useState([])
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const prevCategory = useRef(category)
  // Reset when category changes
  useEffect(() => {
    if (prevCategory.current !== category) {
      prevCategory.current = category
      setArticles([])
      setPage(1)
      setHasMore(true)
    }
  }, [category])

  const fetchPage = useCallback(async (pageNum, cat) => {
    setLoading(true)
    setError(null)
    try {
      const data = await getNews(cat, pageNum)
      setArticles(prev => pageNum === 1 ? data.articles : [...prev, ...data.articles])
      setHasMore(data.has_more)
    } catch (e) {
      setError('Failed to load news. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchPage(page, category)
  }, [page, category, fetchPage])

  const loadMore = () => { if (!loading && hasMore) setPage(p => p + 1) }
  const refresh = () => { setArticles([]); setPage(1); setHasMore(true) }

  return { articles, loading, error, hasMore, loadMore, refresh }
}
