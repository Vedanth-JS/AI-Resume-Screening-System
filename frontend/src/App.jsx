import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { LayoutDashboard, Upload, ListChecks, PieChart, Search, MessageSquare } from 'lucide-react';
import { jobsApi } from './api/client';
import { motion, AnimatePresence } from 'framer-motion';
import UploadPage from './pages/Upload';
import ResultsPage from './pages/Results';
import AnalyticsPage from './pages/Analytics';

const App = () => {
  const [latestJobId, setLatestJobId] = React.useState(null);

  React.useEffect(() => {
    const fetchLatestJob = async () => {
      try {
        const response = await jobsApi.getAll();
        if (response.data && response.data.length > 0) {
          // Assuming the latest job is the last or the one with the highest ID
          const latest = response.data[response.data.length - 1];
          setLatestJobId(latest.id);
        }
      } catch (error) {
        console.error("Failed to fetch jobs:", error);
      }
    };
    fetchLatestJob();
  }, []);

  return (
    <Router>
      <div className="flex h-screen bg-slate-50 font-sans">
        {/* Sidebar */}
        <aside className="w-72 bg-slate-50 border-r border-slate-200 flex flex-col">
          <div className="p-8">
            <h1 className="text-3xl font-bold gradient-text tracking-tight">Screener</h1>
            <p className="text-xs text-slate-400 mt-1 uppercase tracking-widest font-semibold">Recruitment Assistant</p>
          </div>
          
          <nav className="flex-1 px-4 space-y-2">
            <Link to="/" className="sidebar-link group">
              <Upload className="w-5 h-5 mr-3 group-hover:scale-110 transition-transform" />
              Upload Resumes
            </Link>
            <Link to={latestJobId ? `/results/${latestJobId}` : "/results/1"} className="sidebar-link group">
              <ListChecks className="w-5 h-5 mr-3 group-hover:scale-110 transition-transform" />
              Screening Results
            </Link>
            <Link to={latestJobId ? `/analytics/${latestJobId}` : "/analytics/1"} className="sidebar-link group">
              <PieChart className="w-5 h-5 mr-3 group-hover:scale-110 transition-transform" />
              Analytics
            </Link>
          </nav>

          <div className="p-6 mt-auto">
            <div className="bg-gradient-to-br from-primary to-primary-dark p-6 rounded-2xl text-white shadow-lg shadow-primary/20">
              <p className="text-xs font-semibold opacity-80 uppercase mb-1">Current Plan</p>
              <p className="text-lg font-bold">Pro Trial</p>
              <button className="mt-3 w-full bg-white/20 hover:bg-white/30 py-2 rounded-xl text-sm font-medium backdrop-blur-sm transition-colors">
                Upgrade Now
              </button>
            </div>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto bg-white/40 backdrop-blur-sm">
          <div className="max-w-6xl mx-auto p-12">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
            >
              <Routes>
                <Route path="/" element={<UploadPage />} />
                <Route path="/results/:jobId" element={<ResultsPage />} />
                <Route path="/analytics/:jobId" element={<AnalyticsPage />} />
              </Routes>
            </motion.div>
          </div>
        </main>
      </div>
    </Router>
  );
};

export default App;
