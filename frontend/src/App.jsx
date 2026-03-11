import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Navbar from './components/Navbar'
import JobsPage from './pages/JobsPage'
import UploadPage from './pages/UploadPage'
import DashboardPage from './pages/DashboardPage'
import AnalyticsPage from './pages/AnalyticsPage'

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-cream flex flex-col">
        <Navbar />
        
        <main className="flex-1 mt-16 px-6">
          <Routes>
            <Route path="/" element={<Navigate to="/jobs" replace />} />
            <Route path="/jobs" element={<JobsPage />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="*" element={<div className="py-20 text-center font-serif italic text-navy-300">Page not found.</div>} />
          </Routes>
        </main>
        
        <footer className="py-12 border-t border-navy-50 text-center">
          <p className="text-navy-300 text-[11px] uppercase tracking-[0.2em] font-medium">
            &copy; 2026 RecruitAI &mdash; Advanced Candidate Evaluation
          </p>
        </footer>
      </div>
    </Router>
  )
}

export default App
