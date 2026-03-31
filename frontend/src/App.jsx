import React from 'react'
import { Routes, Route, Link, useLocation } from 'react-router-dom'
import { LayoutDashboard, Briefcase, Users, MessageSquare, ShieldAlert, Settings, LogOut, Zap } from 'lucide-react'
import { Dashboard } from './components/Dashboard'
import { JobDetail } from './components/JobDetail'

function Sidebar() {
  const location = useLocation();
  const menuItems = [
    { name: 'Dashboard', icon: LayoutDashboard, path: '/' },
    { name: 'Jobs', icon: Briefcase, path: '/jobs' },
    { name: 'Candidates', icon: Users, path: '/candidates' },
    { name: 'RAG Chat', icon: MessageSquare, path: '/chat' },
    { name: 'Bias Detection', icon: ShieldAlert, path: '/bias' },
    { name: 'System Settings', icon: Settings, path: '/settings' },
  ];

  return (
    <aside className="w-72 bg-[#0a0a0b] border-r border-white/5 h-screen sticky top-0 flex flex-col p-6 z-50">
      <div className="flex items-center gap-3 mb-10 px-2 animate-in fade-in slide-in-from-left-4 duration-1000">
        <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center shadow-[0_0_15px_rgba(59,130,246,0.5)]">
          <Zap className="w-6 h-6 text-white" />
        </div>
        <h1 className="text-xl font-bold font-display text-gradient">AI hiring</h1>
      </div>

      <nav className="flex-1 space-y-2">
        {menuItems.map((item) => (
          <Link
            key={item.name}
            to={item.path}
            className={`nav-item ${location.pathname === item.path ? 'active' : ''}`}
          >
            <item.icon className="w-5 h-5 transition-transform duration-300 group-hover:scale-110" />
            <span>{item.name}</span>
          </Link>
        ))}
      </nav>

      <div className="pt-6 border-t border-white/5 space-y-2">
        <button className="nav-item w-full group hover:bg-destructive/10 hover:text-destructive transition-colors">
          <LogOut className="w-5 h-5 group-hover:rotate-12 transition-transform" />
          <span>Sign Out</span>
        </button>
      </div>
    </aside>
  );
}

function App() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-10 bg-[#0a0a0b]/50 backdrop-blur-3xl overflow-x-hidden relative">
        {/* Background Accent 1 */}
        <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-blue-600/5 blur-[120px] -z-10 rounded-full" />
        {/* Background Accent 2 */}
        <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-purple-600/5 blur-[100px] -z-10 rounded-full" />
        
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/job/:id" element={<JobDetail />} />
          {/* Add more routes as needed */}
        </Routes>
      </main>
    </div>
  )
}

export default App
