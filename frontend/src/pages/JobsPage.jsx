import { useState, useEffect } from 'react'
import { Plus, Clock, ChevronRight, X } from 'lucide-react'
import { getJobs, createJob } from '../api/client'

export default function JobsPage() {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    experience_level: 'Mid-level',
    required_skills: ''
  })
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    fetchJobs()
  }, [])

  const fetchJobs = async () => {
    try {
      const data = await getJobs()
      setJobs(data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSubmitting(true)
    try {
      const skillsArray = formData.required_skills
        .split(',')
        .map(s => s.trim())
        .filter(s => s !== '')
      
      await createJob({
        ...formData,
        required_skills: skillsArray
      })
      
      setFormData({ title: '', description: '', experience_level: 'Mid-level', required_skills: '' })
      setShowForm(false)
      fetchJobs()
    } catch (err) {
      alert('Failed to create job')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto py-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="page-header">Job Postings</h1>
          <p className="page-sub">Define roles to screen candidates against</p>
        </div>
        <button 
          onClick={() => setShowForm(!showForm)}
          className="btn-primary flex items-center gap-2"
        >
          {showForm ? <X size={18} /> : <Plus size={18} />}
          {showForm ? 'Cancel' : 'Create New Job'}
        </button>
      </div>

      {showForm && (
        <div className="card mb-8 animate-slide-up border-2 border-navy-100">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid grid-cols-2 gap-6">
              <div className="col-span-2">
                <label className="label">Job Title</label>
                <input 
                  required
                  className="input"
                  placeholder="e.g. Senior Frontend Engineer"
                  value={formData.title}
                  onChange={(e) => setFormData({...formData, title: e.target.value})}
                />
              </div>
              <div className="col-span-1">
                <label className="label">Experience Level</label>
                <select 
                  className="select"
                  value={formData.experience_level}
                  onChange={(e) => setFormData({...formData, experience_level: e.target.value})}
                >
                  <option>Entry-level</option>
                  <option>Mid-level</option>
                  <option>Senior</option>
                  <option>Director / Lead</option>
                </select>
              </div>
              <div className="col-span-1">
                <label className="label">Required Skills (comma separated)</label>
                <input 
                  required
                  className="input"
                  placeholder="React, TypeScript, Node.js"
                  value={formData.required_skills}
                  onChange={(e) => setFormData({...formData, required_skills: e.target.value})}
                />
              </div>
              <div className="col-span-2">
                <label className="label">Job Description</label>
                <textarea 
                  required
                  rows={4}
                  className="input py-3 resize-none"
                  placeholder="Outline responsibilities and requirements..."
                  value={formData.description}
                  onChange={(e) => setFormData({...formData, description: e.target.value})}
                />
              </div>
            </div>
            <div className="flex justify-end pt-2">
              <button 
                type="submit" 
                disabled={submitting}
                className="btn-primary"
              >
                {submitting ? 'Creating...' : 'Publish Job Posting'}
              </button>
            </div>
          </form>
        </div>
      )}

      {loading ? (
        <div className="text-center py-20 text-navy-400">Loading jobs...</div>
      ) : jobs.length === 0 ? (
        <div className="card text-center py-16">
          <div className="w-16 h-16 bg-navy-50 rounded-full flex items-center justify-center mx-auto mb-4">
            <Briefcase className="text-navy-300" size={24} />
          </div>
          <h3 className="font-serif text-xl font-semibold text-navy-800 mb-2">No active job postings</h3>
          <p className="text-navy-400 max-w-xs mx-auto mb-6">Create a job posting to begin screening resumes with AI.</p>
          <button onClick={() => setShowForm(true)} className="btn-secondary">Get Started</button>
        </div>
      ) : (
        <div className="space-y-4">
          {jobs.map(job => (
            <div key={job.id} className="card flex items-center justify-between group">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-1.5">
                  <h3 className="font-serif font-semibold text-navy-800 text-lg uppercase tracking-tight">{job.title}</h3>
                  <span className="text-[10px] bg-navy-50 text-navy-500 font-bold px-1.5 py-0.5 rounded uppercase tracking-wider border border-navy-100 italic">
                    {job.experience_level}
                  </span>
                </div>
                <div className="flex items-center gap-4 text-xs text-navy-400">
                  <span className="flex items-center gap-1">
                    <Clock size={12} />
                    Added {new Date(job.created_at).toLocaleDateString()}
                  </span>
                  <div className="flex gap-1.5">
                    {job.required_skills.slice(0, 3).map(skill => (
                      <span key={skill} className="px-2 py-0.5 bg-cream border border-navy-100 rounded text-navy-600 font-medium">
                        {skill}
                      </span>
                    ))}
                    {job.required_skills.length > 3 && <span className="opacity-50">+{job.required_skills.length - 3} more</span>}
                  </div>
                </div>
              </div>
              <ChevronRight size={20} className="text-navy-200 group-hover:text-navy-400 transition-colors" />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function Briefcase({ size, className }) {
  return (
    <svg 
      xmlns="http://www.w3.org/2000/svg" 
      width={size} 
      height={size} 
      viewBox="0 0 24 24" 
      fill="none" 
      stroke="currentColor" 
      strokeWidth="2" 
      strokeLinecap="round" 
      strokeLinejoin="round" 
      className={className}
    >
      <rect width="20" height="14" x="2" y="7" rx="2" ry="2"/>
      <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>
    </svg>
  )
}
