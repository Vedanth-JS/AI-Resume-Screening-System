import React, { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  ArrowLeft, Briefcase, Users, Loader2, AlertCircle, Brain,
  CheckCircle, ChevronRight, Zap, HelpCircle, BarChart2, Target
} from 'lucide-react'
import { Radar } from 'react-chartjs-2'
import {
  Chart as ChartJS, RadialLinearScale, PointElement,
  LineElement, Filler, Tooltip, Legend
} from 'chart.js'
import { jobService, candidateService } from '../services/api'
import { ResumeUpload } from './ResumeUpload'
import api from '../services/api'

ChartJS.register(RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend)

// ─── Score Radar ──────────────────────────────────────────────────────────────

function ScoreRadar({ result }) {
  if (!result) return null
  const { ats_breakdown = {} } = result
  const labels = ['Keyword Match', 'Semantic Fit', 'Format Quality', 'Section Complete', 'Experience']
  const values = [
    ats_breakdown.keyword_score  ?? (result.skill_analysis?.score ?? 0) * 100,
    ats_breakdown.semantic_score ?? result.semantic_score ?? 0,
    ats_breakdown.format_score   ?? 75,
    ats_breakdown.section_score  ?? 75,
    ats_breakdown.experience_score ?? (result.experience_analysis?.score ?? 0) * 100,
  ].map(v => Math.round(Math.min(v, 100)))

  const data = {
    labels,
    datasets: [{
      label: 'ATS Score Breakdown',
      data: values,
      backgroundColor: 'rgba(59,130,246,0.15)',
      borderColor: 'rgba(59,130,246,0.8)',
      borderWidth: 2,
      pointBackgroundColor: 'rgba(59,130,246,1)',
      pointBorderColor: '#fff',
      pointHoverBackgroundColor: '#fff',
      pointHoverBorderColor: 'rgba(59,130,246,1)',
    }],
  }
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      r: {
        beginAtZero: true,
        max: 100,
        ticks: { color: '#64748b', font: { size: 9 }, stepSize: 25 },
        grid:  { color: 'rgba(255,255,255,0.06)' },
        angleLines: { color: 'rgba(255,255,255,0.06)' },
        pointLabels: { color: '#94a3b8', font: { size: 10, weight: 'bold' } },
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
        callbacks: { label: ctx => ` ${ctx.label}: ${ctx.parsed.r}%` },
      },
    },
  }
  return (
    <div className="glass rounded-[2rem] p-8 border border-white/5">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-9 h-9 bg-blue-500/10 rounded-xl flex items-center justify-center border border-blue-500/20">
          <BarChart2 className="w-5 h-5 text-blue-400" />
        </div>
        <div>
          <h3 className="font-bold text-white text-sm">ATS Score Radar</h3>
          <p className="text-xs text-slate-500">5-dimension match profile</p>
        </div>
      </div>
      <div className="w-full" style={{ height: '260px' }}>
        <Radar data={data} options={options} />
      </div>
      {/* Score bars */}
      <div className="mt-6 space-y-2.5">
        {labels.map((label, i) => {
          const v = values[i]
          const color = v >= 70 ? 'bg-emerald-500' : v >= 40 ? 'bg-amber-500' : 'bg-red-500'
          return (
            <div key={label} className="flex items-center gap-3">
              <div className="w-28 text-right text-[10px] text-slate-500 font-bold flex-shrink-0">{label}</div>
              <div className="flex-1 h-1.5 bg-white/5 rounded-full overflow-hidden">
                <div className={`h-full ${color} transition-all duration-700`} style={{ width: `${v}%` }} />
              </div>
              <div className="w-10 text-right text-xs font-bold text-slate-300">{v}%</div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ─── Interview Questions ───────────────────────────────────────────────────────

function InterviewQuestions({ questions = [] }) {
  if (!questions || questions.length === 0) return null
  const typeColors = {
    technical:      'bg-blue-500/10 text-blue-400 border-blue-500/20',
    behavioral:     'bg-purple-500/10 text-purple-400 border-purple-500/20',
    situational:    'bg-amber-500/10 text-amber-400 border-amber-500/20',
    system_design:  'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  }
  return (
    <div className="glass rounded-[2rem] p-8 border border-white/5 bg-gradient-to-br from-purple-600/5 to-transparent">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-9 h-9 bg-purple-500/10 rounded-xl flex items-center justify-center border border-purple-500/20">
          <HelpCircle className="w-5 h-5 text-purple-400" />
        </div>
        <div>
          <h3 className="font-bold text-white text-sm">AI-Generated Interview Questions</h3>
          <p className="text-xs text-slate-500">Targeted based on resume gaps vs. JD requirements</p>
        </div>
      </div>
      <div className="space-y-4">
        {questions.map((q, i) => {
          const colorClass = typeColors[q.type] || typeColors.behavioral
          return (
            <div key={i} className="p-5 bg-white/[0.02] border border-white/5 rounded-2xl hover:border-purple-500/20 transition-all">
              <div className="flex items-start justify-between gap-3 mb-2">
                <span className="text-sm font-bold text-white leading-relaxed flex-1">
                  {i + 1}. {q.question}
                </span>
                <span className={`flex-shrink-0 text-[9px] font-bold uppercase tracking-widest px-2 py-1 rounded-lg border ${colorClass}`}>
                  {(q.type || 'behavioral').replace('_', ' ')}
                </span>
              </div>
              {q.rationale && (
                <p className="text-xs text-slate-500 leading-relaxed pl-4 border-l border-white/5">
                  {q.rationale}
                </p>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ─── Suggestions ──────────────────────────────────────────────────────────────

function Suggestions({ suggestions = [] }) {
  if (!suggestions || suggestions.length === 0) return null
  return (
    <div className="glass rounded-[2rem] p-8 border border-white/5">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-9 h-9 bg-amber-500/10 rounded-xl flex items-center justify-center border border-amber-500/20">
          <Target className="w-5 h-5 text-amber-400" />
        </div>
        <h3 className="font-bold text-white text-sm">Resume Improvement Suggestions</h3>
      </div>
      <ul className="space-y-3">
        {suggestions.map((s, i) => (
          <li key={i} className="flex items-start gap-3 text-sm text-slate-300">
            <span className="w-5 h-5 flex-shrink-0 rounded-full bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 text-[10px] font-bold mt-0.5">
              {i + 1}
            </span>
            {s}
          </li>
        ))}
      </ul>
    </div>
  )
}

// ─── Main JobDetail ────────────────────────────────────────────────────────────

export function JobDetail() {
  const { id } = useParams()
  const [job,        setJob]        = useState(null)
  const [history,    setHistory]    = useState([])
  const [selected,   setSelected]   = useState(null)
  const [loading,    setLoading]    = useState(true)
  const [lastResult, setLastResult] = useState(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [jobRes, histRes] = await Promise.all([
          jobService.getJob(id),
          api.get(`/history/${id}`),
        ])
        setJob(jobRes.data)
        setHistory(histRes.data || [])
      } catch (err) {
        console.error('JobDetail fetch error:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [id])

  const handleUploadComplete = (result) => {
    setLastResult(result?.analysis || result)
    // Refresh history
    api.get(`/history/${id}`).then(r => setHistory(r.data || []))
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-40">
        <Loader2 className="w-10 h-10 text-blue-500 animate-spin" />
      </div>
    )
  }

  if (!job) {
    return (
      <div className="flex flex-col items-center py-32">
        <AlertCircle className="w-12 h-12 text-red-400 mb-4" />
        <p className="text-slate-400">Job posting not found.</p>
        <Link to="/jobs" className="mt-4 text-blue-400 hover:text-blue-300 text-sm font-medium">← Back to Jobs</Link>
      </div>
    )
  }

  // Find full screening data for selected candidate
  const selectedResult = selected
    ? history.find(h => h.candidate_id === selected)
    : lastResult

  return (
    <div className="space-y-10 animate-in fade-in slide-in-from-bottom-4 duration-700">
      {/* Breadcrumb */}
      <Link to="/jobs" className="inline-flex items-center gap-2 text-slate-500 hover:text-blue-400 transition-colors text-sm font-medium">
        <ArrowLeft className="w-4 h-4" />
        Back to Jobs
      </Link>

      {/* Job Header */}
      <div className="glass-card !p-10">
        <div className="flex items-start justify-between gap-6">
          <div className="flex items-start gap-6">
            <div className="w-16 h-16 bg-blue-500/10 rounded-2xl flex items-center justify-center border border-blue-500/20 flex-shrink-0">
              <Briefcase className="w-8 h-8 text-blue-400" />
            </div>
            <div>
              <h2 className="text-3xl font-bold text-white mb-3">{job.title}</h2>
              <div className="flex flex-wrap gap-2 mb-4">
                {(job.required_skills || []).map(skill => (
                  <span key={skill} className="px-3 py-1 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded-lg text-xs font-bold uppercase tracking-wide">
                    {skill}
                  </span>
                ))}
              </div>
              <div className="flex items-center gap-4 text-sm text-slate-500">
                <span><span className="text-white font-semibold">{job.min_experience}+</span> yrs exp</span>
                <span>·</span>
                <span>{job.required_education}</span>
              </div>
            </div>
          </div>
          <div className="text-right flex-shrink-0">
            <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">Candidates</div>
            <div className="text-4xl font-bold text-white">{history.length}</div>
          </div>
        </div>
        {job.description && (
          <div className="mt-8 pt-8 border-t border-white/5">
            <p className="text-xs font-bold uppercase tracking-widest text-slate-500 mb-3">Job Description</p>
            <p className="text-sm text-slate-400 leading-relaxed">{job.description}</p>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-5 gap-8">
        {/* Upload + Candidate list */}
        <div className="xl:col-span-2 space-y-6">
          <ResumeUpload jobId={id} onComplete={handleUploadComplete} />

          {/* Candidate list */}
          {history.length > 0 && (
            <div className="glass rounded-[2rem] p-6 border border-white/5">
              <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
                <Users className="w-4 h-4 text-blue-400" />
                Screened Candidates ({history.length})
              </h3>
              <div className="space-y-2">
                {history
                  .sort((a, b) => (b.final_score || 0) - (a.final_score || 0))
                  .map(h => {
                    const score = h.final_score ?? 0
                    const color = score >= 70 ? 'text-emerald-400' : score >= 40 ? 'text-amber-400' : 'text-red-400'
                    const bg = score >= 70 ? 'hover:border-emerald-500/30' : score >= 40 ? 'hover:border-amber-500/30' : 'hover:border-red-500/30'
                    return (
                      <div key={h.candidate_id} className="relative group/parent">
                        <button
                          onClick={() => setSelected(h.candidate_id)}
                          className={`w-full flex items-center justify-between px-4 py-3 rounded-xl bg-white/[0.02] border border-white/5 ${bg} transition-all text-left group ${selected === h.candidate_id ? 'border-blue-500/40 bg-blue-500/5' : ''}`}
                        >
                          <div>
                            <p className="text-sm font-semibold text-slate-200 group-hover:text-white">{h.candidate_name}</p>
                            <p className="text-xs text-slate-600">{new Date(h.created_at || Date.now()).toLocaleDateString()}</p>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className={`text-lg font-bold ${color}`}>{Math.round(score)}%</span>
                            <ChevronRight className="w-4 h-4 text-slate-600 group-hover:text-slate-300" />
                          </div>
                        </button>
                        {selected === h.candidate_id && (
                          <div className="flex gap-2 mt-2 px-2 animate-in slide-in-from-top-2 duration-300">
                             <Link 
                               to={`/interview/${h.candidate_id}?job_id=${id}`}
                               className="flex-1 py-2 rounded-lg bg-blue-500/10 border border-blue-500/20 text-[10px] font-bold text-blue-400 text-center uppercase tracking-widest hover:bg-blue-500/20 transition-all"
                             >
                               Launch Interview
                             </Link>
                          </div>
                        )}
                      </div>
                    )
                  })}
                {history.length >= 2 && (
                   <Link 
                     to={`/compare/${id}?ids=${history.slice(0,3).map(h => h.candidate_id).join(',')}`}
                     className="block w-full mt-4 py-3 rounded-xl bg-white/5 border border-white/10 text-xs font-bold text-slate-400 text-center uppercase tracking-widest hover:bg-white/10 transition-colors"
                   >
                     Compare Top 3 Candidates
                   </Link>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Results Panel */}
        <div className="xl:col-span-3 space-y-6">
          {selectedResult ? (
            <>
              <ScoreRadar result={selectedResult} />
              <InterviewQuestions questions={selectedResult.interview_questions || []} />
              <Suggestions suggestions={selectedResult.suggestions || selectedResult.ats_breakdown?.suggestions || []} />
              {/* LLM Evaluation */}
              {selectedResult.llm_evaluation && (
                <div className="glass rounded-[2rem] p-8 border border-white/5 bg-gradient-to-br from-blue-600/5 to-transparent">
                  <div className="flex items-center gap-3 mb-6">
                    <div className="w-9 h-9 bg-blue-500/10 rounded-xl flex items-center justify-center border border-blue-500/20">
                      <Brain className="w-5 h-5 text-blue-400" />
                    </div>
                    <h3 className="font-bold text-white text-sm">AI Evaluation</h3>
                  </div>
                  <div className="space-y-3">
                    {(selectedResult.llm_evaluation || '').split('\n').filter(Boolean).map((line, i) => (
                      <p key={i} className="text-sm text-slate-400 leading-relaxed">{line}</p>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="glass rounded-[2rem] p-16 border border-dashed border-white/10 flex flex-col items-center justify-center text-center">
              <Zap className="w-14 h-14 text-slate-700 mb-6" />
              <h3 className="text-lg font-bold text-slate-400 mb-2">Upload a resume to begin</h3>
              <p className="text-slate-600 text-sm max-w-xs leading-relaxed">
                The 5-agent AI pipeline will analyse the candidate and show their radar chart, interview questions, and improvement suggestions here.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
