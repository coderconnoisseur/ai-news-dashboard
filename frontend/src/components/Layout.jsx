import { NavLink } from 'react-router-dom'
import { Newspaper, Star, Radio, Settings2, Zap } from 'lucide-react'
import clsx from 'clsx'

const nav = [
    { to: '/', icon: Newspaper, label: 'Feed' },
    { to: '/favorites', icon: Star, label: 'Favorites' },
    { to: '/broadcast', icon: Radio, label: 'Broadcast' },
    { to: '/sources', icon: Settings2, label: 'Sources' },
]

export default function Layout({ children }) {
    return (
        <div className="flex h-screen overflow-hidden">
            {/* Sidebar */}
            <aside className="w-56 flex-shrink-0 bg-gray-900 border-r border-gray-800 flex flex-col">
                {/* Logo */}
                <div className="px-5 py-5 border-b border-gray-800">
                    <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center">
                            <Zap size={16} className="text-white" />
                        </div>
                        <div>
                            <p className="text-sm font-bold text-white leading-none">AI News</p>
                            <p className="text-xs text-gray-500 mt-0.5">Dashboard</p>
                        </div>
                    </div>
                </div>

                {/* Nav */}
                <nav className="flex-1 px-3 py-4 space-y-1">
                    {nav.map(({ to, icon: Icon, label }) => (
                        <NavLink
                            key={to}
                            to={to}
                            end={to === '/'}
                            className={({ isActive }) =>
                                clsx(
                                    'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all',
                                    isActive
                                        ? 'bg-brand-600 text-white'
                                        : 'text-gray-400 hover:text-white hover:bg-gray-800'
                                )
                            }
                        >
                            <Icon size={17} />
                            {label}
                        </NavLink>
                    ))}
                </nav>

                <div className="px-5 py-4 border-t border-gray-800">
                    <p className="text-xs text-gray-600">v1.0.0 · Culinda</p>
                </div>
            </aside>

            {/* Main */}
            <main className="flex-1 overflow-auto">
                {children}
            </main>
        </div>
    )
}