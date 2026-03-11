import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Search, RotateCw, AlertCircle, FileStack } from 'lucide-react'
import { getJobs, getCandidates, rescreenJob } from '../api/client'
import CandidateCard from '../components/CandidateCard'
import CandidateModal from '../components/CandidateModal'
import FilterSort from '../components/FilterSort'

export default function DashboardPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const initialJobId = searchParams.get('job_id') || ''

  const [jobs, setJobs] = useState([])
  const [selectedJobId, setSelectedJobId] = useState(initialJobId)
  const [candidates, setCandidates] = useState([])
  const [loading, setLoading] = useState(false)
  const [rescreening, setRescreening] = useState(false)
  const [selectedCandidate, setSelectedCandidate] = useState(null)
  
  const [filter, setFilter] = useState('All')
  const [sort, setSort] = useState('score_desc')
  const [search, setSearch] = useState('')

  useEffect(() => {
    getJobs().then(setJobs).catch(console.error)
  }, [])

  useEffect(() => {
    if (selectedJobId) {
      setSearchParams({ job_id: selectedJobId })
      fetchCandidates(selectedJobId)
    } else {
      setCandidates([])
    }
  }, [selectedJobId])

  const fetchCandidates = async (jobId) => {
    setLoading(true)
    try {
      const data = await getCandidates(jobId)
      setCandidates(data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleRescreen = async () => {
    if (!selectedJobId) return
    if (!confirm('Re-screen all candidates for this job using current criteria? This uses AI credits.')) return
    
    setRescreening(true)
    try {
      const results = await rescreenJob(selectedJobId)
      setCandidates(results)
    } catch (err) {
      alert('Rescreening failed')
    } finally {
      setRescreening(false)
    }
  }

  const filtered = candidates.filter(c => {
    const matchesFilter = filter === 'All' || c.recommendation === filter
    const matchesSearch = c.candidate?.name?.toLowerCase().includes(search.toLowerCase()) || 
                          c.candidate?.email?.toLowerCase().includes(search.toLowerCase())
    return matchesFilter && matchesSearch
  })

  const sorted = [...filtered].sort((a, b) => {
    if (sort === 'score_desc') return b.score - a.score
    if (sort === 'score_asc') return a.score - b.score
    if (sort === 'name_asc') return (a.candidate?.name || '').localeCompare(b.candidate?.name || '')
    return 0
  })

  const selectedJob = jobs.find(j => j.id.toString() === selectedJobId)

  return (
    <div className="max-w-6xl mx-auto py-8">
      {/* Dashboard Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-10">
        <div>
          <h1 className="page-header">Review Pipeline</h1>
          <p className="page-sub">Ranked screening results for your active job postings</p>
          
          <div className="mt-4 flex items-center gap-4">
             <div className="w-64">
                <label className="label">Active Job</label>
                <select 
                  className="select"
                  value={selectedJobId}
                  onChange={(e) => setSelectedJobId(e.target.value)}
                >
                  <option value="">Select a job...</option>
                  {jobs.map(j => (
                    <option key={j.id} value={j.id}>{j.title}</option>
                  ))}
                </select>
             </div>
             {selectedJobId && (
                <button 
                  onClick={handleRescreen}
                  disabled={rescreening || loading}
                  className="btn-secondary mt-5 flex items-center gap-2 text-xs py-2 bg-white"
                  title="Re-run AI analysis for all candidates"
                >
                  <RotateCw size={14} className={rescreening ? 'animate-spin' : ''} />
                  {rescreening ? 'Re-screening...' : 'Re-Screen All'}
                </button>
             )}
          </div>
        </div>

        <div className="relative w-full md:w-72">
           <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-navy-300" />
           <input 
             className="input pl-10" 
             placeholder="Search by name or email..." 
             value={search}
             onChange={(e) => setSearch(e.target.value)}
           />
        </div>
      </div>

      {!selectedJobId ? (
        <div className="card text-center py-24 flex flex-col items-center">
            <div className="w-16 h-16 bg-navy-50 rounded-full flex items-center justify-center mb-6">
                <FileStack className="text-navy-200" size={28} />
            </div>
            <h2 className="font-serif text-2xl font-semibold text-navy-800 mb-2">Select a job posting</h2>
            <p className="text-navy-400 max-w-sm">Choose a job from the menu above to view screened candidates and their AI-generated scores.</p>
        </div>
      ) : loading ? (
        <div className="text-center py-24 text-navy-400">
           <RotateCw className="animate-spin mx-auto mb-4" size={32} />
           Loading candidates...
        </div>
      ) : candidates.length === 0 ? (
        <div className="card text-center py-20">
           <AlertCircle className="text-navy-100 mx-auto mb-4" size={48} />
           <h3 className="font-serif text-xl text-navy-800 mb-2">No candidates screened yet</h3>
           <p className="text-navy-400 mb-6">Go to the upload page to add resumes for "{selectedJob?.title}".</p>
           <button 
             onClick={() => window.location.href = '/upload'} 
             className="btn-primary"
           >
             Go to Upload
           </button>
        </div>
      ) : (
        <div className="animate-fade-in">
           <FilterSort 
             filter={filter} 
             setFilter={setFilter} 
             sort={sort} 
             setSort={setSort} 
             count={sorted.length}
           />

           <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {sorted.map(s => (
                <CandidateCard 
                  key={s.id} 
                  screening={s} 
                  onClick={setSelectedCandidate} 
                />
              ))}
           </div>
           
           {sorted.length === 0 && (
             <div className="text-center py-20 text-navy-300 italic border-2 border-dashed border-navy-50 rounded-xl">
                No candidates match your current search/filters.
             </div>
           )}
        </div>
      )}

      {selectedCandidate && (
        <CandidateModal 
          screening={selectedCandidate} 
          onClose={() => setSelectedCandidate(null)} 
        />
      )}
    </div>
  )
}
