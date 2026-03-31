import React from 'react'
import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Briefcase, Users, MessageSquare, ShieldAlert, Settings, LogOut, Terminal } from 'lucide-react'

export function Sidebar() {
  const navItems = [
    { name: 'Dashboard', path: '/', icon: LayoutDashboard },
    { name: 'Jobs', path: '/jobs', icon: Briefcase },
    { name: 'Candidates', path: '/candidates', icon: Users },
    { name: 'RAG Chat', path: '/chat', icon: MessageSquare },
    { name: 'Bias Detection', path: '/bias', icon: ShieldAlert },
    { name: 'System Settings', path: '/settings', icon: Settings },
  ]

  return (
    <aside className="w-72 bg-[#0d0d0f] border-r border-white/5 flex flex-col px-4 py-8">
      {/* Brand Logo */}
      <div className="flex items-center gap-3 px-2 mb-12">
        <div className="bg-blue-600/20 p-2.5 rounded-xl border border-blue-500/30">
          <Terminal className="w-6 h-6 text-blue-500" />
        </div>
        <h1 className="text-xl font-bold tracking-tight">AI <span className="text-blue-500">ATS</span></h1>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 space-y-2">
        {navItems.map((item) => (
          <NavLink
            key={item.name}
            to={item.path}
            className={({ isActive }) => `
              flex items-center gap-3 px-3 py-3 rounded-xl transition-all duration-300
              ${isActive 
                ? 'bg-blue-600/10 text-blue-500 border border-blue-500/20' 
                : 'text-slate-400 hover:text-white hover:bg-white/5'
              }
            `}
          >
            <item.icon className="w-5 h-5" />
            <span className="font-medium">{item.name}</span>
          </NavLink>
        ))}
      </nav>

      {/* User Footer */}
      <div className="mt-auto pt-6 border-t border-white/5">
        <button className="flex items-center gap-3 w-full px-3 py-3 text-slate-400 hover:text-white rounded-xl transition-all hover:bg-red-500/5 hover:text-red-400">
          <LogOut className="w-5 h-5" />
          <span className="font-medium">Sign Out</span>
        </button>
      </div>
    </aside>
  )
}
