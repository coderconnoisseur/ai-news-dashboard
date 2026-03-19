import { useState } from 'react'
import { X, Mail, Linkedin, MessageCircle, FileText, Send, Copy, Check } from 'lucide-react'
import { broadcast } from '../api'
import toast from 'react-hot-toast'
import clsx from 'clsx'

const PLATFORMS = [
    { id: 'email', label: 'Email', icon: Mail, color: 'text-blue-400' },
    { id: 'linkedin', label: 'LinkedIn', icon: Linkedin, color: 'text-sky-400' },
    { id: 'whatsapp', label: 'WhatsApp', icon: MessageCircle, color: 'text-green-400' },
    { id: 'newsletter', label: 'Newsletter', icon: FileText, color: 'text-purple-400' },
]

function CopyButton({ text }) {
    const [copied, setCopied] = useState(false)
    const copy = () => {
        navigator.clipboard.writeText(text)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
    }
    return (
        <button onClick={copy} className="btn-ghost text-xs flex items-center gap-1.5">
            {copied ? <Check size={12} className="text-green-400" /> : <Copy size={12} />}
            {copied ? 'Copied!' : 'Copy'}
        </button>
    )
}

export default function BroadcastModal({ favoriteIds, onClose }) {
    const [platform, setPlatform] = useState('linkedin')
    const [email, setEmail] = useState('')
    const [subject, setSubject] = useState('Your AI News Digest')
    const [loading, setLoading] = useState(false)
    const [result, setResult] = useState(null)

    const handleSend = async () => {
        if (!favoriteIds.length) {
            toast.error('Select at least one favorite to broadcast')
            return
        }
        setLoading(true)
        try {
            const payload = {
                favorite_ids: favoriteIds,
                platform,
                generate_caption: true,
                ...(platform === 'email' && { recipient_email: email, subject }),
            }
            const res = await broadcast(payload)
            setResult(res)
            toast.success(res.message)
        } catch (e) {
            toast.error(e.response?.data?.detail || 'Broadcast failed')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            {/* Backdrop */}
            <div className="absolute inset-0 bg-black/70" onClick={onClose} />

            {/* Modal */}
            <div className="relative card w-full max-w-lg shadow-2xl">
                {/* Header */}
                <div className="flex items-center justify-between p-5 border-b border-gray-800">
                    <h2 className="text-base font-semibold text-white flex items-center gap-2">
                        <Send size={16} className="text-brand-400" />
                        Broadcast ({favoriteIds.length} item{favoriteIds.length !== 1 ? 's' : ''})
                    </h2>
                    <button onClick={onClose} className="btn-ghost p-1.5">
                        <X size={16} />
                    </button>
                </div>

                <div className="p-5 space-y-4">
                    {/* Platform selector */}
                    <div>
                        <label className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-2 block">
                            Platform
                        </label>
                        <div className="grid grid-cols-4 gap-2">
                            {PLATFORMS.map(p => {
                                const Icon = p.icon
                                return (
                                    <button
                                        key={p.id}
                                        onClick={() => { setPlatform(p.id); setResult(null) }}
                                        className={clsx(
                                            'flex flex-col items-center gap-1.5 p-3 rounded-lg border text-xs font-medium transition-all',
                                            platform === p.id
                                                ? 'border-brand-500 bg-brand-600/10 text-white'
                                                : 'border-gray-700 text-gray-400 hover:border-gray-600 hover:text-gray-200'
                                        )}
                                    >
                                        <Icon size={18} className={platform === p.id ? p.color : ''} />
                                        {p.label}
                                    </button>
                                )
                            })}
                        </div>
                    </div>

                    {/* Email fields */}
                    {platform === 'email' && (
                        <div className="space-y-3">
                            <div>
                                <label className="text-xs text-gray-400 mb-1 block">Recipient Email</label>
                                <input
                                    className="input w-full"
                                    type="email"
                                    placeholder="recipient@example.com"
                                    value={email}
                                    onChange={e => setEmail(e.target.value)}
                                />
                            </div>
                            <div>
                                <label className="text-xs text-gray-400 mb-1 block">Subject</label>
                                <input
                                    className="input w-full"
                                    value={subject}
                                    onChange={e => setSubject(e.target.value)}
                                />
                            </div>
                        </div>
                    )}

                    {/* Result */}
                    {result && (
                        <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700">
                            <div className="flex items-center justify-between mb-2">
                                <span className={clsx(
                                    'badge',
                                    result.status === 'success' ? 'bg-green-500/10 text-green-400' :
                                        result.status === 'simulated' ? 'bg-yellow-500/10 text-yellow-400' :
                                            'bg-red-500/10 text-red-400'
                                )}>
                                    {result.status}
                                </span>
                                {result.generated_content && (
                                    <CopyButton text={result.generated_content} />
                                )}
                            </div>
                            <p className="text-xs text-gray-400 mb-2">{result.message}</p>
                            {result.generated_content && (
                                <pre className="text-xs text-gray-300 whitespace-pre-wrap max-h-48 overflow-y-auto font-sans">
                                    {result.generated_content}
                                </pre>
                            )}
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="flex justify-end gap-2 px-5 pb-5">
                    <button onClick={onClose} className="btn-ghost">Cancel</button>
                    <button
                        onClick={handleSend}
                        disabled={loading || (platform === 'email' && !email)}
                        className="btn-primary flex items-center gap-2"
                    >
                        {loading ? (
                            <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        ) : (
                            <Send size={14} />
                        )}
                        {loading ? 'Sending…' : 'Send'}
                    </button>
                </div>
            </div>
        </div>
    )
}