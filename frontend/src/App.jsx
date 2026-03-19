import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import Layout from './components/Layout'
import FeedPage from './pages/FeedPage'
import FavoritesPage from './pages/FavoritesPage'
import BroadcastPage from './pages/BroadcastPage'
import SourcesPage from './pages/SourcesPage'

export default function App() {
    return (
        <BrowserRouter>
            <Toaster
                position="bottom-right"
                toastOptions={{
                    style: {
                        background: '#1f2937',
                        color: '#f3f4f6',
                        border: '1px solid #374151',
                        fontSize: '13px',
                    },
                }}
            />
            <Layout>
                <Routes>
                    <Route path="/" element={<FeedPage />} />
                    <Route path="/favorites" element={<FavoritesPage />} />
                    <Route path="/broadcast" element={<BroadcastPage />} />
                    <Route path="/sources" element={<SourcesPage />} />
                </Routes>
            </Layout>
        </BrowserRouter>
    )
}