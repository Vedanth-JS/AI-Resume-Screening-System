import React, { useState } from 'react'
import { Briefcase, X, Loader2, Tag, Zap, AlertCircle } from 'lucide-react'
import { jobService } from '../services/api'

export function CreateJobModal({ onClose, onCreated }) {
  const [form, setForm] = useState({
    title: '',
    description: '',
    required_skills: [],
    min_experience: 0,
    required_education: "Bachelor's Degree",
  })
  const [skillInput, setSkillInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const addSkill = (e) => {
    if ((e.key === 'Enter' || e.key === ',') && skillInput.trim()) {
      e.preventDefault()
      const skill = skillInput.trim().replace(/,$/, '')
      if (skill && !form.required_skills.includes(skill)) {
        setForm(f => ({ ...f, required_skills: [...f.required_skills, skill] }))
      }
      setSkillInput('')
    }
  }

  const removeSkill = (skill) =>
    setForm(f => ({ ...f, required_skills: f.required_skills.filter(s => s !== skill) }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.title || !form.description || form.required_skills.length === 0) {
      setError('Title, description, and at least one skill are required.')
      return
    }
    setLoading(true)
    setError('')
    try {
      const res = await jobService.createJob(form)
      if (onCreated) onCreated(res.data)
      onClose()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create job. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" />
      <div
        className="relative w-full max-w-2xl bg-[#0d0d10] border border-white/10 rounded-[2rem] shadow-2xl shadow-black/50 animate-in fade-in zoom-in-95 duration-300"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-8 pt-8 pb-6 border-b border-white/5">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-blue-500/10 rounded-xl border border-blue-500/20">
              <Briefcase className="w-5 h-5 text-blue-400" />
            </div>
            <h2 className="text-xl font-bold text-white">Create New Position</h2>
          </div>
          <button onClick={onClose} className="p-2 rounded-xl text-slate-500 hover:text-white hover:bg-white/5 transition-all">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-8 space-y-5">
          <div className="space-y-2">
            <label className="text-xs font-bold uppercase tracking-widest text-slate-500">Job Title *</label>
            <input
              type="text"
              placeholder="e.g. Senior Machine Learning Engineer"
              value={form.title}
              onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
              className="w-full bg-white/[0.03] border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/40 transition-all placeholder:text-slate-600"
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-bold uppercase tracking-widest text-slate-500">Job Description *</label>
            <textarea
              rows={3}
              placeholder="Describe the role, responsibilities, and success criteria..."
              value={form.description}
              onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              className="w-full bg-white/[0.03] border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/40 transition-all placeholder:text-slate-600 resize-none"
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-bold uppercase tracking-widest text-slate-500">Required Skills * <span className="normal-case font-normal text-slate-600">(Enter or comma to add)</span></label>
            <div className="bg-white/[0.03] border border-white/10 rounded-xl p-3 min-h-[56px] focus-within:ring-2 focus-within:ring-blue-500/40 transition-all">
              <div className="flex flex-wrap gap-2 mb-2">
                {form.required_skills.map(skill => (
                  <span key={skill} className="flex items-center gap-1.5 px-3 py-1 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded-lg text-xs font-semibold">
                    <Tag className="w-3 h-3" />
                    {skill}
                    <button type="button" onClick={() => removeSkill(skill)} className="hover:text-red-400 transition-colors">
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>
              <input
                type="text"
                value={skillInput}
                onChange={e => setSkillInput(e.target.value)}
                onKeyDown={addSkill}
                placeholder={form.required_skills.length === 0 ? 'python, fastapi, machine-learning...' : 'Add more...'}
                className="bg-transparent text-white text-sm outline-none placeholder:text-slate-600 w-full"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-xs font-bold uppercase tracking-widest text-slate-500">Min. Experience (yrs)</label>
              <input
                type="number" min={0} max={20}
                value={form.min_experience}
                onChange={e => setForm(f => ({ ...f, min_experience: parseInt(e.target.value) || 0 }))}
                className="w-full bg-white/[0.03] border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/40 transition-all"
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs font-bold uppercase tracking-widest text-slate-500">Education</label>
              <select
                value={form.required_education}
                onChange={e => setForm(f => ({ ...f, required_education: e.target.value }))}
                className="w-full bg-[#0d0d10] border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/40 transition-all"
              >
                <option>High School</option>
                <option>Associate's Degree</option>
                <option>Bachelor's Degree</option>
                <option>Master's Degree</option>
                <option>PhD</option>
                <option>Not Specified</option>
              </select>
            </div>
          </div>

          {error && (
            <div className="flex items-center gap-3 p-3.5 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              {error}
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="flex-1 py-3.5 rounded-xl bg-white/5 border border-white/10 text-slate-400 font-semibold hover:bg-white/10 transition-all">
              Cancel
            </button>
            <button type="submit" disabled={loading}
              className="flex-1 py-3.5 rounded-xl bg-blue-600 text-white font-semibold hover:bg-blue-500 transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:pointer-events-none shadow-[0_0_20px_rgba(59,130,246,0.2)]">
              {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <><Zap className="w-5 h-5" />Post Position</>}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
