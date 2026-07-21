import React, { useState, useEffect } from 'react'
import { Plus, Briefcase, Search, X, ChevronRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { jobService } from '../services/api'
import { CreateJobModal } from './CreateJobModal'

export function Jobs() {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [showModal, setShowModal] = useState(false)

  useEffect(() => {
    jobService.getJobs()
      .then(res => setJobs(res.data || []))
      .catch(err => console.error('Jobs fetch error:', err))
      .finally(() => setLoading(false))
  }, [])

  const handleJobCreated = (newJob) => {
    setJobs(prev => [newJob, ...prev])
  }

  const filtered = jobs.filter(j =>
    (j.title || '').toLowerCase().includes(search.toLowerCase()) ||
    (j.required_skills || []).some(s => (s || '').toLowerCase().includes(search.toLowerCase()))
  )

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-6 duration-700">
      {showModal && (
        <CreateJobModal onClose={() => setShowModal(false)} onCreated={handleJobCreated} />
      )}

      {/* Header */}
      <header className="flex items-end justify-between">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
            <p className="text-[10px] font-bold text-blue-500/80 uppercase tracking-widest">Open Roles</p>
          </div>
          <h2 className="text-4xl font-bold text-gradient">Job Postings</h2>
        </div>
        <button
          id="create-job-btn"
          onClick={() => setShowModal(true)}
          className="btn-primary flex items-center gap-2 px-8"
        >
          <Plus className="w-5 h-5" />
          <span>New Position</span>
        </button>
      </header>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
        <input
          type="text"
          placeholder="Search by title or skill..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-full bg-white/[0.03] border border-white/10 rounded-2xl pl-12 pr-6 py-3.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/40 transition-all placeholder:text-slate-600"
        />
        {search && (
          <button onClick={() => setSearch('')} className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white transition-colors">
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* List */}
      {loading ? (
        <div className="grid gap-4">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="h-28 bg-white/[0.02] border border-white/5 rounded-3xl animate-pulse" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-32 bg-white/[0.01] rounded-[2rem] border border-dashed border-white/10">
          <Briefcase className="w-14 h-14 text-slate-700 mb-4" />
          <p className="text-slate-500 font-medium text-lg mb-2">No job postings found</p>
          <p className="text-slate-600 text-sm">
            {search ? 'Try a different search term.' : 'Create your first position to get started.'}
          </p>
          {!search && (
            <button onClick={() => setShowModal(true)} className="mt-6 btn-primary px-6 py-2.5 text-sm">
              Post a Position
            </button>
          )}
        </div>
      ) : (
        <div className="grid gap-4">
          {filtered.map((job, i) => (
            <Link
              to={`/job/${job.id}`}
              key={job.id}
              className="group flex items-center justify-between p-6 rounded-3xl bg-white/[0.02] border border-white/5 hover:bg-white/[0.04] hover:border-blue-500/30 transition-all duration-300 animate-in fade-in slide-in-from-bottom-2"
              style={{ animationDelay: `${i * 60}ms` }}
            >
              <div className="flex items-center gap-6">
                <div className="w-14 h-14 bg-white/5 rounded-2xl flex items-center justify-center text-slate-500 group-hover:bg-blue-600/10 group-hover:text-blue-400 transition-all border border-white/5 group-hover:border-blue-500/20 flex-shrink-0">
                  <Briefcase className="w-7 h-7" />
                </div>
                <div>
                  <h4 className="text-lg font-bold text-slate-100 group-hover:text-blue-400 transition-all mb-2">
                    {job.title}
                  </h4>
                  <div className="flex items-center flex-wrap gap-2">
                    {(job.required_skills || []).slice(0, 5).map(skill => (
                      <span key={skill} className="px-2.5 py-0.5 rounded-lg bg-white/5 text-slate-400 text-[10px] font-bold uppercase tracking-wide border border-white/5 group-hover:border-blue-500/10 group-hover:text-slate-300 transition-all">
                        {skill}
                      </span>
                    ))}
                    {(job.required_skills || []).length > 5 && (
                      <span className="text-[10px] text-slate-600 font-medium">+{job.required_skills.length - 5} more</span>
                    )}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-6 flex-shrink-0">
                <div className="text-right hidden md:block">
                  <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">Experience</p>
                  <span className="text-sm font-bold text-white">{job.min_experience}+ yrs</span>
                </div>
                <div className="text-right hidden lg:block">
                  <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">Education</p>
                  <span className="text-xs font-semibold text-slate-300">{job.required_education}</span>
                </div>
                <div className="text-right hidden sm:block">
                  <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">Status</p>
                  <span className="text-xs font-bold text-emerald-500">Active</span>
                </div>
                <div className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center group-hover:translate-x-1 transition-transform border border-white/5 group-hover:border-blue-500/20">
                  <ChevronRight className="w-5 h-5 text-slate-400 group-hover:text-blue-400" />
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}

      {!loading && filtered.length > 0 && (
        <p className="text-center text-xs text-slate-600 font-medium pt-2">
          Showing <span className="text-slate-400 font-bold">{filtered.length}</span> of <span className="text-slate-400 font-bold">{jobs.length}</span> positions
        </p>
      )}
    </div>
  )
}
