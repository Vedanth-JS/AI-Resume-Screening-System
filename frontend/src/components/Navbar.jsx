import { Link, useLocation } from 'react-router-dom'
import { Briefcase, Upload, LayoutDashboard, BarChart2 } from 'lucide-react'

const NAV_ITEMS = [
  { to: '/jobs', icon: Briefcase, label: 'Jobs' },
  { to: '/upload', icon: Upload, label: 'Upload' },
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/analytics', icon: BarChart2, label: 'Analytics' },
]

export default function Navbar() {
  const { pathname } = useLocation()

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-navy-700 border-b border-navy-600 shadow-lg">
      <div className="max-w-7xl mx-auto px-6 flex items-center justify-between h-16">
        {/* Brand */}
        <Link to="/" className="flex items-center gap-2.5">
          <div className="w-8 h-8 bg-accent rounded-md flex items-center justify-center">
            <span className="text-navy-900 font-serif font-bold text-sm">RS</span>
          </div>
          <div>
            <span className="font-serif font-semibold text-white text-lg tracking-tight">RecruitAI</span>
            <span className="hidden sm:inline text-navy-300 text-xs ml-2 uppercase tracking-widest">Screening System</span>
          </div>
        </Link>

        {/* Navigation */}
        <div className="flex items-center gap-1">
          {NAV_ITEMS.map(({ to, icon: Icon, label }) => {
            const active = pathname.startsWith(to)
            return (
              <Link
                key={to}
                to={to}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200
                  ${active
                    ? 'bg-white/10 text-white'
                    : 'text-navy-300 hover:bg-white/5 hover:text-white'
                  }`}
              >
                <Icon size={15} />
                <span className="hidden sm:inline">{label}</span>
              </Link>
            )
          })}
        </div>
      </div>
    </nav>
  )
}
