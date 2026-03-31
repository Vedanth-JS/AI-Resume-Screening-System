import React from 'react'
import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Briefcase, Users, MessageSquare,
  ShieldAlert, Settings, LogOut, Terminal, BarChart2
} from 'lucide-react'
import { authService } from '../services/api'

export function Sidebar({ onLogout }) {
  const userEmail = authService.getEmail()
  const initials  = userEmail ? userEmail[0].toUpperCase() : '?'

  const navItems = [
    { name: 'Dashboard',      path: '/',          icon: LayoutDashboard, end: true  },
    { name: 'Jobs',           path: '/jobs',       icon: Briefcase,       end: false },
    { name: 'Candidates',     path: '/candidates', icon: Users,           end: false },
    { name: 'Analytics',      path: '/analytics',  icon: BarChart2,       end: false },
    { name: 'RAG Chat',       path: '/chat',       icon: MessageSquare,   end: false },
    { name: 'Bias Detection', path: '/bias',       icon: ShieldAlert,     end: false },
    { name: 'Settings',       path: '/settings',   icon: Settings,        end: false },
  ]

  return (
    <aside className="w-72 bg-[#0d0d0f] border-r border-white/5 flex flex-col px-4 py-8 flex-shrink-0">
      {/* Brand */}
      <div className="flex items-center gap-3 px-2 mb-12">
        <div className="bg-blue-600/20 p-2.5 rounded-xl border border-blue-500/30 shadow-[0_0_20px_rgba(59,130,246,0.1)]">
          <Terminal className="w-6 h-6 text-blue-500" />
        </div>
        <div>
          <h1 className="text-xl font-bold tracking-tight leading-none">
            AI <span className="text-blue-500">ATS</span>
          </h1>
          <p className="text-[9px] text-slate-600 font-bold uppercase tracking-widest mt-0.5">
            v2.0 · Talent Intelligence
          </p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.name}
            to={item.path}
            end={item.end}
            className={({ isActive }) =>
              `relative flex items-center gap-3 px-3 py-3 rounded-xl transition-all duration-300 group ${
                isActive
                  ? 'bg-blue-600/10 text-blue-400 border border-blue-500/20 shadow-[0_0_15px_rgba(59,130,246,0.08)]'
                  : 'text-slate-400 hover:text-white hover:bg-white/5 border border-transparent'
              }`
            }
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-blue-500 rounded-r-full" />
                )}
                <item.icon className="w-5 h-5 flex-shrink-0" />
                <span className="font-medium text-sm">{item.name}</span>
                {item.name === 'Analytics' && (
                  <span className="ml-auto text-[9px] font-bold text-blue-500/60 bg-blue-500/10 border border-blue-500/20 rounded px-1.5 py-0.5 uppercase tracking-wider">
                    NEW
                  </span>
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* User Footer */}
      <div className="mt-auto pt-6 border-t border-white/5 space-y-3">
        {userEmail && (
          <div className="flex items-center gap-3 px-3 py-3 rounded-xl bg-white/[0.02] border border-white/5">
            <div className="w-8 h-8 rounded-xl bg-blue-500/20 border border-blue-500/30 flex items-center justify-center text-blue-400 font-bold text-sm flex-shrink-0">
              {initials}
            </div>
            <div className="min-w-0">
              <p className="text-xs font-semibold text-slate-300 truncate">{userEmail}</p>
              <p className="text-[10px] text-slate-600 font-medium">Recruiter</p>
            </div>
          </div>
        )}
        <button
          onClick={onLogout}
          className="flex items-center gap-3 w-full px-3 py-3 text-slate-400 hover:text-red-400 rounded-xl transition-all hover:bg-red-500/5 border border-transparent hover:border-red-500/10"
        >
          <LogOut className="w-5 h-5" />
          <span className="font-medium text-sm">Sign Out</span>
        </button>
      </div>
    </aside>
  )
}
