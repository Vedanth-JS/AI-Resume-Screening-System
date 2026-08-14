import React, { useState, useCallback, useEffect } from 'react'
import { Search, RefreshCw, ChevronUp, ChevronDown, Trophy, AlertTriangle, CheckCircle, XCircle } from 'lucide-react'
import { jobService } from '@/services/api'
import axios from 'axios'

interface MatchedCandidate {
  id: number
  name: string
  email: string
  score: number
  keyword_score?: number
  semantic_score?: number
  matched_skills?: string[]
  missing_skills?: string[]
  verdict?: string
  rank?: number
}

interface Job {
  id: number
  title: string
  description: string
}

function VerdictBadge({ verdict }: { verdict?: string }) {
  const cfg: Record<string, { color: string; bg: string }> = {
    ACCEPT: { color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/30' },
    REVIEW: { color: 'text-amber-400',   bg: 'bg-amber-500/10 border-amber-500/30' },
    REJECT: { color: 'text-red-400',     bg: 'bg-red-500/10 border-red-500/30' },
  }
  const key = verdict?.toUpperCase() ?? 'REVIEW'
  const style = cfg[key] ?? cfg.REVIEW
  return (
    <span className={`px-2 py-0.5 rounded-full border text-[10px] font-bold uppercase tracking-widest ${style.color} ${style.bg}`}>
      {verdict ?? 'Review'}
    </span>
  )
}

function ScoreMeter({ score, label }: { score: number; label: string }) {
  const color = score >= 70 ? '#10b981' : score >= 40 ? '#f59e0b' : '#ef4444'
  return (
    <div className="flex flex-col items-center gap-1">
      <div className="w-10 h-10 rounded-full flex items-center justify-center border-2"
        style={{ borderColor: color, color }}>
        <span className="text-xs font-bold">{Math.round(score)}</span>
      </div>
      <span className="text-[10px] text-slate-500 text-center leading-tight">{label}</span>
    </div>
  )
}

export default function JDComparisonPage() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null)
  const [candidates, setCandidates] = useState<MatchedCandidate[]>([])
  const [loading, setLoading] = useState(false)
  const [sortField, setSortField] = useState<'score' | 'keyword_score' | 'semantic_score'>('score')
  const [sortDir, setSortDir] = useState<'desc' | 'asc'>('desc')
  const [searchQuery, setSearchQuery] = useState('')
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null)

  // Load jobs on mount
  useEffect(() => {
    jobService.getJobs()
      .then(res => {
        const items = res.data?.items ?? res.data ?? []
        setJobs(items)
        if (items.length > 0) setSelectedJobId(items[0].id)
      })
      .catch(console.error)
  }, [])

  // Fetch ranked candidates when job changes
  const fetchRanking = useCallback(async () => {
    if (!selectedJobId) return
    setLoading(true)
    try {
      // Use the match-candidates endpoint
      const token = localStorage.getItem('access_token')
      const res = await axios.post(
        `/api/jobs/${selectedJobId}/match-candidates`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      )
      const raw: any[] = res.data?.candidates ?? []
      const ranked: MatchedCandidate[] = raw.map((c, i) => ({
        id: c.id ?? c.candidate_id,
        name: c.name ?? 'Unknown',
        email: c.email ?? '',
        score: c.score ?? c.similarity_score ?? 0,
        keyword_score: c.keyword_score,
        semantic_score: c.semantic_score,
        matched_skills: c.matched_skills ?? [],
        missing_skills: c.missing_skills ?? [],
        verdict: c.verdict,
        rank: i + 1,
      }))
      setCandidates(ranked)
      setLastRefreshed(new Date())
    } catch (err) {
      console.error('Failed to fetch ranking', err)
    } finally {
      setLoading(false)
    }
  }, [selectedJobId])

  useEffect(() => {
    fetchRanking()
  }, [fetchRanking])

  // Sorting
  const handleSort = (field: typeof sortField) => {
    if (field === sortField) {
      setSortDir(d => d === 'desc' ? 'asc' : 'desc')
    } else {
      setSortField(field)
      setSortDir('desc')
    }
  }

  const sorted = [...candidates]
    .filter(c => !searchQuery || c.name.toLowerCase().includes(searchQuery.toLowerCase()) || c.email.toLowerCase().includes(searchQuery.toLowerCase()))
    .sort((a, b) => {
      const va = (a[sortField] ?? 0) as number
      const vb = (b[sortField] ?? 0) as number
      return sortDir === 'desc' ? vb - va : va - vb
    })

  const SortIcon = ({ field }: { field: string }) => {
    if (field !== sortField) return null
    return sortDir === 'desc' ? <ChevronDown className="w-3 h-3 inline ml-1" /> : <ChevronUp className="w-3 h-3 inline ml-1" />
  }

  const selectedJob = jobs.find(j => j.id === selectedJobId)

  return (
    <div className="max-w-7xl mx-auto space-y-8 pb-20">
      {/* Header */}
      <div className="text-center space-y-3">
        <h1 className="text-4xl font-bold font-display tracking-tight">JD Comparison View</h1>
        <p className="text-slate-400 max-w-xl mx-auto">
          Select a job, see all candidates ranked by semantic + keyword alignment in real time.
        </p>
      </div>

      {/* Job selector + controls */}
      <div className="glass-card p-5 flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div className="flex-1">
          <label className="text-xs font-bold text-slate-500 uppercase tracking-widest block mb-1.5">
            Select Job Posting
          </label>
          <select
            id="jd-comparison-job-select"
            className="w-full sm:w-80 bg-slate-800 border border-white/10 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            value={selectedJobId ?? ''}
            onChange={e => setSelectedJobId(Number(e.target.value))}
          >
            {jobs.map(j => (
              <option key={j.id} value={j.id}>{j.title}</option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-3">
          {lastRefreshed && (
            <span className="text-xs text-slate-500">
              Updated {lastRefreshed.toLocaleTimeString()}
            </span>
          )}
          <button
            id="jd-comparison-refresh-btn"
            onClick={fetchRanking}
            disabled={loading}
            className="btn-secondary flex items-center gap-2 text-sm px-4 py-2 rounded-xl"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Search bar */}
      <div className="relative">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
        <input
          id="jd-comparison-search"
          type="text"
          placeholder="Filter by name or email…"
          className="w-full bg-slate-800/50 border border-white/10 rounded-xl pl-10 pr-4 py-3 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 placeholder-slate-600"
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
        />
      </div>

      {/* Summary stats */}
      {sorted.length > 0 && (
        <div className="grid grid-cols-3 sm:grid-cols-5 gap-3">
          {[
            { label: 'Total', value: sorted.length, color: 'text-slate-300' },
            { label: 'Accept (≥70)', value: sorted.filter(c => c.score >= 70).length, color: 'text-emerald-400' },
            { label: 'Review (40-70)', value: sorted.filter(c => c.score >= 40 && c.score < 70).length, color: 'text-amber-400' },
            { label: 'Reject (<40)', value: sorted.filter(c => c.score < 40).length, color: 'text-red-400' },
            { label: 'Avg Score', value: `${(sorted.reduce((s, c) => s + c.score, 0) / sorted.length).toFixed(1)}%`, color: 'text-indigo-400' },
          ].map(stat => (
            <div key={stat.label} className="glass-card p-4 text-center">
              <p className={`text-2xl font-black ${stat.color}`}>{stat.value}</p>
              <p className="text-xs text-slate-500 mt-1">{stat.label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Ranking Table */}
      <div className="glass-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/5">
                <th className="text-left px-5 py-3 text-xs font-bold text-slate-500 uppercase tracking-widest w-12">#</th>
                <th className="text-left px-5 py-3 text-xs font-bold text-slate-500 uppercase tracking-widest">Candidate</th>
                <th
                  className="text-center px-4 py-3 text-xs font-bold text-slate-500 uppercase tracking-widest cursor-pointer hover:text-white transition-colors"
                  onClick={() => handleSort('score')}
                >
                  Total Score <SortIcon field="score" />
                </th>
                <th
                  className="text-center px-4 py-3 text-xs font-bold text-slate-500 uppercase tracking-widest cursor-pointer hover:text-white transition-colors"
                  onClick={() => handleSort('keyword_score')}
                >
                  Keywords <SortIcon field="keyword_score" />
                </th>
                <th
                  className="text-center px-4 py-3 text-xs font-bold text-slate-500 uppercase tracking-widest cursor-pointer hover:text-white transition-colors"
                  onClick={() => handleSort('semantic_score')}
                >
                  Semantic <SortIcon field="semantic_score" />
                </th>
                <th className="text-left px-5 py-3 text-xs font-bold text-slate-500 uppercase tracking-widest">Matched Skills</th>
                <th className="text-left px-5 py-3 text-xs font-bold text-slate-500 uppercase tracking-widest">Missing</th>
                <th className="text-center px-4 py-3 text-xs font-bold text-slate-500 uppercase tracking-widest">Verdict</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={8} className="text-center py-16 text-slate-500">
                    <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-3 text-indigo-400" />
                    <p>Ranking candidates…</p>
                  </td>
                </tr>
              )}
              {!loading && sorted.length === 0 && (
                <tr>
                  <td colSpan={8} className="text-center py-16 text-slate-500">
                    No candidates found for this job. Upload some resumes first.
                  </td>
                </tr>
              )}
              {!loading && sorted.map((cand, idx) => {
                const rankBadge = idx === 0 ? '🥇' : idx === 1 ? '🥈' : idx === 2 ? '🥉' : `${idx + 1}`
                const scoreColor = cand.score >= 70 ? 'text-emerald-400' : cand.score >= 40 ? 'text-amber-400' : 'text-red-400'
                return (
                  <tr
                    key={cand.id}
                    className="border-b border-white/[0.04] hover:bg-white/[0.03] transition-colors"
                  >
                    <td className="px-5 py-4 text-lg">{rankBadge}</td>
                    <td className="px-5 py-4">
                      <p className="font-semibold text-white">{cand.name}</p>
                      <p className="text-slate-500 text-xs">{cand.email}</p>
                    </td>
                    <td className="px-4 py-4 text-center">
                      <span className={`text-xl font-black ${scoreColor}`}>
                        {Math.round(cand.score)}
                      </span>
                      <span className="text-xs text-slate-500 ml-0.5">%</span>
                    </td>
                    <td className="px-4 py-4 text-center text-slate-300 font-semibold">
                      {cand.keyword_score != null ? `${Math.round(cand.keyword_score)}%` : '—'}
                    </td>
                    <td className="px-4 py-4 text-center text-slate-300 font-semibold">
                      {cand.semantic_score != null ? `${Math.round(cand.semantic_score)}%` : '—'}
                    </td>
                    <td className="px-5 py-4">
                      <div className="flex flex-wrap gap-1 max-w-[200px]">
                        {(cand.matched_skills ?? []).slice(0, 3).map(s => (
                          <span key={s} className="inline-flex items-center gap-0.5 px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-medium">
                            <CheckCircle className="w-2.5 h-2.5" /> {s}
                          </span>
                        ))}
                        {(cand.matched_skills?.length ?? 0) > 3 && (
                          <span className="text-[10px] text-slate-500">+{(cand.matched_skills?.length ?? 0) - 3}</span>
                        )}
                      </div>
                    </td>
                    <td className="px-5 py-4">
                      <div className="flex flex-wrap gap-1 max-w-[160px]">
                        {(cand.missing_skills ?? []).slice(0, 2).map(s => (
                          <span key={s} className="inline-flex items-center gap-0.5 px-2 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20 text-[10px] font-medium">
                            <XCircle className="w-2.5 h-2.5" /> {s}
                          </span>
                        ))}
                        {(cand.missing_skills?.length ?? 0) > 2 && (
                          <span className="text-[10px] text-slate-500">+{(cand.missing_skills?.length ?? 0) - 2}</span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-4 text-center">
                      <VerdictBadge verdict={cand.verdict} />
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
