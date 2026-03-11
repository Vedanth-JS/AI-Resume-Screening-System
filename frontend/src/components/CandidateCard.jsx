import { CheckCircle2, XCircle, AlertCircle, ChevronRight, Star } from 'lucide-react'

const RECOMMENDATION_CONFIG = {
  'Strong Fit': {
    badge: 'badge-strong',
    icon: CheckCircle2,
    glow: 'ring-1 ring-emerald-200',
    barColor: 'bg-emerald-500',
  },
  'Maybe': {
    badge: 'badge-maybe',
    icon: AlertCircle,
    glow: 'ring-1 ring-amber-200',
    barColor: 'bg-amber-500',
  },
  'Reject': {
    badge: 'badge-reject',
    icon: XCircle,
    glow: '',
    barColor: 'bg-red-400',
  },
}

function ScoreRing({ score }) {
  const radius = 28
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (score / 100) * circumference
  const color = score >= 75 ? '#10b981' : score >= 50 ? '#f59e0b' : '#f87171'

  return (
    <div className="relative w-20 h-20 flex-shrink-0">
      <svg width="80" height="80" className="-rotate-90">
        <circle cx="40" cy="40" r={radius} fill="none" stroke="#E2E8F3" strokeWidth="6" />
        <circle
          cx="40" cy="40" r={radius} fill="none"
          stroke={color} strokeWidth="6"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 0.8s ease' }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-xl font-bold text-navy-800 leading-none">{Math.round(score)}</span>
        <span className="text-[10px] text-navy-400 font-medium">/ 100</span>
      </div>
    </div>
  )
}

export default function CandidateCard({ screening, onClick }) {
  const rec = screening.recommendation
  const config = RECOMMENDATION_CONFIG[rec] || RECOMMENDATION_CONFIG['Reject']
  const Icon = config.icon

  const name = screening.candidate?.name || 'Unknown Candidate'
  const email = screening.candidate?.email || ''
  const filename = screening.candidate?.original_filename || ''

  return (
    <div
      className={`card cursor-pointer hover:scale-[1.01] transition-all duration-200 ${config.glow}`}
      onClick={() => onClick(screening)}
    >
      <div className="flex items-start gap-5">
        {/* Score Ring */}
        <ScoreRing score={screening.score} />

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2 mb-1">
            <div>
              <h3 className="font-serif font-semibold text-navy-800 text-base leading-tight truncate">{name}</h3>
              {email && <p className="text-xs text-navy-400 mt-0.5">{email}</p>}
            </div>
            <span className={config.badge}>
              <Icon size={11} />
              {rec}
            </span>
          </div>

          {filename && (
            <p className="text-xs text-navy-300 mb-2 truncate">{filename}</p>
          )}

          {/* Skills */}
          <div className="flex flex-wrap gap-1.5 mt-2">
            {(screening.matched_skills || []).slice(0, 4).map(s => (
              <span key={s} className="skill-matched">{s}</span>
            ))}
            {(screening.missing_skills || []).slice(0, 3).map(s => (
              <span key={s} className="skill-missing line-through opacity-70">{s}</span>
            ))}
            {((screening.matched_skills?.length || 0) + (screening.missing_skills?.length || 0)) > 7 && (
              <span className="text-xs text-navy-400">+more</span>
            )}
          </div>
        </div>

        <ChevronRight size={16} className="text-navy-300 flex-shrink-0 mt-1" />
      </div>
    </div>
  )
}
