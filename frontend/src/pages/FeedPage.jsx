import { useState } from 'react'
import { RefreshCw, Search, SlidersHorizontal, BarChart2, Database, Rss } from 'lucide-react'
import { useFeed } from '../hooks/useFeed'
import { fetchStats } from '../api'
import { useEffect } from 'react'
import NewsCard from '../components/NewsCard'
import clsx from 'clsx'

function StatCard({ label, value, icon: Icon, color }) {
    return (
        <div className="card px-4 py-3 flex items-center gap-3">
            <div className={clsx('w-8 h-8 rounded-lg flex items-center justify-center', color)}>
                <Icon size={15} className="text-white" />
            </div>
            <div>
                <p className="text-lg font-bold text-white leading-none">{value ?? '—'}</p>
                <p className="text-xs text-gray-500 mt-0.5">{label}</p>
            </div>
        </div>
    )
}

export default function FeedPage() {
    const { items, total, loading, refreshing, hasMore, filters, setFilters, loadMore, refresh, toggleFavorite } = useFeed()
    const [search, setSearch] = useState('')
    const [stats, setStats] = useState(null)

    useEffect(() => {
        fetchStats().then(setStats).catch(() => { })
    }, [])

    const handleSearch = (e) => {
        if (e.key === 'Enter') setFilters(f => ({ ...f, search: search || undefined }))
    }

    return (
        <div className="h-full flex flex-col">
            {/* Header */}
            <div className="px-6 py-5 border-b border-gray-800">
                <div className="flex items-center justify-between mb-4">
                    <div>
                        <h1 className="text-xl font-bold text-white">AI News Feed</h1>
                        <p className="text-sm text-gray-500 mt-0.5">{total.toLocaleString()} stories · auto-refreshes every 15 min</p>
                    </div>
                    <button
                        onClick={refresh}
                        disabled={refreshing}
                        className="btn-ghost flex items-center gap-2 text-sm"
                    >
                        <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
                        {refreshing ? 'Refreshing…' : 'Refresh'}
                    </button>
                </div>

                {/* Stats */}
                {stats && (
                    <div className="grid grid-cols-4 gap-3 mb-4">
                        <StatCard label="Total Stories" value={stats.total_items} icon={Rss} color="bg-brand-600" />
                        <StatCard label="Unique Stories" value={stats.unique_items} icon={BarChart2} color="bg-emerald-600" />
                        <StatCard label="Duplicates" value={stats.duplicate_items} icon={Database} color="bg-yellow-600" />
                        <StatCard label="Active Sources" value={stats.sources_active} icon={SlidersHorizontal} color="bg-purple-600" />
                    </div>
                )}

                {/* Search + Filters */}
                <div className="flex items-center gap-3">
                    <div className="relative flex-1 max-w-sm">
                        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                        <input
                            className="input w-full pl-8"
                            placeholder="Search news…"
                            value={search}
                            onChange={e => setSearch(e.target.value)}
                            onKeyDown={handleSearch}
                        />
                    </div>

                    <select
                        className="input text-sm"
                        value={filters.sort_by}
                        onChange={e => setFilters(f => ({ ...f, sort_by: e.target.value }))}
                    >
                        <option value="date">Sort: Date</option>
                        <option value="impact">Sort: Impact</option>
                        <option value="source">Sort: Source</option>
                    </select>

                    <select
                        className="input text-sm"
                        value={filters.days_back}
                        onChange={e => setFilters(f => ({ ...f, days_back: Number(e.target.value) }))}
                    >
                        <option value={1}>Last 24h</option>
                        <option value={3}>Last 3 days</option>
                        <option value={7}>Last 7 days</option>
                        <option value={30}>Last 30 days</option>
                    </select>
                </div>
            </div>

            {/* Feed */}
            <div className="flex-1 overflow-y-auto px-6 py-4">
                {loading && items.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-64 gap-3">
                        <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
                        <p className="text-sm text-gray-500">Loading news…</p>
                    </div>
                ) : items.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-64 gap-3">
                        <Rss size={32} className="text-gray-700" />
                        <p className="text-sm text-gray-500">No stories found. Try refreshing the feed.</p>
                        <button onClick={refresh} className="btn-primary text-sm">Fetch News</button>
                    </div>
                ) : (
                    <div className="space-y-3">
                        {items.map(item => (
                            <NewsCard key={item.id} item={item} onToggleFavorite={toggleFavorite} />
                        ))}

                        {hasMore && (
                            <div className="flex justify-center pt-2 pb-6">
                                <button
                                    onClick={loadMore}
                                    disabled={loading}
                                    className="btn-ghost text-sm"
                                >
                                    {loading ? 'Loading…' : 'Load more'}
                                </button>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    )
}