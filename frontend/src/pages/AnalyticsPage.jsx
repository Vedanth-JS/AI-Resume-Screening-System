import { useState, useEffect } from 'react'
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  PieChart, Pie, Cell, FunnelChart as ReFunnelChart, Funnel, LabelList
} from 'recharts'
import { BarChart2, TrendingUp, PieChart as PieIcon, Users } from 'lucide-react'
import { getJobs, getCandidates } from '../api/client'

const COLORS = ['#2B4FA0', '#7E93C3', '#A9B7D7', '#D4DBEB', '#F8F6F1']
const REC_COLORS = {
  'Strong Fit': '#10b981',
  'Maybe': '#f59e0b',
  'Reject': '#f87171'
}

export default function AnalyticsPage() {
  const [jobs, setJobs] = useState([])
  const [selectedJobId, setSelectedJobId] = useState('')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    getJobs().then(setJobs).catch(console.error)
  }, [])

  useEffect(() => {
    if (selectedJobId) {
      fetchAnalytics(selectedJobId)
    }
  }, [selectedJobId])

  const fetchAnalytics = async (jobId) => {
    setLoading(true)
    try {
      const candidates = await getCandidates(jobId)
      
      // Calculate funnel
      const total = candidates.length
      const maybeOrBetter = candidates.filter(c => c.recommendation !== 'Reject').length
      const strongFit = candidates.filter(c => c.recommendation === 'Strong Fit').length
      
      const funnel = [
        { value: total, name: 'Screened', fill: '#0F1E3C' },
        { value: maybeOrBetter, name: 'Potential (Maybe+)', fill: '#536FAF' },
        { value: strongFit, name: 'Shortlisted (Strong)', fill: '#C9A84C' },
      ]

      // Recommendation breakdown
      const recCounts = candidates.reduce((acc, c) => {
        acc[c.recommendation] = (acc[c.recommendation] || 0) + 1
        return acc
      }, {})
      const recommendations = Object.entries(recCounts).map(([name, value]) => ({ name, value }))

      // Score distribution
      const buckets = { '0-20': 0, '21-40': 0, '41-60': 0, '61-80': 0, '81-100': 0 }
      candidates.forEach(c => {
        if (c.score <= 20) buckets['0-20']++
        else if (c.score <= 40) buckets['21-40']++
        else if (c.score <= 60) buckets['41-60']++
        else if (c.score <= 80) buckets['61-80']++
        else buckets['81-100']++
      })
      const scores = Object.entries(buckets).map(([range, count]) => ({ range, count }))

      setData({ funnel, recommendations, scores, total })
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-6xl mx-auto py-8 px-4">
      <div className="mb-10 flex items-center justify-between gap-6">
        <div>
          <h1 className="page-header">HR Analytics</h1>
          <p className="page-sub">Visual insights into candidate quality and hiring pipeline velocity</p>
        </div>
        <div className="w-64">
          <label className="label text-navy-400">Filter Dataset</label>
          <select 
            className="select"
            value={selectedJobId}
            onChange={(e) => setSelectedJobId(e.target.value)}
          >
            <option value="">Select a job posting...</option>
            {jobs.map(j => (
              <option key={j.id} value={j.id}>{j.title}</option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-32 text-navy-300">Calculating metrics...</div>
      ) : !selectedJobId ? (
        <div className="card text-center py-24 flex flex-col items-center border-dashed border-2">
            <Users className="text-navy-50 mb-4" size={64} />
            <h2 className="font-serif text-xl font-semibold text-navy-300">Select a job to view recruitment analytics</h2>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 animate-fade-in">
          
          {/* Funnel Chart */}
          <div className="card md:col-span-1">
            <div className="flex items-center gap-2 mb-6">
               <TrendingUp size={16} className="text-navy-400" />
               <h3 className="font-serif font-bold text-navy-800">Recruitment Funnel</h3>
            </div>
            <div className="h-64">
               <ResponsiveContainer width="100%" height="100%">
                  <ReFunnelChart>
                    <Tooltip contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 8px 32px rgba(0,0,0,0.1)' }} />
                    <Funnel
                      dataKey="value"
                      data={data?.funnel || []}
                      isAnimationActive
                    >
                      <LabelList position="right" fill="#0A1528" stroke="none" dataKey="name" fontSize={11} fontWeight={600} />
                    </Funnel>
                  </ReFunnelChart>
               </ResponsiveContainer>
            </div>
            <p className="text-[10px] text-navy-400 uppercase tracking-widest text-center mt-4">Screened → Potential → Shortlisted</p>
          </div>

          {/* Recommendation Breakdown */}
          <div className="card">
             <div className="flex items-center gap-2 mb-6">
               <PieIcon size={16} className="text-navy-400" />
               <h3 className="font-serif font-bold text-navy-800">Candidate Breakdown</h3>
            </div>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={data?.recommendations || []}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {(data?.recommendations || []).map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={REC_COLORS[entry.name] || COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="flex justify-center gap-4 text-[10px] font-bold uppercase tracking-wider">
               {data?.recommendations.map(r => (
                 <div key={r.name} className="flex items-center gap-1.5">
                    <div className="w-2 h-2 rounded-full" style={{ backgroundColor: REC_COLORS[r.name] }} />
                    {r.name} ({r.value})
                 </div>
               ))}
            </div>
          </div>

          {/* Score Distribution */}
          <div className="card md:col-span-2">
            <div className="flex items-center gap-2 mb-6">
               <BarChart2 size={16} className="text-navy-400" />
               <h3 className="font-serif font-bold text-navy-800">Score Distribution</h3>
            </div>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data?.scores || []}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
                  <XAxis dataKey="range" fontSize={10} fontStyle="italic" />
                  <YAxis fontSize={10} />
                  <Tooltip cursor={{ fill: '#F8F6F1' }} />
                  <Bar dataKey="count" fill="#2B4FA0" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

        </div>
      )}
    </div>
  )
}
