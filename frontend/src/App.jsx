import React, { useState } from 'react'
import { Routes, Route } from 'react-router-dom'
import { Sidebar } from './components/Sidebar'
import { Login } from './components/Login'
import { Dashboard } from './components/Dashboard'
import { JobDetail } from './components/JobDetail'
import { Jobs } from './components/Jobs'
import { Candidates } from './components/Candidates'
import { RAGChat } from './components/RAGChat'
import { BiasDetection } from './components/BiasDetection'
import { Analytics } from './components/Analytics'
import { authService } from './services/api'

// Lazy‐load Settings to reduce initial bundle
const SettingsPage = React.lazy(() =>
  import('./components/Settings').then(m => ({ default: m.Settings }))
)

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('token'))

  const handleLogin  = () => setIsAuthenticated(true)
  const handleLogout = () => { authService.logout(); setIsAuthenticated(false) }

  if (!isAuthenticated) return <Login onLogin={handleLogin} />

  return (
    <div className="flex min-h-screen">
      <Sidebar onLogout={handleLogout} />
      <main className="flex-1 p-10 bg-[#0a0a0b]/50 backdrop-blur-3xl overflow-x-hidden relative">
        {/* Ambient background glow */}
        <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-blue-600/5 blur-[120px] -z-10 rounded-full pointer-events-none" />
        <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-purple-600/5 blur-[100px] -z-10 rounded-full pointer-events-none" />

        <React.Suspense fallback={<div className="text-slate-500 text-sm p-4">Loading…</div>}>
          <Routes>
            <Route path="/"           element={<Dashboard />} />
            <Route path="/jobs"       element={<Jobs />} />
            <Route path="/job/:id"    element={<JobDetail />} />
            <Route path="/candidates" element={<Candidates />} />
            <Route path="/chat"       element={<RAGChat />} />
            <Route path="/bias"       element={<BiasDetection />} />
            <Route path="/analytics"  element={<Analytics />} />
            <Route path="/settings"   element={<SettingsPage />} />
          </Routes>
        </React.Suspense>
      </main>
    </div>
  )
}

export default App
