import React, { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Briefcase, Users, FileText, ChevronRight, Zap, Target, Award, BrainCircuit } from 'lucide-react'
import { jobService } from '../services/api'
import api from '../services/api'
import { ResumeUpload } from './ResumeUpload'
import { ResultViewer } from './ResultViewer'

export function JobDetail() {
  const { id } = useParams()
  const [job, setJob] = useState(null)
  const [candidates, setCandidates] = useState([])
  const [selectedResult, setSelectedResult] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchJobData = async () => {
      try {
        const [jobRes, candidatesRes] = await Promise.all([
          jobService.getJob(id),
          api.get(`/history/${id}`) 
        ])
        setJob(jobRes.data)
        setCandidates(candidatesRes.data || [])
      } catch (err) {
        console.error("Job detail fetch error:", err)
      } finally {
        setLoading(false)
      }
    }
    fetchJobData()
  }, [id])

  if (loading) return (
    <div className="h-screen flex items-center justify-center -mt-20">
      <div className="w-16 h-16 border-4 border-blue-500/10 border-t-blue-500 rounded-full animate-spin shadow-[0_0_20px_rgba(59,130,246,0.2)]" />
    </div>
  )

  return (
    <div className="space-y-12 animate-in fade-in slide-in-from-right-6 duration-1000">
      {/* Breadcrumbs & Header */}
      <header>
        <Link to="/" className="group flex items-center gap-2 text-slate-500 hover:text-blue-400 transition-all text-sm mb-6 font-medium">
          <ArrowLeft className="w-4 h-4 transition-transform group-hover:-translate-x-1" />
          Back to Dashboard
        </Link>
        <div className="flex items-center justify-between">
           <div className="flex items-center gap-8">
              <div className="w-20 h-20 bg-blue-500/10 rounded-3xl flex items-center justify-center border border-blue-500/20 shadow-blue-500/5 shadow-2xl relative">
                <Briefcase className="w-10 h-10 text-blue-500" />
                <div className="absolute -top-1 -right-1 w-4 h-4 bg-emerald-500 rounded-full border-4 border-[#0a0a0b] shadow-lg shadow-emerald-500/20" />
              </div>
              <div>
                <h2 className="text-4xl font-bold tracking-tight text-white mb-2">{job?.title}</h2>
                <div className="flex items-center gap-4 text-slate-400 font-medium">
                   <div className="flex items-center gap-1.5 px-3 py-1 bg-white/5 rounded-lg border border-white/5">
                      <Award className="w-3.5 h-3.5 text-blue-400" />
                      <span className="text-xs uppercase tracking-wider">{job?.required_education}</span>
                   </div>
                   <span className="w-1 h-1 rounded-full bg-slate-700" />
                   <div className="flex items-center gap-1.5 px-3 py-1 bg-white/5 rounded-lg border border-white/5">
                      <Target className="w-3.5 h-3.5 text-blue-400" />
                      <span className="text-xs uppercase tracking-wider">{job?.min_experience}+ Years Exp</span>
                   </div>
                </div>
              </div>
           </div>
           <div className="flex items-center gap-4">
              <div className="px-6 py-3 rounded-2xl glass border-emerald-500/10 shadow-emerald-500/5 group hover:border-emerald-500/20 transition-all">
                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">Qualified Hires</p>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-emerald-500 shadow-emerald-500/50 shadow-[0_0_8px]" />
                  <span className="text-xl font-bold text-white">{candidates.length}</span>
                </div>
              </div>
           </div>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-10">
        {/* Left Column: Role Details & Actions */}
        <div className="space-y-8">
           <div className="glass rounded-[2.5rem] p-8 border border-white/5">
              <h3 className="text-lg font-bold mb-6 flex items-center gap-3">
                 <BrainCircuit className="w-5 h-5 text-blue-400" />
                 Contextual Analysis
              </h3>
              <p className="text-sm text-slate-400 leading-relaxed mb-10">
                {job?.description}
              </p>
              
              <h3 className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500 mb-6">Semantic Filter Stack</h3>
              <div className="flex flex-wrap gap-2.5">
                 {job?.required_skills.map(skill => (
                   <span key={skill} className="px-4 py-2 bg-white/5 rounded-xl border border-white/5 text-xs text-slate-300 hover:bg-blue-600/10 hover:text-blue-400 hover:border-blue-500/10 transition-all duration-300">
                     {skill}
                   </span>
                 ))}
              </div>
           </div>

           <ResumeUpload jobId={id} onComplete={() => window.location.reload()} />
        </div>

        {/* Right Column: Candidate Matching Index */}
        <div className="lg:col-span-2">
           {selectedResult ? (
             <div className="space-y-6">
                <button 
                  onClick={() => setSelectedResult(null)}
                  className="px-6 py-3 bg-white/5 hover:bg-white/10 rounded-2xl text-xs font-bold transition-all border border-white/5 uppercase tracking-widest text-blue-400 shadow-lg"
                >
                  Close Match Viewer
                </button>
                <ResultViewer result={selectedResult} />
             </div>
           ) : (
             <div className="glass rounded-[2.5rem] p-10 border border-white/5 min-h-[600px] flex flex-col">
                <div className="flex items-center justify-between mb-10">
                  <header>
                    <h3 className="text-2xl font-bold mb-1 text-white">Matching Index</h3>
                    <p className="text-xs text-slate-500 font-medium uppercase tracking-widest">Neural Ranking Pipeline</p>
                  </header>
                  <div className="flex items-center gap-2 px-4 py-2 bg-blue-600/10 rounded-xl border border-blue-500/20">
                     <Zap className="w-4 h-4 text-blue-400 animate-pulse" />
                     <span className="text-[10px] font-bold text-blue-400 uppercase tracking-widest mt-0.5">Automated Matcher Online</span>
                  </div>
                </div>

                <div className="space-y-4 flex-1">
                   {candidates.length === 0 ? (
                     <div className="flex-1 flex flex-col items-center justify-center py-20 bg-white/[0.01] rounded-[2rem] border border-dashed border-white/10">
                        <FileText className="w-16 h-16 text-slate-800 mx-auto mb-6" />
                        <p className="text-slate-500 font-medium">Capture incoming resumes to populate Neural Matching.</p>
                     </div>
                   ) : (
                     candidates.sort((a,b) => b.final_score - a.final_score).map((cand, i) => (
                       <div 
                        key={cand.id} 
                        onClick={() => setSelectedResult(cand.analysis)} 
                        className="group flex items-center justify-between p-6 rounded-3xl bg-white/[0.02] border border-white/5 hover:bg-blue-600/5 hover:border-blue-500/40 transition-all duration-300 cursor-pointer animate-in fade-in slide-in-from-right-4"
                        style={{ animationDelay: `${i * 100}ms` }}
                       >
                          <div className="flex items-center gap-6">
                             <div className="w-14 h-14 rounded-2xl bg-slate-900 flex items-center justify-center font-bold text-blue-500 border border-white/5 group-hover:border-blue-500/20 shadow-inner group-hover:bg-blue-500/10 transition-all">
                                {cand.candidate_name?.[0] || 'C'}
                             </div>
                             <div>
                                <h4 className="text-lg font-bold group-hover:text-blue-400 transition-all text-white mb-1">{cand.candidate_name || `Ref #${cand.candidate_id}`}</h4>
                                <div className="flex items-center gap-2">
                                  <div className="w-1.5 h-1.5 rounded-full bg-blue-500/50" />
                                  <p className="text-xs text-slate-500 font-medium tracking-wide">Processed {new Date(cand.created_at).toLocaleDateString()}</p>
                                </div>
                             </div>
                          </div>
                          <div className="flex items-center gap-8">
                             <div className="text-right">
                                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em] mb-2">Neural Match</p>
                                <div className="flex items-center gap-2.5">
                                   <div className="w-16 h-1.5 bg-white/5 rounded-full overflow-hidden border border-white/5">
                                      <div className="h-full bg-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.5)]" style={{ width: `${cand.final_score}%` }} />
                                   </div>
                                   <span className="text-2xl font-bold font-display text-white">{cand.final_score}%</span>
                                </div>
                             </div>
                             <div className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center border border-white/5 group-hover:translate-x-1 transition-transform group-hover:border-blue-500/20">
                                <ChevronRight className="w-5 h-5 text-slate-600 group-hover:text-blue-400" />
                             </div>
                          </div>
                       </div>
                     ))
                   )}
                </div>
             </div>
           )}
        </div>
      </div>
    </div>
  )
}
