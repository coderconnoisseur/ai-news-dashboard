import { useState } from 'react'
import { Star, Trash2, Send, CheckSquare, Square, Inbox } from 'lucide-react'
import { useFavorites } from '../hooks/useFavorites'
import { formatDistanceToNow } from 'date-fns'
import BroadcastModal from '../components/BroadcastModal'
import clsx from 'clsx'

function FavoriteRow({ fav, selected, onToggleSelect, onRemove }) {
    const item = fav.news_item
    const timeAgo = item.published_at
        ? formatDistanceToNow(new Date(item.published_at), { addSuffix: true })
        : 'Recently'

    return (
        <div className={clsx(
            'card p-4 flex items-start gap-3 transition-all',
            selected && 'border-brand-500/50 bg-brand-600/5'
        )}>
            {/* Checkbox */}
            <button
                onClick={() => onToggleSelect(fav.id)}
                className="mt-0.5 text-gray-500 hover:text-brand-400 transition-colors flex-shrink-0"
            >
                {selected
                    ? <CheckSquare size={16} className="text-brand-400" />
                    : <Square size={16} />}
            </button>

            {/* Image */}
            {item.image_url && (
                <img
                    src={item.image_url}
                    alt=""
                    className="w-14 h-14 rounded-lg object-cover flex-shrink-0 bg-gray-800"
                    onError={e => e.target.style.display = 'none'}
                />
            )}

            {/* Content */}
            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                    <span className="badge bg-gray-800 text-gray-400 text-xs">{item.source_name}</span>
                    <span className="text-xs text-gray-600">{timeAgo}</span>
                </div>
                <a
                    href={item.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm font-semibold text-gray-100 hover:text-brand-400 transition-colors line-clamp-2 block"
                >
                    {item.title}
                </a>
                {item.ai_summary && (
                    <p className="text-xs text-gray-500 mt-1 line-clamp-2">{item.ai_summary}</p>
                )}
            </div>

            {/* Actions */}
            <button
                onClick={() => onRemove(item.id)}
                className="p-1.5 rounded-md text-gray-600 hover:text-red-400 hover:bg-red-400/10 transition-all flex-shrink-0"
                title="Remove from favorites"
            >
                <Trash2 size={14} />
            </button>
        </div>
    )
}

export default function FavoritesPage() {
    const { favorites, loading, selected, toggleSelect, selectAll, clearSelection, remove } = useFavorites()
    const [showBroadcast, setShowBroadcast] = useState(false)

    const selectedIds = [...selected]
    const allSelected = favorites.length > 0 && selected.size === favorites.length

    return (
        <div className="h-full flex flex-col">
            {/* Header */}
            <div className="px-6 py-5 border-b border-gray-800">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-xl font-bold text-white flex items-center gap-2">
                            <Star size={18} className="text-yellow-400" fill="currentColor" />
                            Favorites
                        </h1>
                        <p className="text-sm text-gray-500 mt-0.5">{favorites.length} saved item{favorites.length !== 1 ? 's' : ''}</p>
                    </div>

                    <div className="flex items-center gap-2">
                        {favorites.length > 0 && (
                            <button
                                onClick={allSelected ? clearSelection : selectAll}
                                className="btn-ghost text-sm flex items-center gap-1.5"
                            >
                                {allSelected ? <CheckSquare size={14} /> : <Square size={14} />}
                                {allSelected ? 'Deselect all' : 'Select all'}
                            </button>
                        )}
                        <button
                            onClick={() => setShowBroadcast(true)}
                            disabled={selected.size === 0}
                            className="btn-primary flex items-center gap-2 text-sm"
                        >
                            <Send size={14} />
                            Broadcast ({selected.size})
                        </button>
                    </div>
                </div>
            </div>

            {/* List */}
            <div className="flex-1 overflow-y-auto px-6 py-4">
                {loading ? (
                    <div className="flex items-center justify-center h-48">
                        <div className="w-7 h-7 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
                    </div>
                ) : favorites.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-64 gap-3">
                        <Inbox size={36} className="text-gray-700" />
                        <p className="text-sm text-gray-500">No favorites yet.</p>
                        <p className="text-xs text-gray-600">Star items from the feed to save them here.</p>
                    </div>
                ) : (
                    <div className="space-y-3">
                        {favorites.map(fav => (
                            <FavoriteRow
                                key={fav.id}
                                fav={fav}
                                selected={selected.has(fav.id)}
                                onToggleSelect={toggleSelect}
                                onRemove={remove}
                            />
                        ))}
                    </div>
                )}
            </div>

            {showBroadcast && (
                <BroadcastModal
                    favoriteIds={selectedIds}
                    onClose={() => setShowBroadcast(false)}
                />
            )}
        </div>
    )
}