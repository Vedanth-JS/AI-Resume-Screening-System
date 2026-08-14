import React, { useMemo } from 'react'
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  Brain,
  Clock,
  Zap,
  Shield,
  BookOpen,
  Target,
  TrendingUp,
} from 'lucide-react'

// ─── Verdict Badge ─────────────────────────────────────────────────────────────
function VerdictBadge({ verdict }) {
  const cfg = {
    ACCEPT:  { color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/30', label: '✓ Accept' },
    REVIEW:  { color: 'text-amber-400',   bg: 'bg-amber-500/10 border-amber-500/30',     label: '⚡ Review' },
    REJECT:  { color: 'text-red-400',     bg: 'bg-red-500/10 border-red-500/30',         label: '✕ Reject' },
  }[verdict?.toUpperCase()] ?? { color: 'text-slate-400', bg: 'bg-slate-500/10 border-slate-500/30', label: verdict ?? 'Pending' }

  return (
    <span className={`px-3 py-1 rounded-full border text-xs font-bold uppercase tracking-widest ${cfg.color} ${cfg.bg}`}>
      {cfg.label}
    </span>
  )
}

// ─── Skill Tag ────────────────────────────────────────────────────────────────
function SkillTag({ skill, matched }) {
  return matched ? (
    <span className="inline-flex items-center gap-1 px-3 py-1 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-medium">
      <CheckCircle className="w-3 h-3" /> {skill}
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 px-3 py-1 rounded-lg bg-red-500/10 text-red-400 border border-red-500/20 text-xs font-medium">
      <XCircle className="w-3 h-3" /> {skill}
    </span>
  )
}

// ─── Custom Radar Tooltip ──────────────────────────────────────────────────────
function RadarTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const { subject, value } = payload[0].payload
  return (
    <div className="bg-slate-800 border border-white/10 rounded-xl px-4 py-3 shadow-2xl">
      <p className="text-slate-400 text-xs font-semibold uppercase tracking-wider">{subject}</p>
      <p className="text-white text-xl font-bold mt-1">{value?.toFixed(1)}%</p>
    </div>
  )
}

// ─── Score Component Card ─────────────────────────────────────────────────────
function ScoreCard({ label, score, icon: Icon, color, weight }) {
  const pct = Math.round(score ?? 0)
  const barColor = pct >= 70 ? '#10b981' : pct >= 40 ? '#f59e0b' : '#ef4444'
  return (
    <div className="flex items-center gap-4 p-3 rounded-xl bg-white/[0.03] border border-white/5 hover:bg-white/[0.06] transition-all">
      <div className="p-2 rounded-lg bg-slate-700/50">
        <Icon className={`w-4 h-4 ${color}`} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-xs font-semibold text-slate-300 truncate">{label}</span>
          <span className="text-xs font-bold text-white ml-2">{pct}%</span>
        </div>
        <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-700 ease-out"
            style={{ width: `${pct}%`, backgroundColor: barColor }}
          />
        </div>
        {weight && (
          <span className="text-[10px] text-slate-500 mt-0.5 block">Weight: {(weight * 100).toFixed(0)}%</span>
        )}
      </div>
    </div>
  )
}

// ─── Main ResultViewer ─────────────────────────────────────────────────────────
export function ResultViewer({ result }) {
  if (!result) return null

  // Support both old format (final_result/skill_analysis) and new pipeline format (breakdown/xai)
  const isNewFormat = Boolean(result.breakdown || result.score !== undefined)

  // ── New pipeline format (from ATSWorkflow) ─────────────────────────────────
  if (isNewFormat) {
    const breakdown = result.breakdown ?? {}
    const xai = breakdown.xai ?? result.xai ?? {}
    const candidate = result.candidate ?? {}
    const kw = breakdown.keyword_detail ?? {}
    const matched = kw.matched ?? xai.matched_skills ?? []
    const missing = kw.missing ?? xai.missing_skills ?? []
    const redFlags = xai.red_flags ?? []

    const radarData = [
      { subject: 'Keywords',   value: (breakdown.keyword_score   ?? 0) },
      { subject: 'Semantic',   value: (breakdown.semantic_score  ?? 0) },
      { subject: 'Format',     value: (breakdown.format_score    ?? 0) },
      { subject: 'Sections',   value: (breakdown.section_score   ?? 0) },
      { subject: 'Experience', value: (breakdown.experience_score ?? 0) },
    ]

    const scoreCards = [
      { label: 'Keyword Match',     score: breakdown.keyword_score,   icon: Zap,      color: 'text-blue-400',    weight: 0.30 },
      { label: 'Semantic Align',    score: breakdown.semantic_score,  icon: Brain,    color: 'text-purple-400',  weight: 0.40 },
      { label: 'Resume Format',     score: breakdown.format_score,    icon: BookOpen, color: 'text-amber-400',   weight: 0.15 },
      { label: 'Section Coverage',  score: breakdown.section_score,   icon: Target,   color: 'text-cyan-400',    weight: 0.10 },
      { label: 'Experience',        score: breakdown.experience_score, icon: Clock,    color: 'text-emerald-400', weight: 0.10 },
    ]

    const overallScore = result.score ?? breakdown.overall_score ?? 0
    const verdict = xai.verdict ?? (overallScore >= 70 ? 'ACCEPT' : overallScore >= 40 ? 'REVIEW' : 'REJECT')
    const reasoning = xai.reasoning ?? {}
    const strengths = xai.key_strengths ?? []
    const gaps = xai.key_gaps ?? []

    return (
      <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700">

        {/* ── Header: Score + Verdict ──────────────────────────────────────── */}
        <div className="glass-card p-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
          <div className="flex items-center gap-6">
            {/* Circular score gauge */}
            <div className="relative w-24 h-24 shrink-0">
              <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
                <circle cx="50" cy="50" r="42" strokeWidth="8" fill="transparent"
                  className="stroke-white/5" />
                <circle cx="50" cy="50" r="42" strokeWidth="8" fill="transparent"
                  strokeDasharray={264}
                  strokeDashoffset={264 - (overallScore / 100) * 264}
                  className="transition-all duration-1000 ease-out"
                  stroke={overallScore >= 70 ? '#10b981' : overallScore >= 40 ? '#f59e0b' : '#ef4444'}
                  strokeLinecap="round"
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-2xl font-black">{Math.round(overallScore)}</span>
              </div>
            </div>

            <div>
              <h2 className="text-2xl font-bold leading-tight">{candidate.name || 'Candidate'}</h2>
              {candidate.email && <p className="text-slate-400 text-sm mt-0.5">{candidate.email}</p>}
              <div className="flex flex-wrap gap-2 mt-2">
                <VerdictBadge verdict={verdict} />
                {candidate.total_years_experience && (
                  <span className="px-2 py-0.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-semibold">
                    {candidate.total_years_experience}y exp
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* XAI recommendation */}
          {xai.hiring_recommendation && (
            <div className="max-w-md glass p-4 rounded-2xl border border-white/5">
              <p className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-1">AI Recommendation</p>
              <p className="text-slate-300 text-sm leading-relaxed italic">"{xai.hiring_recommendation}"</p>
            </div>
          )}
        </div>

        {/* ── Score Radar + Component Breakdown ──────────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* RadarChart */}
          <div className="glass-card p-6">
            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-4">Score Radar</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData} margin={{ top: 10, right: 30, bottom: 10, left: 30 }}>
                  <PolarGrid stroke="rgba(255,255,255,0.06)" />
                  <PolarAngleAxis
                    dataKey="subject"
                    tick={{ fill: '#94a3b8', fontSize: 11, fontWeight: 600 }}
                  />
                  <PolarRadiusAxis
                    angle={90}
                    domain={[0, 100]}
                    tick={{ fill: '#475569', fontSize: 9 }}
                    tickCount={5}
                  />
                  <Radar
                    name="Score"
                    dataKey="value"
                    stroke="#6366f1"
                    fill="#6366f1"
                    fillOpacity={0.25}
                    strokeWidth={2}
                    dot={{ r: 4, fill: '#818cf8', strokeWidth: 0 }}
                  />
                  <Tooltip content={<RadarTooltip />} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Score component cards */}
          <div className="glass-card p-6">
            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-4">Component Breakdown</h3>
            <div className="space-y-3">
              {scoreCards.map((c) => <ScoreCard key={c.label} {...c} />)}
            </div>
          </div>
        </div>

        {/* ── Skills Grid ─────────────────────────────────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* Matched skills */}
          <div className="glass-card p-6">
            <div className="flex items-center gap-2 mb-4">
              <CheckCircle className="w-5 h-5 text-emerald-400" />
              <h3 className="text-sm font-bold text-slate-300 uppercase tracking-widest">
                Matched Skills ({matched.length})
              </h3>
            </div>
            <div className="flex flex-wrap gap-2">
              {matched.length > 0
                ? matched.map((s) => <SkillTag key={s} skill={s} matched={true} />)
                : <p className="text-slate-500 text-sm italic">No skills matched</p>
              }
            </div>
          </div>

          {/* Missing skills */}
          <div className="glass-card p-6">
            <div className="flex items-center gap-2 mb-4">
              <XCircle className="w-5 h-5 text-red-400" />
              <h3 className="text-sm font-bold text-slate-300 uppercase tracking-widest">
                Missing Skills ({missing.length})
              </h3>
            </div>
            <div className="flex flex-wrap gap-2">
              {missing.length > 0
                ? missing.map((s) => <SkillTag key={s} skill={s} matched={false} />)
                : <p className="text-slate-500 text-sm italic">No required skills missing</p>
              }
            </div>
          </div>
        </div>

        {/* ── XAI Dimension Reasoning ────────────────────────────────────── */}
        {Object.keys(reasoning).length > 0 && (
          <div className="glass-card p-6">
            <div className="flex items-center gap-2 mb-4">
              <Brain className="w-5 h-5 text-indigo-400" />
              <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest">AI Reasoning</h3>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {Object.entries(reasoning).map(([dim, text]) => (
                <div key={dim} className="p-4 rounded-xl bg-white/[0.03] border border-white/5">
                  <p className="text-xs font-bold text-indigo-400 uppercase tracking-wider mb-1.5 capitalize">{dim}</p>
                  <p className="text-slate-400 text-sm leading-relaxed">{text}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Strengths, Gaps, Red Flags ─────────────────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {strengths.length > 0 && (
            <div className="glass-card p-5">
              <div className="flex items-center gap-2 mb-3">
                <TrendingUp className="w-4 h-4 text-emerald-400" />
                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Key Strengths</h4>
              </div>
              <ul className="space-y-2">
                {strengths.map((s, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                    <span className="text-emerald-400 mt-0.5">→</span> {s}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {gaps.length > 0 && (
            <div className="glass-card p-5">
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Key Gaps</h4>
              </div>
              <ul className="space-y-2">
                {gaps.map((g, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                    <span className="text-amber-400 mt-0.5">→</span> {g}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {redFlags.length > 0 && (
            <div className="glass-card p-5 border-red-500/10">
              <div className="flex items-center gap-2 mb-3">
                <Shield className="w-4 h-4 text-red-400" />
                <h4 className="text-xs font-bold text-red-400 uppercase tracking-widest">Red Flags</h4>
              </div>
              <ul className="space-y-2">
                {redFlags.map((f, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-red-300">
                    <span className="mt-0.5">⚠</span> {f}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

      </div>
    )
  }

  // ── Legacy format fallback (old agent pipeline) ────────────────────────────
  const { final_result, skill_analysis, experience_analysis, semantic_score, llm_evaluation, candidate } = result

  const signals = [
    { label: 'Skills Match', score: (skill_analysis?.score ?? 0) * 100, icon: Zap,   color: 'text-blue-500',   bg: 'bg-blue-500/10' },
    { label: 'Experience',   score: (experience_analysis?.score ?? 0) * 100, icon: Clock,  color: 'text-purple-500', bg: 'bg-purple-500/10' },
    { label: 'Semantic',     score: semantic_score ?? 0,                icon: Brain,  color: 'text-pink-500',   bg: 'bg-pink-500/10' },
    { label: 'Education',    score: 80,                                 icon: BookOpen, color: 'text-emerald-500', bg: 'bg-emerald-500/10' },
  ]

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="glass-card flex items-center justify-between">
        <div className="flex items-center gap-6">
          <div className="relative">
            <svg className="w-24 h-24 transform -rotate-90">
              <circle cx="48" cy="48" r="40" stroke="currentColor" strokeWidth="8" fill="transparent" className="text-white/5" />
              <circle cx="48" cy="48" r="40" stroke="currentColor" strokeWidth="8" fill="transparent"
                strokeDasharray={251.2}
                strokeDashoffset={251.2 - (final_result?.final_score / 100) * 251.2}
                className="text-blue-500 transition-all duration-1000 ease-out" />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center font-bold text-2xl">
              {final_result?.final_score}%
            </div>
          </div>
          <div>
            <h2 className="text-2xl font-bold">{candidate?.name}</h2>
            <p className="text-slate-400">{candidate?.email} • {candidate?.phone}</p>
          </div>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {signals.map((signal) => (
          <div key={signal.label} className="glass p-5 rounded-2xl border border-white/5">
            <div className="flex items-center justify-between mb-3">
              <div className={`${signal.bg} p-2 rounded-lg`}>
                <signal.icon className={`w-5 h-5 ${signal.color}`} />
              </div>
              <span className="text-lg font-bold">{Math.round(signal.score)}%</span>
            </div>
            <p className="text-xs font-semibold text-slate-400">{signal.label}</p>
            <div className="mt-3 w-full h-1.5 bg-white/5 rounded-full overflow-hidden">
              <div className={`h-full ${signal.bg.replace('/10', '/50')} transition-all duration-700`} style={{ width: `${signal.score}%` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
