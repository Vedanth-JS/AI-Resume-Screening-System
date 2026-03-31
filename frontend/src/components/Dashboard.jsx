import React, { useState, useEffect } from 'react'
import { Plus, Users, Briefcase, TrendingUp, Search, ShieldAlert, Zap, ArrowRight, Star } from 'lucide-react'
import { Link } from 'react-router-dom'
import { jobService } from '../services/api'
import api from '../services/api'

export function Dashboard() {
  const [stats, setStats] = useState([
    { label: 'Total Candidates', value: '0', icon: Users, color: 'text-blue-400', bg: 'bg-blue-500/10' },
    { label: 'Active Job Postings', value: '0', icon: Briefcase, color: 'text-purple-400', bg: 'bg-purple-500/10' },
    { label: 'Avg Match Rate', value: '0%', icon: TrendingUp, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
  ])
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [jobsRes, metricsRes] = await Promise.all([
          jobService.getJobs(),
          api.get('/metrics')
        ])
        
        setJobs(jobsRes.data || [])
        setStats([
          { label: 'Total Candidates', value: metricsRes.data.count.toString(), icon: Users, color: 'text-blue-400', bg: 'bg-blue-500/10' },
          { label: 'Active Job Postings', value: jobsRes.data.length.toString(), icon: Briefcase, color: 'text-purple-400', bg: 'bg-purple-500/10' },
          { label: 'Avg Match Rate', value: `${metricsRes.data.average_score}%`, icon: TrendingUp, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
        ])
      } catch (err) {
        console.error("Dashboard fetch error:", err)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  return (
    <div className="space-y-12 animate-in fade-in slide-in-from-bottom-6 duration-1000">
      {/* Header Section */}
      <header className="flex items-end justify-between">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
            <p className="text-[10px] font-bold text-blue-500/80 uppercase tracking-widest">Enterprise Talent Cloud</p>
          </div>
          <h2 className="text-4xl font-bold text-gradient">Hiring Overview</h2>
        </div>
        <button className="btn-primary flex items-center gap-2 px-8">
          <Plus className="w-5 h-5" />
          <span>New Position</span>
        </button>
      </header>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {stats.map((stat, i) => (
          <div key={stat.label} className="glass-card group relative" style={{ animationDelay: `${i * 150}ms` }}>
            <div className="flex items-start justify-between mb-6">
              <div className={`${stat.bg} p-4 rounded-2xl border border-white/5 transition-all duration-500 group-hover:scale-110 group-hover:border-blue-500/20`}>
                <stat.icon className={`w-8 h-8 ${stat.color}`} />
              </div>
              <TrendingUp className="w-4 h-4 text-emerald-500" />
            </div>
            <h3 className="text-4xl font-bold mb-2 tracking-tighter text-white">{stat.value}</h3>
            <p className="text-sm font-medium text-muted-foreground">{stat.label}</p>
            
            {/* Decorative Sparkle */}
            <Star className="absolute top-4 right-4 w-2 h-2 text-white/10 group-hover:text-blue-500/40 transition-colors" />
          </div>
        ))}
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-10">
        {/* Active Jobs Section */}
        <div className="xl:col-span-2 glass rounded-[2.5rem] p-10 border border-white/5">
          <div className="flex items-center justify-between mb-10">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-2xl bg-blue-500/10 flex items-center justify-center border border-blue-500/20">
                <Zap className="w-6 h-6 text-blue-400" />
              </div>
              <h3 className="text-2xl font-bold tracking-tight text-white">Active Postings</h3>
            </div>
            
            <div className="relative group">
              <Search className="w-4 h-4 text-slate-500 absolute left-4 top-1/2 -translate-y-1/2 group-focus-within:text-blue-500 transition-colors" />
              <input 
                type="text" 
                placeholder="Search candidates/jobs..." 
                className="bg-white/5 border border-white/10 rounded-2xl pl-12 pr-6 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/40 w-80 transition-all placeholder:text-slate-600"
              />
            </div>
          </div>

          <div className="grid gap-4">
            {loading ? (
              [1, 2, 3].map(i => <div key={i} className="h-24 bg-white/5 animate-pulse rounded-3xl" />)
            ) : jobs.length === 0 ? (
                 <div className="text-center py-20 bg-white/[0.01] rounded-3xl border border-dashed border-white/10">
                    <Briefcase className="w-12 h-12 text-slate-700 mx-auto mb-4" />
                    <p className="text-slate-500 font-medium">No open roles found. Expand your search or create one.</p>
                 </div>
            ) : (
                jobs.map((job) => (
                    <Link 
                      to={`/job/${job.id}`}
                      key={job.id} 
                      className="group flex items-center justify-between p-6 rounded-3xl bg-white/[0.02] border border-white/5 hover:bg-white/[0.04] hover:border-blue-500/30 transition-all duration-300"
                    >
                        <div className="flex items-center gap-6">
                          <div className="w-14 h-14 bg-white/5 rounded-2xl flex items-center justify-center text-slate-500 group-hover:bg-blue-600/10 group-hover:text-blue-400 transition-all border border-white/5 group-hover:border-blue-500/20">
                              <Briefcase className="w-7 h-7" />
                          </div>
                          <div>
                              <h4 className="text-lg font-bold text-slate-100 group-hover:text-blue-400 transition-all mb-1">{job.title}</h4>
                              <div className="flex items-center gap-3 text-xs text-slate-500">
                                <span className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 font-bold uppercase tracking-wider">Full Time</span>
                                <span className="w-1 h-1 rounded-full bg-slate-700" />
                                <span>{job.description.slice(0, 40)}...</span>
                              </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-6">
                          <div className="text-right hidden sm:block">
                            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">Status</p>
                            <span className="text-xs font-bold text-emerald-500">Active Pipeline</span>
                          </div>
                          <div className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center group-hover:translate-x-1 transition-transform border border-white/5">
                            <ArrowRight className="w-5 h-5 text-slate-400 group-hover:text-blue-400" />
                          </div>
                        </div>
                    </Link>
                ))
            )}
          </div>
        </div>

        {/* Intelligence Sidebar */}
        <div className="space-y-8">
          <div className="glass-card bg-gradient-to-br from-blue-600/10 via-transparent to-purple-600/5">
            <header className="flex items-center justify-between mb-6">
              <h4 className="font-bold flex items-center gap-2 text-blue-400 font-display">
                <ShieldAlert className="w-5 h-5" />
                Bias Engine
              </h4>
              <span className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
            </header>
            <p className="text-sm text-slate-400 leading-relaxed mb-8">
              Neural audit currently scanning **gendered phrasing** and **hidden bias** across all active job descriptions in your stack.
            </p>
            <button className="w-full py-4 rounded-2xl bg-white/5 border border-white/10 text-xs font-bold uppercase tracking-widest hover:bg-white/10 transition-colors">
              Run Full Audit
            </button>
          </div>

          <div className="glass rounded-[2rem] p-8 border border-white/5">
            <h4 className="font-bold mb-6 font-display text-white">Neural Hub Status</h4>
            <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="w-2 h-2 rounded-full bg-emerald-500 shadow-emerald-500/50 shadow-[0_0_10px]" />
                    <p className="text-xs font-bold text-slate-300 uppercase tracking-wide">FastAPI Gateway</p>
                  </div>
                  <span className="text-[10px] font-bold text-slate-600 tracking-widest">STABLE</span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="w-2 h-2 rounded-full bg-blue-500 shadow-blue-500/50 shadow-[0_0_10px]" />
                    <p className="text-xs font-bold text-slate-300 uppercase tracking-wide">Celery Distributed</p>
                  </div>
                  <span className="text-[10px] font-bold text-slate-600 tracking-widest">ACTIVE</span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="w-2 h-2 rounded-full bg-purple-500 shadow-purple-500/50 shadow-[0_0_10px]" />
                    <p className="text-xs font-bold text-slate-300 uppercase tracking-wide">Chroma Vector DB</p>
                  </div>
                  <span className="text-[10px] font-bold text-slate-600 tracking-widest">INDEXED</span>
                </div>
            </div>
            
            <div className="mt-10 p-5 rounded-2xl bg-blue-500/5 border border-blue-500/10">
               <p className="text-[10px] leading-relaxed text-blue-400 font-medium">
                 Pro Tip: You can now bulk-upload resumes as ZIP files directly to any active position.
               </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
