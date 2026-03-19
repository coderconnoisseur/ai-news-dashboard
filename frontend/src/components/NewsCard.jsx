import { Star, ExternalLink, Clock, User } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import clsx from 'clsx'

const SOURCE_COLORS = {
    'OpenAI Blog': 'bg-emerald-500/10 text-emerald-400',
    'Anthropic News': 'bg-orange-500/10 text-orange-400',
    'Google AI Blog': 'bg-blue-500/10 text-blue-400',
    'DeepMind Blog': 'bg-cyan-500/10 text-cyan-400',
    'TechCrunch AI': 'bg-green-500/10 text-green-400',
    'arXiv cs.AI': 'bg-purple-500/10 text-purple-400',
    'arXiv cs.LG': 'bg-purple-500/10 text-purple-400',
    'Hacker News (AI)': 'bg-amber-500/10 text-amber-400',
}

function getSourceColor(name) {
    return SOURCE_COLORS[name] || 'bg-gray-700/50 text-gray-400'
}

function ImpactDot({ score }) {
    if (!score) return null
    const color = score >= 8 ? 'bg-red-400' : score >= 6 ? 'bg-yellow-400' : 'bg-green-400'
    return (
        <span className="flex items-center gap-1 text-xs text-gray-500">
            <span className={clsx('w-1.5 h-1.5 rounded-full', color)} />
            {score.toFixed(1)}
        </span>
    )
}

export default function NewsCard({ item, onToggleFavorite }) {
    const timeAgo = item.published_at
        ? formatDistanceToNow(new Date(item.published_at), { addSuffix: true })
        : 'Recently'

    const summary = item.ai_summary || item.summary

    return (
        <div className={clsx(
            'card p-4 hover:border-gray-700 transition-all group',
            item.is_favorited && 'border-brand-500/30'
        )}>
            <div className="flex items-start gap-3">
                {/* Image */}
                {item.image_url && (
                    <img
                        src={item.image_url}
                        alt=""
                        className="w-16 h-16 rounded-lg object-cover flex-shrink-0 bg-gray-800"
                        onError={e => e.target.style.display = 'none'}
                    />
                )}

                {/* Content */}
                <div className="flex-1 min-w-0">
                    {/* Top row */}
                    <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                        <span className={clsx('badge', getSourceColor(item.source_name))}>
                            {item.source_name || 'Unknown'}
                        </span>
                        {item.tags?.slice(0, 2).map(tag => (
                            <span key={tag} className="badge bg-gray-800 text-gray-400">{tag}</span>
                        ))}
                        <ImpactDot score={item.impact_score} />
                    </div>

                    {/* Title */}
                    <a
                        href={item.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm font-semibold text-gray-100 hover:text-brand-400
                       transition-colors line-clamp-2 block"
                    >
                        {item.title}
                    </a>

                    {/* Summary */}
                    {summary && (
                        <p className="text-xs text-gray-500 mt-1 line-clamp-2">{summary}</p>
                    )}

                    {/* Footer */}
                    <div className="flex items-center justify-between mt-2">
                        <div className="flex items-center gap-3 text-xs text-gray-600">
                            <span className="flex items-center gap-1">
                                <Clock size={11} /> {timeAgo}
                            </span>
                            {item.author && (
                                <span className="flex items-center gap-1">
                                    <User size={11} /> {item.author.slice(0, 20)}
                                </span>
                            )}
                        </div>
                        <div className="flex items-center gap-1">
                            <a
                                href={item.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="p-1.5 rounded-md text-gray-600 hover:text-gray-300
                           hover:bg-gray-800 transition-all"
                                title="Open article"
                            >
                                <ExternalLink size={13} />
                            </a>
                            <button
                                onClick={() => onToggleFavorite(item)}
                                className={clsx(
                                    'p-1.5 rounded-md transition-all',
                                    item.is_favorited
                                        ? 'text-yellow-400 hover:text-yellow-300 bg-yellow-400/10'
                                        : 'text-gray-600 hover:text-yellow-400 hover:bg-gray-800'
                                )}
                                title={item.is_favorited ? 'Remove favorite' : 'Add to favorites'}
                            >
                                <Star size={13} fill={item.is_favorited ? 'currentColor' : 'none'} />
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}