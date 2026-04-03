import React, { useState } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Briefcase, 
  Users, 
  BarChart3, 
  Settings, 
  Search, 
  Bell, 
  Menu, 
  X,
  ChevronLeft,
  ChevronRight,
  LogOut,
  Plus
} from 'lucide-react';
import { cn } from '@/lib/utils';

const navItems = [
  { name: 'Dashboard', icon: LayoutDashboard, path: '/dashboard' },
  { name: 'Jobs', icon: Briefcase, path: '/jobs' },
  { name: 'Candidates', icon: Users, path: '/candidates' },
  { name: 'Analytics', icon: BarChart3, path: '/analytics' },
  { name: 'Settings', icon: Settings, path: '/settings' },
];

export default function DashboardLayout() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const location = useLocation();

  return (
    <div className="flex h-screen bg-background overflow-hidden text-foreground">
      {/* Sidebar */}
      <aside 
        className={cn(
          "relative bg-card border-r transition-all duration-300 ease-in-out z-30",
          isSidebarOpen ? "w-64" : "w-20"
        )}
      >
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="flex items-center gap-3 px-6 h-16 border-b">
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
              <span className="text-primary-foreground font-bold font-display">A</span>
            </div>
            {isSidebarOpen && <span className="font-display font-bold text-lg tracking-tight">Antigravity</span>}
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-3 py-4 space-y-1">
            {navItems.map((item) => (
              <Link
                key={item.name}
                to={item.path}
                className={cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors group relative",
                  location.pathname.startsWith(item.path) 
                    ? "bg-primary/10 text-primary" 
                    : "text-muted-foreground hover:bg-accent hover:text-foreground"
                )}
              >
                <item.icon className="w-5 h-5 flex-shrink-0" />
                {isSidebarOpen && <span className="font-medium text-sm">{item.name}</span>}
                {!isSidebarOpen && (
                  <div className="absolute left-14 bg-popover text-popover-foreground px-2 py-1 rounded text-xs opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-50">
                    {item.name}
                  </div>
                )}
              </Link>
            ))}
          </nav>

          {/* Bottom Sidebar */}
          <div className={cn("p-4 border-t space-y-1", !isSidebarOpen && "items-center")}>
            <button className={cn(
              "flex items-center gap-3 px-3 py-2.5 w-full rounded-lg text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors",
              !isSidebarOpen && "justify-center px-0"
            )}>
              <LogOut className="w-5 h-5" />
              {isSidebarOpen && <span className="text-sm font-medium">Log out</span>}
            </button>
          </div>
        </div>

        {/* Toggle Button */}
        <button 
          onClick={() => setIsSidebarOpen(!isSidebarOpen)}
          className="absolute -right-3 top-20 bg-background border rounded-full p-1 shadow-sm hover:bg-accent z-40"
        >
          {isSidebarOpen ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Header */}
        <header className="h-16 border-b bg-card px-8 flex items-center justify-between z-20">
          <div className="flex items-center gap-4 flex-1">
            <div className="relative max-w-md w-full group">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground transition-colors group-focus-within:text-primary" />
              <input 
                type="text" 
                placeholder="Global Search (CMD+K)" 
                className="w-full bg-accent/30 border-none rounded-full pl-10 pr-4 py-2 text-sm focus:ring-1 focus:ring-primary transition-all"
              />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button className="flex items-center gap-2 bg-primary text-primary-foreground px-4 py-1.5 rounded-full text-sm font-medium hover:opacity-90 transition-opacity">
              <Plus className="w-4 h-4" />
              Create Job
            </button>
            <div className="w-[1px] h-6 bg-border mx-2" />
            <button className="relative p-2 text-muted-foreground hover:text-foreground transition-colors">
              <Bell className="w-5 h-5" />
              <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-destructive rounded-full border-2 border-card" />
            </button>
            <div className="flex items-center gap-3 pl-2 cursor-pointer group">
              <div className="text-right hidden sm:block">
                <p className="text-xs font-bold leading-tight">Vedanth</p>
                <p className="text-[10px] text-muted-foreground">Admin</p>
              </div>
              <div className="w-8 h-8 rounded-full bg-accent flex items-center justify-center font-bold text-xs ring-2 ring-transparent group-hover:ring-primary/20 transition-all">
                VS
              </div>
            </div>
          </div>
        </header>

        {/* Scrollable Area */}
        <main className="flex-1 overflow-y-auto bg-background/50 p-8">
          <div className="max-w-7xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
