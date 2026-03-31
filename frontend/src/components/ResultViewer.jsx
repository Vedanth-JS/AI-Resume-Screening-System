import React from 'react'
import { CheckCircle, AlertCircle, Award, Brain, Clock, Zap } from 'lucide-react'

export function ResultViewer({ result }) {
  if (!result) return null;

  const { final_result, skill_analysis, experience_analysis, semantic_score, llm_evaluation, candidate } = result;

  const signals = [
    { label: 'Skills Match', score: skill_analysis.score * 100, icon: Zap, color: 'text-blue-500', bg: 'bg-blue-500/10' },
    { label: 'Experience', score: experience_analysis.score * 100, icon: Clock, color: 'text-purple-500', bg: 'bg-purple-500/10' },
    { label: 'Semantic', score: semantic_score, icon: Brain, color: 'text-pink-500', bg: 'bg-pink-500/10' },
    { label: 'Education', score: 80, icon: Award, color: 'text-emerald-500', bg: 'bg-emerald-500/10' },
  ]

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      {/* Main Score Header */}
      <div className="glass-card flex items-center justify-between">
        <div className="flex items-center gap-6">
          <div className="relative">
             <svg className="w-24 h-24 transform -rotate-90">
                <circle cx="48" cy="48" r="40" stroke="currentColor" strokeWidth="8" fill="transparent" className="text-white/5" />
                <circle cx="48" cy="48" r="40" stroke="currentColor" strokeWidth="8" fill="transparent" 
                        strokeDasharray={251.2} 
                        strokeDashoffset={251.2 - (final_result.final_score / 100) * 251.2}
                        className="text-blue-500 transition-all duration-1000 ease-out" />
             </svg>
             <div className="absolute inset-0 flex items-center justify-center font-bold text-2xl">
               {final_result.final_score}%
             </div>
          </div>
          <div>
            <h2 className="text-2xl font-bold">{candidate.name}</h2>
            <p className="text-slate-400">{candidate.email} • {candidate.phone}</p>
            <div className="flex items-center gap-2 mt-2">
               <span className="px-2.5 py-0.5 rounded-full bg-blue-500/10 text-blue-500 text-[10px] font-bold uppercase tracking-wider border border-blue-500/20">
                 ATS Verified
               </span>
            </div>
          </div>
        </div>
        <div className="text-right max-w-md">
           <p className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-1">AI Verdict</p>
           <p className="text-slate-300 italic text-sm leading-relaxed">"{final_result.explanation}"</p>
        </div>
      </div>

      {/* Multi-Agent Signals Grid */}
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

      {/* Detailed Analysis Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* LLM Evaluation */}
        <div className="glass rounded-3xl p-8 border border-white/5 bg-gradient-to-br from-blue-600/5 to-transparent">
           <h3 className="text-xl font-bold mb-6 flex items-center gap-3">
             <Brain className="w-6 h-6 text-blue-500" />
             Intelligent Evaluation
           </h3>
           <div className="prose prose-invert prose-sm max-w-none">
              {llm_evaluation.split('\n').map((line, i) => (
                <p key={i} className="text-slate-400 leading-relaxed mb-4">{line}</p>
              ))}
           </div>
        </div>

        {/* Skills & Experience Breakdown */}
        <div className="space-y-6">
           <div className="glass rounded-3xl p-8 border border-white/5">
             <h3 className="text-lg font-bold mb-6 flex items-center gap-3">
               <CheckCircle className="w-5 h-5 text-emerald-500" />
               Skills Match
             </h3>
             <div className="flex flex-wrap gap-2">
                {skill_analysis.matched.map(skill => (
                  <span key={skill} className="px-3 py-1.5 rounded-lg bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 text-xs font-medium">
                    {skill}
                  </span>
                ))}
                {skill_analysis.missing.map(skill => (
                  <span key={skill} className="px-3 py-1.5 rounded-lg bg-red-500/10 text-red-500 border border-red-500/20 text-xs font-medium">
                    {skill}
                  </span>
                ))}
             </div>
           </div>

           <div className="glass rounded-3xl p-8 border border-white/5">
             <h3 className="text-lg font-bold mb-6 flex items-center gap-3">
               <Clock className="w-5 h-5 text-purple-500" />
               Experience Audit
             </h3>
             <div className="space-y-4">
                <div className="flex justify-between items-center text-sm">
                   <span className="text-slate-400">Total Experience Found</span>
                   <span className="font-bold">{experience_analysis.candidate_exp} Years</span>
                </div>
                <div className="flex justify-between items-center text-sm">
                   <span className="text-slate-400">Required for Role</span>
                   <span className="font-bold">{experience_analysis.required_exp} Years</span>
                </div>
                <div className="w-full h-2 bg-white/5 rounded-full overflow-hidden mt-4">
                   <div className="h-full bg-purple-500 transition-all duration-700" style={{ width: `${experience_analysis.score * 100}%` }} />
                </div>
             </div>
           </div>
        </div>
      </div>
    </div>
  )
}
