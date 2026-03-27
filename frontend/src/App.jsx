import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Navbar from './components/Navbar'
import Dashboard from './pages/Dashboard'
import VideoDetail from './pages/VideoDetail'
import Keywords from './pages/Keywords'
import Saved from './pages/Saved'
import Channels from './pages/Channels'
import Trends from './pages/Trends'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 60_000,
    },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen bg-white">
          <Navbar />
          <main>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/video/:videoId" element={<VideoDetail />} />
              <Route path="/keywords" element={<Keywords />} />
              <Route path="/saved" element={<Saved />} />
              <Route path="/channels" element={<Channels />} />
              <Route path="/trends" element={<Trends />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
