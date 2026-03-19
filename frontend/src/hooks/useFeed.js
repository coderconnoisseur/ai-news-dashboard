import { useState, useEffect, useCallback } from 'react'
import { fetchFeed, addFavorite, removeFavorite, refreshFeed } from '../api'
import toast from 'react-hot-toast'

export function useFeed(initialFilters = {}) {
    const [items, setItems] = useState([])
    const [total, setTotal] = useState(0)
    const [loading, setLoading] = useState(false)
    const [refreshing, setRefreshing] = useState(false)
    const [page, setPage] = useState(1)
    const [hasMore, setHasMore] = useState(false)
    const [filters, setFilters] = useState({
        sort_by: 'date',
        sort_order: 'desc',
        days_back: 7,
        page_size: 20,
        ...initialFilters,
    })

    const load = useCallback(async (p = 1, append = false) => {
        setLoading(true)
        try {
            const data = await fetchFeed({ ...filters, page: p })
            setItems(prev => append ? [...prev, ...data.items] : data.items)
            setTotal(data.total)
            setHasMore(data.has_more)
            setPage(p)
        } catch (e) {
            toast.error('Failed to load news feed')
        } finally {
            setLoading(false)
        }
    }, [filters])

    useEffect(() => { load(1) }, [load])

    const loadMore = () => {
        if (!loading && hasMore) load(page + 1, true)
    }

    const refresh = async () => {
        setRefreshing(true)
        try {
            await refreshFeed()
            toast.success('Refreshing feed…')
            setTimeout(() => load(1), 3000) // give backend time
        } catch {
            toast.error('Refresh failed')
        } finally {
            setRefreshing(false)
        }
    }

    const toggleFavorite = async (item) => {
        try {
            if (item.is_favorited) {
                await removeFavorite(item.id)
                toast('Removed from favorites', { icon: '💔' })
            } else {
                await addFavorite(item.id)
                toast.success('Added to favorites!')
            }
            setItems(prev =>
                prev.map(i => i.id === item.id ? { ...i, is_favorited: !i.is_favorited } : i)
            )
        } catch (e) {
            const msg = e.response?.data?.detail || 'Action failed'
            toast.error(msg)
        }
    }

    return { items, total, loading, refreshing, hasMore, filters, setFilters, loadMore, refresh, toggleFavorite }
}