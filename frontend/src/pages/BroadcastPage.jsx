import { useEffect, useState } from 'react'
import { Radio, Mail, Linkedin, MessageCircle, FileText, CheckCircle, XCircle, Clock } from 'lucide-react'
import { fetchBroadcastLogs, fetchFavorites } from '../api'
import { formatDistanceToNow } from 'date-fns'
import BroadcastModal from '../components/BroadcastModal'
import { useFavorites } from '../hooks/useFavorites'
import clsx from 'clsx'

const PLATFORM_META = {
    email: { icon: Mail, label: 'Email', color: 'text-blue-400', bg: 'bg-blue-500/10' },
    linkedin: { icon: Linkedin, label: 'LinkedIn', color: 'text-sky-400', bg: 'bg-sky-500/10' },
    whatsapp: { icon: MessageCircle, label: 'WhatsApp', color: 'text-green-400', bg: 'bg-green-500/10' },
    newsletter: { icon: FileText, label: 'Newsletter', color: 'text-purple-400', bg: 'bg-purple-500/10' },
    blog: { icon: FileText, label: 'Blog', color: 'text-pink-400', bg: 'bg-pink-500/10' },
}

const STATUS_META = {
    success: { icon: CheckCircle, color: 'text-green-400', label: 'Sent' },
    simulated: { icon: Clock, color: 'text-yellow-400', label: 'Simulated' },
    failed: { icon: XCircle, color: 'text-red-400', label: 'Failed' },
    pending: { icon: Clock, color: 'text-gray-400', label: 'Pending' },
}

function LogRow({ log }) {
    const platform = PLATFORM_META[log.platform] || PLATFORM_META.email
    const status = STATUS_META[log.status] || STATUS_META.pending
    const Icon = platform.icon
    const StatusIcon = status.icon

    return (
        <div className="card px-4 py-3 flex items-center gap-4">
            <div className={clsx('w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0', platform.bg)}>
                <Icon size={15} className={platform.color} />
            </div>
            <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-200">{platform.label}</p>
                <p className="text-xs text-gray-600 truncate">
                    Favorite #{log.favorite_id} · {formatDistanceToNow(new Date(log.timestamp), { addSuffix: true })}
                </p>
            </div>
            <div className="flex items-center gap-1.5">
                <StatusIcon size={13} className={status.color} />
                <span className={clsx('text-xs font-medium', status.color)}>{status.label}</span>
            </div>
        </div>
    )
}

export default function BroadcastPage() {
    const [logs, setLogs] = useState([])
    const [loading, setLoading] = useState(true)
    const [showModal, setShowModal] = useState(false)
    const { favorites, selected, toggleSelect, selectAll, clearSelection } = useFavorites()

    const loadLogs = async () => {
        setLoading(true)
        try {
            const data = await fetchBroadcastLogs()
            setLogs(data)
        } catch { }
        setLoading(false)
    }

    useEffect(() => { loadLogs() }, [])

    const stats = {
        total: logs.length,
        sent: logs.filter(l => l.status === 'success').length,
        simulated: logs.filter(l => l.status === 'simulated').length,
        failed: logs.filter(l => l.status === 'failed').length,
    }

    return (
        <div className="h-full flex flex-col">
            {/* Header */}
            <div className="px-6 py-5 border-b border-gray-800">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-xl font-bold text-white flex items-center gap-2">
                            <Radio size={18} className="text-brand-400" />
                            Broadcast
                        </h1>
                        <p className="text-sm text-gray-500 mt-0.5">Send your favorites to Email, LinkedIn, WhatsApp</p>
                    </div>
                    <button
                        onClick={() => setShowModal(true)}
                        disabled={favorites.length === 0}
                        className="btn-primary flex items-center gap-2 text-sm"
                    >
                        <Radio size={14} />
                        New Broadcast
                    </button>
                </div>

                {/* Stats bar */}
                <div className="grid grid-cols-4 gap-3 mt-4">
                    {[
                        { label: 'Total Broadcasts', value: stats.total, color: 'text-white' },
                        { label: 'Sent', value: stats.sent, color: 'text-green-400' },
                        { label: 'Simulated', value: stats.simulated, color: 'text-yellow-400' },
                        { label: 'Failed', value: stats.failed, color: 'text-red-400' },
                    ].map(s => (
                        <div key={s.label} className="card px-4 py-3">
                            <p className={clsx('text-2xl font-bold', s.color)}>{s.value}</p>
                            <p className="text-xs text-gray-500 mt-0.5">{s.label}</p>
                        </div>
                    ))}
                </div>
            </div>

            {/* Quick-select favorites for broadcast */}
            {favorites.length > 0 && (
                <div className="px-6 py-3 border-b border-gray-800 bg-gray-900/50">
                    <div className="flex items-center justify-between mb-2">
                        <p className="text-xs font-medium text-gray-400 uppercase tracking-wider">
                            Select favorites to broadcast
                        </p>
                        <div className="flex gap-2">
                            <button onClick={selectAll} className="text-xs text-brand-400 hover:text-brand-300">Select all</button>
                            <span className="text-gray-700">·</span>
                            <button onClick={clearSelection} className="text-xs text-gray-500 hover:text-gray-300">Clear</button>
                        </div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        {favorites.map(fav => (
                            <button
                                key={fav.id}
                                onClick={() => toggleSelect(fav.id)}
                                className={clsx(
                                    'text-xs px-2.5 py-1 rounded-full border transition-all truncate max-w-xs',
                                    selected.has(fav.id)
                                        ? 'border-brand-500 bg-brand-600/10 text-brand-300'
                                        : 'border-gray-700 text-gray-400 hover:border-gray-600'
                                )}
                            >
                                {fav.news_item.title.slice(0, 40)}…
                            </button>
                        ))}
                    </div>
                    {selected.size > 0 && (
                        <button
                            onClick={() => setShowModal(true)}
                            className="btn-primary text-sm mt-3 flex items-center gap-2"
                        >
                            <Radio size={13} />
                            Broadcast {selected.size} selected
                        </button>
                    )}
                </div>
            )}

            {/* Logs */}
            <div className="flex-1 overflow-y-auto px-6 py-4">
                <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                    Broadcast History
                </h2>
                {loading ? (
                    <div className="flex justify-center pt-12">
                        <div className="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
                    </div>
                ) : logs.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-48 gap-3">
                        <Radio size={32} className="text-gray-700" />
                        <p className="text-sm text-gray-500">No broadcasts yet.</p>
                    </div>
                ) : (
                    <div className="space-y-2">
                        {logs.map(log => <LogRow key={log.id} log={log} />)}
                    </div>
                )}
            </div>

            {showModal && (
                <BroadcastModal
                    favoriteIds={[...selected]}
                    onClose={() => { setShowModal(false); loadLogs() }}
                />
            )}
        </div>
    )
}