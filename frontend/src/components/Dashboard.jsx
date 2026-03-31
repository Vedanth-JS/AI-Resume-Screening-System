import React, { useState, useEffect } from 'react'
import { Plus, Users, Briefcase, TrendingUp, Search, ShieldAlert, Zap, ArrowRight, Star, BarChart2, Target } from 'lucide-react'
import { Link } from 'react-router-dom'
import { jobService } from '../services/api'
import api from '../services/api'
import { CreateJobModal } from './CreateJobModal'
import { Doughnut, Bar } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale,
  BarElement,
} from 'chart.js'

ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement)

// ─── Score Distribution Chart ─────────────────────────────────────────────────

function ScoreDistributionChart({ metrics }) {
  const total = (metrics.accept || 0) + (metrics.review || 0) + (metrics.reject || 0)
  const data = {
    labels: ['Shortlisted (70%+)', 'In Review (40–70%)', 'Declined (<40%)'],
    datasets: [{
      data: [metrics.accept || 0, metrics.review || 0, metrics.reject || 0],
      backgroundColor: ['rgba(16,185,129,0.75)', 'rgba(245,158,11,0.75)', 'rgba(239,68,68,0.7)'],
      borderColor: ['rgba(16,185,129,1)', 'rgba(245,158,11,1)', 'rgba(239,68,68,1)'],
      borderWidth: 1.5,
      hoverOffset: 10,
    }],
  }
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: '74%',
    plugins: {
      legend: {
        position: 'bottom',
        labels: { color: '#94a3b8', font: { size: 10, weight: 'bold' }, padding: 14, usePointStyle: true, pointStyleWidth: 8 },
      },
      tooltip: {
        backgroundColor: 'rgba(10,10,12,0.97)',
        borderColor: 'rgba(255,255,255,0.07)',
        borderWidth: 1,
        titleColor: '#fff',
        bodyColor: '#94a3b8',
      },
    },
  }
  return (
    <div className="glass rounded-[2rem] p-8 border border-white/5">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-purple-500/10 flex items-center justify-center border border-purple-500/20">
          <Target className="w-5 h-5 text-purple-400" />
        </div>
        <div>
          <h3 className="font-bold text-white text-sm">Score Distribution</h3>
          <p className="text-xs text-slate-500">{total} total screened</p>
        </div>
      </div>
      {total === 0 ? (
        <div className="h-48 flex items-center justify-center text-slate-600 text-sm">Upload resumes to see data</div>
      ) : (
        <div className="h-48"><Doughnut data={data} options={options} /></div>
      )}
    </div>
  )
}

// ─── Top Candidates Bar Chart ─────────────────────────────────────────────────

function TopCandidatesChart({ candidates }) {
  const top = [...candidates]
    .filter(c => c.final_score != null)
    .sort((a, b) => b.final_score - a.final_score)
    .slice(0, 6)

  const data = {
    labels: top.map(c => c.candidate_name?.split(' ')[0] || `#${c.candidate_id}`),
    datasets: [{
      label: 'Match Score',
      data: top.map(c => Math.round(c.final_score)),
      backgroundColor: top.map(c =>
        c.final_score >= 70 ? 'rgba(16,185,129,0.7)' :
        c.final_score >= 40 ? 'rgba(245,158,11,0.7)' :
        'rgba(239,68,68,0.7)'
      ),
      borderRadius: 8,
      borderSkipped: false,
    }],
  }
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      x: { grid: { display: false }, ticks: { color: '#94a3b8', font: { size: 10, weight: 'bold' } } },
      y: {
        min: 0, max: 100,
        grid: { color: 'rgba(255,255,255,0.04)' },
        ticks: { color: '#94a3b8', font: { size: 10 }, callback: v => `${v}%` },
      },
    },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: 'rgba(10,10,12,0.97)',
        borderColor: 'rgba(255,255,255,0.07)',
        borderWidth: 1,
        titleColor: '#fff',
        bodyColor: '#94a3b8',
        callbacks: { label: ctx => ` Score: ${ctx.parsed.y}%` },
      },
    },
  }
  return (
    <div className="glass rounded-[2rem] p-8 border border-white/5">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center border border-blue-500/20">
          <BarChart2 className="w-5 h-5 text-blue-400" />
        </div>
        <div>
          <h3 className="font-bold text-white text-sm">Top Candidates</h3>
          <p className="text-xs text-slate-500">by neural match score</p>
        </div>
      </div>
      {top.length === 0 ? (
        <div className="h-40 flex items-center justify-center text-slate-600 text-sm">Upload resumes to see ranking</div>
      ) : (
        <div className="h-40"><Bar data={data} options={options} /></div>
      )}
    </div>
  )
}

// ─── Dashboard ────────────────────────────────────────────────────────────────

export function Dashboard() {
  const [stats, setStats] = useState([
    { label: 'Total Candidates', value: '—', icon: Users, color: 'text-blue-400', bg: 'bg-blue-500/10' },
    { label: 'Active Job Postings', value: '—', icon: Briefcase, color: 'text-purple-400', bg: 'bg-purple-500/10' },
    { label: 'Avg Match Rate', value: '—', icon: TrendingUp, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
  ])
  const [jobs, setJobs] = useState([])
  const [topCandidates, setTopCandidates] = useState([])
  const [metrics, setMetrics] = useState({ accept: 0, review: 0, reject: 0 })
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [showModal, setShowModal] = useState(false)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [jobsRes, metricsRes] = await Promise.all([
          jobService.getJobs(),
          api.get('/metrics'),
        ])
        const jobList = jobsRes.data || []
        const m = metricsRes.data || {}
        setJobs(jobList)
        setMetrics(m)
        setStats([
          { label: 'Total Candidates', value: String(m.count ?? 0), icon: Users, color: 'text-blue-400', bg: 'bg-blue-500/10' },
          { label: 'Active Job Postings', value: String(jobList.length), icon: Briefcase, color: 'text-purple-400', bg: 'bg-purple-500/10' },
          { label: 'Avg Match Rate', value: `${m.average_score ?? 0}%`, icon: TrendingUp, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
        ])
        // fetch candidate history for charts (top 5 jobs)
        const allCandidates = []
        await Promise.all(jobList.slice(0, 5).map(async (job) => {
          try {
            const h = await api.get(`/history/${job.id}`)
            allCandidates.push(...(h.data || []))
          } catch {}
        }))
        setTopCandidates(allCandidates)
      } catch (err) {
        console.error('Dashboard fetch error:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  const handleJobCreated = (newJob) => {
    setJobs(prev => [newJob, ...prev])
    setStats(prev => prev.map(s =>
      s.label === 'Active Job Postings' ? { ...s, value: String(parseInt(s.value) + 1) } : s
    ))
    setShowModal(false)
  }

  const filteredJobs = jobs.filter(j => j.title.toLowerCase().includes(search.toLowerCase()))

  return (
    <div className="space-y-10 animate-in fade-in slide-in-from-bottom-6 duration-1000">
      {showModal && <CreateJobModal onClose={() => setShowModal(false)} onCreated={handleJobCreated} />}

      {/* Header */}
      <header className="flex items-end justify-between">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
            <p className="text-[10px] font-bold text-blue-500/80 uppercase tracking-widest">Enterprise Talent Cloud</p>
          </div>
          <h2 className="text-4xl font-bold text-gradient">Hiring Overview</h2>
        </div>
        <button onClick={() => setShowModal(true)} className="btn-primary flex items-center gap-2 px-8">
          <Plus className="w-5 h-5" />
          <span>New Position</span>
        </button>
      </header>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {stats.map((stat, i) => (
          <div key={stat.label} className="glass-card group relative" style={{ animationDelay: `${i * 120}ms` }}>
            <div className="flex items-start justify-between mb-6">
              <div className={`${stat.bg} p-4 rounded-2xl border border-white/5 transition-all duration-500 group-hover:scale-110 group-hover:border-blue-500/20`}>
                <stat.icon className={`w-7 h-7 ${stat.color}`} />
              </div>
              <TrendingUp className="w-4 h-4 text-emerald-500/40" />
            </div>
            <h3 className={`text-4xl font-bold mb-2 tracking-tighter text-white transition-opacity ${loading ? 'opacity-30' : 'opacity-100'}`}>
              {stat.value}
            </h3>
            <p className="text-sm font-medium text-slate-500">{stat.label}</p>
            <Star className="absolute top-4 right-4 w-2 h-2 text-white/10 group-hover:text-blue-500/40 transition-colors" />
          </div>
        ))}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ScoreDistributionChart metrics={metrics} />
        <TopCandidatesChart candidates={topCandidates} />
      </div>

      {/* Active Jobs + Sidebar */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
        {/* Jobs */}
        <div className="xl:col-span-2 glass rounded-[2.5rem] p-10 border border-white/5">
          <div className="flex items-center justify-between mb-8">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-2xl bg-blue-500/10 flex items-center justify-center border border-blue-500/20">
                <Zap className="w-6 h-6 text-blue-400" />
              </div>
              <h3 className="text-2xl font-bold tracking-tight text-white">Active Postings</h3>
            </div>
            <div className="relative">
              <Search className="w-4 h-4 text-slate-500 absolute left-4 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Filter jobs..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="bg-white/5 border border-white/10 rounded-2xl pl-12 pr-6 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/40 w-56 transition-all placeholder:text-slate-600"
              />
            </div>
          </div>

          <div className="grid gap-4">
            {loading ? (
              [1, 2, 3].map(i => <div key={i} className="h-24 bg-white/5 animate-pulse rounded-3xl" />)
            ) : filteredJobs.length === 0 ? (
              <div className="text-center py-20 bg-white/[0.01] rounded-3xl border border-dashed border-white/10">
                <Briefcase className="w-12 h-12 text-slate-700 mx-auto mb-4" />
                <p className="text-slate-500 font-medium mb-3">No open roles found.</p>
                <button onClick={() => setShowModal(true)} className="text-xs text-blue-400 font-bold hover:text-blue-300 transition-colors">
                  Post your first position →
                </button>
              </div>
            ) : (
              filteredJobs.slice(0, 6).map(job => (
                <Link
                  to={`/job/${job.id}`}
                  key={job.id}
                  className="group flex items-center justify-between p-5 rounded-3xl bg-white/[0.02] border border-white/5 hover:bg-white/[0.04] hover:border-blue-500/30 transition-all duration-300"
                >
                  <div className="flex items-center gap-5">
                    <div className="w-12 h-12 bg-white/5 rounded-2xl flex items-center justify-center text-slate-500 group-hover:bg-blue-600/10 group-hover:text-blue-400 transition-all border border-white/5 group-hover:border-blue-500/20 flex-shrink-0">
                      <Briefcase className="w-6 h-6" />
                    </div>
                    <div>
                      <h4 className="text-base font-bold text-slate-100 group-hover:text-blue-400 transition-all mb-1">{job.title}</h4>
                      <div className="flex items-center gap-2 text-[11px] text-slate-500">
                        <span className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 font-bold uppercase tracking-wider text-[10px]">Full Time</span>
                        <span className="w-1 h-1 rounded-full bg-slate-700" />
                        <span>{job.min_experience}+ yrs exp</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right hidden sm:block">
                      <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">Status</p>
                      <span className="text-xs font-bold text-emerald-500">Active Pipeline</span>
                    </div>
                    <div className="w-9 h-9 rounded-xl bg-white/5 flex items-center justify-center group-hover:translate-x-1 transition-transform border border-white/5">
                      <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-blue-400" />
                    </div>
                  </div>
                </Link>
              ))
            )}
            {!loading && jobs.length > 6 && (
              <Link to="/jobs" className="block py-4 text-center text-xs font-bold text-blue-400 hover:text-blue-300 transition-colors tracking-widest uppercase">
                View all {jobs.length} postings →
              </Link>
            )}
          </div>
        </div>

        {/* Intelligence Sidebar */}
        <div className="space-y-6">
          <div className="glass-card bg-gradient-to-br from-blue-600/10 via-transparent to-purple-600/5">
            <header className="flex items-center justify-between mb-6">
              <h4 className="font-bold flex items-center gap-2 text-blue-400">
                <ShieldAlert className="w-5 h-5" />
                Bias Engine
              </h4>
              <span className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
            </header>
            <p className="text-sm text-slate-400 leading-relaxed mb-6">
              Neural audit scanning for gendered phrasing and hidden bias across all active job descriptions.
            </p>
            <Link to="/bias" className="block w-full py-4 rounded-2xl bg-white/5 border border-white/10 text-xs font-bold uppercase tracking-widest hover:bg-white/10 transition-colors text-center">
              Run Full Audit
            </Link>
          </div>

          <div className="glass rounded-[2rem] p-8 border border-white/5">
            <h4 className="font-bold mb-6 text-white text-sm uppercase tracking-wide">Neural Hub Status</h4>
            <div className="space-y-5">
              {[
                { label: 'FastAPI Gateway', dot: 'bg-emerald-500', glow: 'shadow-emerald-500/50', status: 'STABLE' },
                { label: 'Celery Distributed', dot: 'bg-blue-500', glow: 'shadow-blue-500/50', status: 'ACTIVE' },
                { label: 'Chroma Vector DB', dot: 'bg-purple-500', glow: 'shadow-purple-500/50', status: 'INDEXED' },
                { label: 'PostgreSQL', dot: 'bg-amber-500', glow: 'shadow-amber-500/50', status: 'ONLINE' },
              ].map(item => (
                <div key={item.label} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-2 h-2 rounded-full ${item.dot} shadow-[0_0_8px] ${item.glow}`} />
                    <p className="text-xs font-bold text-slate-300 uppercase tracking-wide">{item.label}</p>
                  </div>
                  <span className="text-[10px] font-bold text-slate-600 tracking-widest">{item.status}</span>
                </div>
              ))}
            </div>
            <div className="mt-8 p-4 rounded-2xl bg-blue-500/5 border border-blue-500/10">
              <p className="text-[10px] leading-relaxed text-blue-400 font-medium">
                💡 Bulk-upload resumes as ZIP files directly to any active position via the Job Detail page.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
