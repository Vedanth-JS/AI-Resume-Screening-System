import { useEffect, useRef } from 'react'
import { X, CheckCircle2, XCircle, AlertCircle, FileText, Brain, Award } from 'lucide-react'

const REC_CONFIG = {
  'Strong Fit': { badge: 'badge-strong', Icon: CheckCircle2 },
  'Maybe': { badge: 'badge-maybe', Icon: AlertCircle },
  'Reject': { badge: 'badge-reject', Icon: XCircle },
}

function ScoreBar({ label, value, max = 100, color }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-navy-500 w-24 text-right">{label}</span>
      <div className="flex-1 h-2 bg-navy-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${color}`}
          style={{ width: `${(value / max) * 100}%` }}
        />
      </div>
      <span className="text-xs font-semibold text-navy-700 w-8">{value}</span>
    </div>
  )
}

export default function CandidateModal({ screening, onClose }) {
  const overlayRef = useRef()

  useEffect(() => {
    const handleKey = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [onClose])

  if (!screening) return null

  const rec = screening.recommendation
  const { badge, Icon } = REC_CONFIG[rec] || REC_CONFIG['Reject']
  const name = screening.candidate?.name || 'Unknown Candidate'
  const email = screening.candidate?.email || ''
  const filename = screening.candidate?.original_filename || ''
  const matchedCount = screening.matched_skills?.length || 0
  const missingCount = screening.missing_skills?.length || 0
  const totalSkills = matchedCount + missingCount || 1

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in"
      style={{ backgroundColor: 'rgba(6,13,24,0.6)', backdropFilter: 'blur(4px)' }}
      onClick={(e) => { if (e.target === overlayRef.current) onClose() }}
    >
      <div className="bg-white rounded-2xl shadow-modal w-full max-w-2xl max-h-[90vh] overflow-y-auto animate-slide-up">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-navy-100 px-8 py-5 flex items-start justify-between rounded-t-2xl">
          <div>
            <h2 className="font-serif text-xl font-semibold text-navy-800">{name}</h2>
            {email && <p className="text-sm text-navy-400 mt-0.5">{email}</p>}
            {filename && <p className="text-xs text-navy-300 mt-0.5">{filename}</p>}
          </div>
          <div className="flex items-center gap-3 ml-4">
            <span className={badge}>
              <Icon size={12} />
              {rec}
            </span>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-navy-50 text-navy-400 hover:text-navy-600 transition-colors"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="px-8 py-6 space-y-7">
          {/* Score Overview */}
          <section>
            <h3 className="flex items-center gap-2 text-xs font-semibold text-navy-500 uppercase tracking-widest mb-4">
              <Award size={13} />
              Score Breakdown
            </h3>
            <div className="flex items-center gap-8 mb-5">
              <div className="text-center">
                <div className="text-5xl font-serif font-bold text-navy-800">{Math.round(screening.score)}</div>
                <div className="text-xs text-navy-400 mt-1">Overall Score</div>
              </div>
              <div className="flex-1 space-y-2.5">
                <ScoreBar label="Overall" value={Math.round(screening.score)} color="bg-navy-700" />
                <ScoreBar
                  label="Skills Match"
                  value={Math.round((matchedCount / totalSkills) * 100)}
                  color="bg-emerald-500"
                />
              </div>
            </div>
          </section>

          {/* AI Summary */}
          <section>
            <h3 className="flex items-center gap-2 text-xs font-semibold text-navy-500 uppercase tracking-widest mb-3">
              <Brain size={13} />
              AI Assessment
            </h3>
            <div className="bg-navy-50 border border-navy-100 rounded-xl p-4">
              <p className="text-sm text-navy-700 leading-relaxed">{screening.ai_summary || 'No summary available.'}</p>
            </div>
          </section>

          {/* Skills */}
          <section>
            <h3 className="flex items-center gap-2 text-xs font-semibold text-navy-500 uppercase tracking-widest mb-3">
              <FileText size={13} />
              Skills Analysis
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-emerald-600 font-semibold mb-2 flex items-center gap-1">
                  <CheckCircle2 size={11} /> Matched ({matchedCount})
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {(screening.matched_skills || []).map(s => (
                    <span key={s} className="skill-matched">{s}</span>
                  ))}
                  {matchedCount === 0 && <span className="text-xs text-navy-300">None identified</span>}
                </div>
              </div>
              <div>
                <p className="text-xs text-red-600 font-semibold mb-2 flex items-center gap-1">
                  <XCircle size={11} /> Missing ({missingCount})
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {(screening.missing_skills || []).map(s => (
                    <span key={s} className="skill-missing">{s}</span>
                  ))}
                  {missingCount === 0 && <span className="text-xs text-navy-300">All skills matched!</span>}
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}
