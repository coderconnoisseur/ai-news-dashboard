import { useState, useEffect, useCallback } from 'react'
import { fetchFavorites, removeFavorite } from '../api'
import toast from 'react-hot-toast'

export function useFavorites() {
    const [favorites, setFavorites] = useState([])
    const [loading, setLoading] = useState(false)
    const [selected, setSelected] = useState(new Set())

    const load = useCallback(async () => {
        setLoading(true)
        try {
            const data = await fetchFavorites()
            setFavorites(data)
        } catch {
            toast.error('Failed to load favorites')
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => { load() }, [load])

    const remove = async (newsItemId) => {
        try {
            await removeFavorite(newsItemId)
            setFavorites(prev => prev.filter(f => f.news_item_id !== newsItemId))
            setSelected(prev => { const s = new Set(prev); s.delete(newsItemId); return s })
            toast('Removed from favorites', { icon: '🗑️' })
        } catch {
            toast.error('Failed to remove')
        }
    }

    const toggleSelect = (favoriteId) => {
        setSelected(prev => {
            const s = new Set(prev)
            s.has(favoriteId) ? s.delete(favoriteId) : s.add(favoriteId)
            return s
        })
    }

    const selectAll = () => setSelected(new Set(favorites.map(f => f.id)))
    const clearSelection = () => setSelected(new Set())

    return { favorites, loading, selected, toggleSelect, selectAll, clearSelection, remove, reload: load }
}