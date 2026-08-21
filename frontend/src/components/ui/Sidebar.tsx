import React, { useState } from "react";
import { NavLink } from "react-router-dom";
import { LayoutDashboard, Briefcase, Users, BarChart3, Upload, MessageSquare, LogOut, Moon, Sun, ChevronLeft, ChevronRight, KanbanSquare } from "lucide-react";

interface SidebarProps {
  onLogout: () => void;
  userEmail?: string;
  darkMode: boolean;
  onToggleDark: () => void;
}

const navItems = [
  { to: "/dashboard", icon: LayoutDashboard, label: "Dashboard", end: true },
  { to: "/jobs", icon: Briefcase, label: "Jobs" },
  { to: "/candidates", icon: Users, label: "Candidates" },
  { to: "/pipeline", icon: KanbanSquare, label: "Pipeline" },
  { to: "/analytics", icon: BarChart3, label: "Analytics" },
  { to: "/upload", icon: Upload, label: "Upload" },
  { to: "/chat", icon: MessageSquare, label: "AI Chat" },
];

export const Sidebar = React.memo(function Sidebar({ onLogout, userEmail, darkMode, onToggleDark }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={`${collapsed ? "w-16" : "w-60"} bg-background border-r flex flex-col flex-shrink-0 min-h-screen transition-all duration-200`}
      role="navigation"
      aria-label="Main navigation"
    >
      {/* Brand */}
      <div className={`px-4 py-5 border-b flex items-center ${collapsed ? "justify-center" : "gap-3"}`}>
        <div className="w-9 h-9 bg-primary rounded-lg flex items-center justify-center text-primary-foreground font-bold text-sm shrink-0">A</div>
        {!collapsed && (
          <div className="min-w-0">
            <h1 className="text-sm font-semibold tracking-tight leading-none">AI ATS</h1>
            <p className="text-[11px] text-muted-foreground font-medium">Talent Engine</p>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 py-4 space-y-0.5">
        {navItems.map((item) => {
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isActive ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-accent hover:text-foreground"
                }`
              }
              title={collapsed ? item.label : undefined}
            >
              <item.icon className="w-4 h-4 shrink-0" aria-hidden="true" />
              {!collapsed && <span>{item.label}</span>}
            </NavLink>
          );
        })}
      </nav>

      {/* Bottom */}
      <div className="px-2 py-3 border-t space-y-1">
        <button onClick={onToggleDark} className="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors" title={darkMode ? "Light mode" : "Dark mode"}>
          {darkMode ? <Sun className="w-4 h-4 shrink-0"/> : <Moon className="w-4 h-4 shrink-0"/>}
          {!collapsed && <span>{darkMode ? "Light Mode" : "Dark Mode"}</span>}
        </button>

        {userEmail && !collapsed && (
          <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-muted/50">
            <div className="w-7 h-7 bg-primary rounded-lg flex items-center justify-center text-primary-foreground text-xs font-bold shrink-0">{userEmail[0].toUpperCase()}</div>
            <div className="min-w-0"><p className="text-xs font-medium truncate">{userEmail}</p></div>
          </div>
        )}

        <button onClick={onLogout} className="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm font-medium text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors" aria-label="Sign out" title="Sign out">
          <LogOut className="w-4 h-4 shrink-0" />
          {!collapsed && <span>Sign Out</span>}
        </button>

        <button onClick={() => setCollapsed(!collapsed)} className="flex items-center justify-center w-full py-1.5 text-muted-foreground hover:text-foreground transition-colors" aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}>
          {collapsed ? <ChevronRight className="w-4 h-4"/> : <ChevronLeft className="w-4 h-4"/>}
        </button>
      </div>
    </aside>
  );
});
