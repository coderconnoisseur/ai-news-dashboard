import { useEffect, useState } from 'react'
import { fetchSources, toggleSource, deleteSource, createSource } from '../api'
import { Settings2, Plus, Trash2, ToggleLeft, ToggleRight, Rss, Clock } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import toast from 'react-hot-toast'
import clsx from 'clsx'

const TYPE_COLORS = {
    rss: 'bg-orange-500/10 text-orange-400',
    api: 'bg-blue-500/10 text-blue-400',
    scraper: 'bg-purple-500/10 text-purple-400',
    youtube: 'bg-red-500/10 text-red-400',
    reddit: 'bg-amber-500/10 text-amber-400',
}

function AddSourceModal({ onClose, onAdd }) {
    const [form, setForm] = useState({ name: '', url: '', type: 'rss' })
    const [saving, setSaving] = useState(false)

    const submit = async () => {
        if (!form.name || !form.url) { toast.error('Name and URL required'); return }
        setSaving(true)
        try {
            const src = await createSource(form)
            onAdd(src)
            toast.success(`Added: ${src.name}`)
            onClose()
        } catch (e) {
            toast.error(e.response?.data?.detail || 'Failed to add source')
        }
        setSaving(false)
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="absolute inset-0 bg-black/70" onClick={onClose} />
            <div className="relative card w-full max-w-md shadow-2xl p-6 space-y-4">
                <h2 className="text-base font-semibold text-white flex items-center gap-2">
                    <Plus size={16} className="text-brand-400" /> Add Source
                </h2>
                <div className="space-y-3">
                    <input className="input w-full" placeholder="Source name" value={form.name}
                        onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
                    <input className="input w-full" placeholder="RSS / API URL" value={form.url}
                        onChange={e => setForm(f => ({ ...f, url: e.target.value }))} />
                    <select className="input w-full" value={form.type}
                        onChange={e => setForm(f => ({ ...f, type: e.target.value }))}>
                        <option value="rss">RSS</option>
                        <option value="api">API</option>
                        <option value="scraper">Scraper</option>
                        <option value="youtube">YouTube</option>
                        <option value="reddit">Reddit</option>
                    </select>
                </div>
                <div className="flex justify-end gap-2 pt-1">
                    <button onClick={onClose} className="btn-ghost">Cancel</button>
                    <button onClick={submit} disabled={saving} className="btn-primary flex items-center gap-2">
                        {saving && <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />}
                        Add Source
                    </button>
                </div>
            </div>
        </div>
    )
}

export default function SourcesPage() {
    const [sources, setSources] = useState([])
    const [loading, setLoading] = useState(true)
    const [showAdd, setShowAdd] = useState(false)

    const load = async () => {
        setLoading(true)
        try { setSources(await fetchSources()) } catch { }
        setLoading(false)
    }

    useEffect(() => { load() }, [])

    const handleToggle = async (id) => {
        const src = await toggleSource(id)
        setSources(prev => prev.map(s => s.id === id ? src : s))
    }

    const handleDelete = async (id, name) => {
        if (!confirm(`Delete "${name}"?`)) return
        try {
            await deleteSource(id)
            setSources(prev => prev.filter(s => s.id !== id))
            toast.success('Source deleted')
        } catch { toast.error('Delete failed') }
    }

    const active = sources.filter(s => s.active).length

    return (
        <div className="h-full flex flex-col">
            <div className="px-6 py-5 border-b border-gray-800">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-xl font-bold text-white flex items-center gap-2">
                            <Settings2 size={18} className="text-brand-400" />
                            Sources
                        </h1>
                        <p className="text-sm text-gray-500 mt-0.5">
                            {active} active · {sources.length} total
                        </p>
                    </div>
                    <button onClick={() => setShowAdd(true)} className="btn-primary flex items-center gap-2 text-sm">
                        <Plus size={14} /> Add Source
                    </button>
                </div>
            </div>

            <div className="flex-1 overflow-y-auto px-6 py-4">
                {loading ? (
                    <div className="flex justify-center pt-16">
                        <div className="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
                    </div>
                ) : (
                    <div className="space-y-2">
                        {sources.map(src => (
                            <div key={src.id} className={clsx(
                                'card px-4 py-3 flex items-center gap-4 transition-all',
                                !src.active && 'opacity-50'
                            )}>
                                <div className="w-8 h-8 bg-gray-800 rounded-lg flex items-center justify-center flex-shrink-0">
                                    <Rss size={14} className="text-gray-400" />
                                </div>

                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2">
                                        <span className="text-sm font-medium text-gray-200">{src.name}</span>
                                        <span className={clsx('badge', TYPE_COLORS[src.type] || 'bg-gray-700 text-gray-400')}>
                                            {src.type}
                                        </span>
                                    </div>
                                    <p className="text-xs text-gray-600 truncate mt-0.5">{src.url}</p>
                                    {src.last_fetched_at && (
                                        <p className="text-xs text-gray-700 flex items-center gap-1 mt-0.5">
                                            <Clock size={10} />
                                            {formatDistanceToNow(new Date(src.last_fetched_at), { addSuffix: true })}
                                        </p>
                                    )}
                                </div>

                                <div className="flex items-center gap-1">
                                    <button
                                        onClick={() => handleToggle(src.id)}
                                        className={clsx(
                                            'p-1.5 rounded-md transition-all',
                                            src.active
                                                ? 'text-green-400 hover:bg-green-400/10'
                                                : 'text-gray-600 hover:bg-gray-800'
                                        )}
                                        title={src.active ? 'Disable' : 'Enable'}
                                    >
                                        {src.active ? <ToggleRight size={18} /> : <ToggleLeft size={18} />}
                                    </button>
                                    <button
                                        onClick={() => handleDelete(src.id, src.name)}
                                        className="p-1.5 rounded-md text-gray-600 hover:text-red-400 hover:bg-red-400/10 transition-all"
                                        title="Delete source"
                                    >
                                        <Trash2 size={14} />
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {showAdd && <AddSourceModal onClose={() => setShowAdd(false)} onAdd={s => setSources(p => [...p, s])} />}
        </div>
    )
}