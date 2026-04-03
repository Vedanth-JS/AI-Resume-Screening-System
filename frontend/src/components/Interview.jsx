import React, { useState, useEffect } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { Printer, Save, CheckCircle, AlertCircle, FileText, User, Zap, Info } from 'lucide-react'
import { interviewService, jobService } from '../services/api'

export function Interview() {
  const { id } = useParams() // Candidate ID
  const [searchParams] = useSearchParams()
  const jobId = searchParams.get('job_id')
  
  const [kit, setKit] = useState(null)
  const [scores, setScores] = useState({})
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  useEffect(() => {
    const init = async () => {
      try {
        const res = await interviewService.generateKit(id, jobId, ['Technical', 'Behavioral'], 'MID')
        setKit(res.data)
        // Initialize scores
        const initialScores = {}
        res.data.questions.forEach((q, i) => initialScores[i] = 3)
        setScores(initialScores)
      } catch (err) {
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [id, jobId])

  const handleScoreChange = (index, value) => {
    setScores(prev => ({ ...prev, [index]: value }))
  }

  const handleSubmit = async () => {
    setSubmitting(true)
    try {
      await interviewService.submitScorecard(kit.id, scores)
      setSubmitted(true)
    } catch (err) {
      console.error(err)
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) return <div className="p-10 text-slate-500">Generating Interview Kit...</div>
  if (!kit) return <div className="p-10 text-red-500">Failed to load kit.</div>

  const totalScore = (Object.values(scores).reduce((a, b) => a + b, 0) / kit.questions.length).toFixed(1)

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <header className="flex items-center justify-between no-print">
        <div>
          <h2 className="text-3xl font-bold text-white mb-2">Interview Assistant</h2>
          <p className="text-slate-400 text-sm flex items-center gap-2">
            <Zap className="w-4 h-4 text-blue-400" />
            AI-generated technical & behavioral assessment
          </p>
        </div>
        <div className="flex gap-3">
          <button onClick={() => window.print()} className="btn-secondary flex items-center gap-2 px-6">
            <Printer className="w-4 h-4" /> Print Kit
          </button>
          {!submitted && (
            <button 
              onClick={handleSubmit} 
              disabled={submitting}
              className="btn-primary flex items-center gap-2 px-8"
            >
              {submitting ? 'Saving...' : <><Save className="w-4 h-4" /> Complete Interview</>}
            </button>
          )}
        </div>
      </header>

      {submitted && (
        <div className="glass bg-emerald-500/10 border-emerald-500/20 p-6 rounded-3xl flex items-center gap-4 animate-in zoom-in-95 duration-500 no-print">
          <CheckCircle className="w-8 h-8 text-emerald-500" />
          <div>
            <h4 className="font-bold text-emerald-400">Scorecard Submitted</h4>
            <p className="text-sm text-emerald-500/70">The candidate's interview results have been indexed.</p>
          </div>
        </div>
      )}

      {/* Print-ready Layout */}
      <div className="glass rounded-[2.5rem] p-10 border border-white/5 space-y-10 print:shadow-none print:border-none print:bg-white print:text-black">
        <section className="border-b border-white/5 pb-8 print:border-slate-200">
          <div className="flex items-center gap-4 mb-4">
            <div className="w-12 h-12 rounded-2xl bg-blue-500/10 flex items-center justify-center border border-blue-500/20 print:bg-slate-100">
              <User className="w-6 h-6 text-blue-400 print:text-slate-600" />
            </div>
            <div>
              <h3 className="text-2xl font-bold text-white print:text-black">Interview Session</h3>
              <p className="text-slate-500 text-sm uppercase tracking-widest font-bold">Candidate Evaluation Portfolio</p>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-6 mt-6">
            <div className="p-4 rounded-2xl bg-white/5 border border-white/5 print:bg-slate-50 print:border-slate-100">
              <p className="text-[10px] text-slate-500 uppercase font-black mb-1">Focus Areas</p>
              <div className="flex gap-2">
                {kit.focus_areas.map(a => <span key={a} className="text-xs px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 font-bold">{a}</span>)}
              </div>
            </div>
            <div className="p-4 rounded-2xl bg-white/5 border border-white/5 print:bg-slate-50 print:border-slate-100">
              <p className="text-[10px] text-slate-500 uppercase font-black mb-1">Target Intensity</p>
              <span className="text-xs px-2 py-0.5 rounded bg-amber-500/10 text-amber-500 font-bold tracking-widest uppercase">{kit.difficulty} Level</span>
            </div>
          </div>
        </section>

        <section className="space-y-8">
          <div className="flex items-center justify-between">
            <h4 className="text-lg font-bold text-white print:text-black flex items-center gap-3">
              <FileText className="w-5 h-5 text-purple-400" />
              Evaluation Questions
            </h4>
            <div className="no-print">
              <span className="text-3xl font-black text-blue-500">{totalScore}</span>
              <span className="text-xs text-slate-500 ml-2 font-bold uppercase">Avg Score</span>
            </div>
          </div>

          <div className="grid gap-6">
            {kit.questions.map((q, i) => (
              <div key={i} className="group relative p-6 rounded-3xl bg-white/[0.02] border border-white/5 hover:bg-white/[0.04] transition-all print:bg-white print:border-slate-100 print:p-4">
                <div className="flex items-start justify-between gap-6">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <span className="w-6 h-6 rounded-lg bg-white/5 flex items-center justify-center text-[10px] font-bold text-slate-500 print:border print:border-slate-300">{i + 1}</span>
                      <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500">{q.type} Question</span>
                    </div>
                    <p className="text-lg text-slate-200 font-medium leading-relaxed mb-4 print:text-black">{q.question}</p>
                    <div className="flex items-center gap-3 p-3 rounded-xl bg-blue-500/5 border border-blue-500/10 print:bg-slate-50 print:border-slate-200">
                      <Info className="w-4 h-4 text-blue-400" />
                      <p className="text-xs text-blue-400/80 font-medium italic">{q.rationale}</p>
                    </div>
                  </div>
                  <div className="w-48 no-print">
                    <p className="text-[10px] text-slate-500 uppercase font-black mb-3 text-center">Score (1-5)</p>
                    <div className="flex justify-between items-center bg-white/5 rounded-2xl p-2 border border-white/5">
                      {[1, 2, 3, 4, 5].map(val => (
                        <button
                          key={val}
                          onClick={() => handleScoreChange(i, val)}
                          className={`w-7 h-7 rounded-lg text-[10px] font-bold transition-all ${
                            scores[i] === val 
                              ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/30' 
                              : 'text-slate-500 hover:bg-white/5'
                          }`}
                        >
                          {val}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
                {/* Print Answer Sheet */}
                <div className="hidden print:block mt-6 pt-4 border-t border-dashed border-slate-200">
                  <p className="text-[10px] uppercase font-black text-slate-400 mb-8">Interviewer Notes:</p>
                  <div className="h-24 border border-slate-200 rounded-xl" />
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      <footer className="glass p-8 rounded-[2rem] border border-blue-500/20 bg-blue-500/5 text-center no-print">
        <p className="text-sm text-slate-400 mb-4 italic">"This kit is dynamically generated by Gemini 1.5-flash based on real-time skill gap analysis."</p>
        <button onClick={() => window.print()} className="text-xs font-bold text-blue-400 uppercase tracking-widest hover:text-blue-300">
          Export as PDF for Offline Interview →
        </button>
      </footer>
    </div>
  )
}
