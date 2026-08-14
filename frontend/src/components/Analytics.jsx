import React, { useEffect, useState } from 'react'
import {
  BarChart2, TrendingUp, Users, Briefcase, Target, Clock,
  ShieldAlert, Zap, Brain, AlertCircle, RefreshCw
} from 'lucide-react'
import { Bar, Doughnut, Line } from 'react-chartjs-2'
import {
  Chart as ChartJS, ArcElement, Tooltip, Legend,
  CategoryScale, LinearScale, BarElement, PointElement, LineElement
} from 'chart.js'
import api, { extractErrorMessage } from '../services/api'

ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement, PointElement, LineElement)

const CHART_OPTS = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { labels: { color: '#94a3b8', font: { size: 11, weight: 'bold' } } },
    tooltip: {
      backgroundColor: 'rgba(10,10,12,0.97)',
      borderColor: 'rgba(255,255,255,0.07)',
      borderWidth: 1,
      titleColor: '#fff',
      bodyColor: '#94a3b8',
    },
  },
  scales: {
    x: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#64748b', font: { size: 10 } } },
    y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#64748b', font: { size: 10 } } },
  },
}

function MetricCard({ icon: Icon, label, value, sub, color = 'text-blue-400', bg = 'bg-blue-500/10' }) {
  return (
    <div className="glass-card group">
      <div className={`${bg} p-3.5 rounded-2xl border border-white/5 w-fit mb-5 group-hover:scale-110 transition-transform duration-300`}>
        <Icon className={`w-6 h-6 ${color}`} />
      </div>
      <div className="text-3xl font-bold text-white mb-1">{value ?? '—'}</div>
      <div className="text-sm font-semibold text-slate-400">{label}</div>
      {sub && <div className="text-xs text-slate-600 mt-1">{sub}</div>}
    </div>
  )
}

export function Analytics() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [refreshing, setRefreshing] = useState(false)

  const fetchData = async () => {
    try {
      const res = await api.get('/analytics/overview')
      setData(res.data)
      setError('')
    } catch (err) {
      setError(extractErrorMessage(err, 'Failed to load analytics.'))
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => { fetchData() }, [])

  const handleRefresh = () => { setRefreshing(true); fetchData() }

  // ─── Chart data ──────────────────────────────────────────────────────────

  const histogramData = data ? {
    labels: data.score_distribution.bins,
    datasets: [{
      label: 'Candidates',
      data: data.score_distribution.counts,
      backgroundColor: data.score_distribution.bins.map((_, i) => {
        const midpoint = (i * 10 + 5)
        return midpoint >= 70 ? 'rgba(16,185,129,0.7)' : midpoint >= 40 ? 'rgba(245,158,11,0.7)' : 'rgba(239,68,68,0.7)'
      }),
      borderRadius: 6,
      borderSkipped: false,
    }],
  } : null

  const donutData = data ? {
    labels: ['Shortlisted', 'Review', 'Declined'],
    datasets: [{
      data: [data.score_breakdown.accept, data.score_breakdown.review, data.score_breakdown.reject],
      backgroundColor: ['rgba(16,185,129,0.75)', 'rgba(245,158,11,0.75)', 'rgba(239,68,68,0.7)'],
      borderColor: ['rgba(16,185,129,1)', 'rgba(245,158,11,1)', 'rgba(239,68,68,1)'],
      borderWidth: 1.5, hoverOffset: 8,
    }],
  } : null

  const componentData = data ? {
    labels: ['Keyword Match', 'Semantic Fit', 'Format Quality', 'Section Completeness'],
    datasets: [{
      label: 'Avg Score (%)',
      data: [
        data.component_averages.keyword_avg,
        data.component_averages.semantic_avg,
        data.component_averages.format_avg,
        data.component_averages.section_avg,
      ],
      backgroundColor: [
        'rgba(59,130,246,0.7)',
        'rgba(139,92,246,0.7)',
        'rgba(245,158,11,0.7)',
        'rgba(16,185,129,0.7)',
      ],
      borderRadius: 8,
      borderSkipped: false,
    }],
  } : null

  const donutOpts = {
    responsive: true, maintainAspectRatio: false, cutout: '70%',
    plugins: {
      legend: { position: 'bottom', labels: { color: '#94a3b8', font: { size: 10, weight: 'bold' }, padding: 12, usePointStyle: true } },
      tooltip: { backgroundColor: 'rgba(10,10,12,0.97)', borderColor: 'rgba(255,255,255,0.07)', borderWidth: 1, titleColor: '#fff', bodyColor: '#94a3b8' },
    },
  }

  if (loading) {
    return (
      <div className="space-y-8 animate-in fade-in duration-700">
        <div className="h-10 w-48 bg-white/5 rounded-2xl animate-pulse" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          {[1,2,3,4].map(i => <div key={i} className="h-36 bg-white/5 rounded-3xl animate-pulse" />)}
        </div>
        <div className="grid grid-cols-2 gap-6">
          {[1,2].map(i => <div key={i} className="h-64 bg-white/5 rounded-3xl animate-pulse" />)}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-10 animate-in fade-in slide-in-from-bottom-6 duration-700">
      {/* Header */}
      <header className="flex items-end justify-between">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <div className="w-1.5 h-1.5 rounded-full bg-purple-500 animate-pulse" />
            <p className="text-[10px] font-bold text-purple-500/80 uppercase tracking-widest">Intelligence Hub</p>
          </div>
          <h2 className="text-4xl font-bold text-gradient">Analytics</h2>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="flex items-center gap-2 px-5 py-2.5 bg-white/5 border border-white/10 rounded-xl text-slate-400 hover:text-white hover:bg-white/10 transition-all text-sm font-medium disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </header>

      {error && (
        <div className="flex items-center gap-3 p-4 bg-red-500/10 border border-red-500/20 rounded-2xl text-red-400">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          {error}
        </div>
      )}

      {data && (
        <>
          {/* KPI Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <MetricCard icon={Users}      label="Total Screened"    value={data.total_screened}   color="text-blue-400"   bg="bg-blue-500/10" />
            <MetricCard icon={Briefcase}  label="Active Jobs"       value={data.total_jobs}        color="text-purple-400" bg="bg-purple-500/10" />
            <MetricCard icon={TrendingUp} label="Avg ATS Score"     value={`${data.avg_score}%`}   color="text-emerald-400" bg="bg-emerald-500/10" />
            <MetricCard icon={Clock}      label="Median Process Time" value={`${(data.processing_time.p50/1000).toFixed(1)}s`} sub={`p95: ${(data.processing_time.p95/1000).toFixed(1)}s`} color="text-amber-400" bg="bg-amber-500/10" />
          </div>

          {/* Charts Row 1 */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Score Histogram */}
            <div className="lg:col-span-2 glass rounded-[2rem] p-8 border border-white/5">
              <h3 className="font-bold text-white mb-2 text-sm">Score Distribution Histogram</h3>
              <p className="text-xs text-slate-500 mb-6">Distribution of ATS scores across all screened candidates</p>
              <div className="h-52">
                {histogramData && <Bar data={histogramData} options={{ ...CHART_OPTS, plugins: { ...CHART_OPTS.plugins, legend: { display: false } } }} />}
              </div>
            </div>

            {/* Donut */}
            <div className="glass rounded-[2rem] p-8 border border-white/5 flex flex-col">
              <h3 className="font-bold text-white mb-2 text-sm">Decision Breakdown</h3>
              <p className="text-xs text-slate-500 mb-6">Accept / Review / Reject split</p>
              <div className="flex-1 flex items-center justify-center">
                {donutData && (
                  <div className="w-full" style={{ height: '180px' }}>
                    <Doughnut data={donutData} options={donutOpts} />
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Charts Row 2 */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Component Averages */}
            <div className="glass rounded-[2rem] p-8 border border-white/5">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-9 h-9 bg-blue-500/10 rounded-xl flex items-center justify-center border border-blue-500/20">
                  <BarChart2 className="w-5 h-5 text-blue-400" />
                </div>
                <div>
                  <h3 className="font-bold text-white text-sm">Avg Score by Component</h3>
                  <p className="text-xs text-slate-500">Keyword · Semantic · Format · Section</p>
                </div>
              </div>
              <div className="h-44">
                {componentData && (
                  <Bar
                    data={componentData}
                    options={{
                      ...CHART_OPTS,
                      plugins: { ...CHART_OPTS.plugins, legend: { display: false } },
                      scales: {
                        x: { grid: { display: false }, ticks: { color: '#64748b', font: { size: 9 } } },
                        y: { min: 0, max: 100, grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#64748b', callback: v => `${v}%` } },
                      },
                    }}
                  />
                )}
              </div>
            </div>

            {/* Bias Summary */}
            <div className="glass rounded-[2rem] p-8 border border-white/5">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-9 h-9 bg-red-500/10 rounded-xl flex items-center justify-center border border-red-500/20">
                  <ShieldAlert className="w-5 h-5 text-red-400" />
                </div>
                <div>
                  <h3 className="font-bold text-white text-sm">Bias Detection Summary</h3>
                  <p className="text-xs text-slate-500">Flags across all analyzed job descriptions</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                {[
                  { label: 'Gender Bias Flags', value: data.bias_flags.gender, color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/20' },
                  { label: 'Prestige Bias Flags', value: data.bias_flags.prestige, color: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/20' },
                ].map(item => (
                  <div key={item.label} className={`${item.bg} border ${item.border} rounded-2xl p-5 text-center`}>
                    <div className={`text-4xl font-bold ${item.color} mb-2`}>{item.value}</div>
                    <div className="text-xs text-slate-400 font-medium">{item.label}</div>
                  </div>
                ))}
              </div>

              {/* Processing times */}
              <div className="mt-6 pt-6 border-t border-white/5">
                <p className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-4">Processing Time Percentiles</p>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { label: 'P50', value: data.processing_time.p50 },
                    { label: 'P95', value: data.processing_time.p95 },
                    { label: 'P99', value: data.processing_time.p99 },
                  ].map(t => (
                    <div key={t.label} className="bg-white/[0.02] rounded-xl p-3 text-center border border-white/5">
                      <div className="text-lg font-bold text-white">{(t.value / 1000).toFixed(1)}s</div>
                      <div className="text-[10px] text-slate-600 font-bold">{t.label}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Top Skills Heatmap */}
          <div className="glass rounded-[2rem] p-8 border border-white/5">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-9 h-9 bg-emerald-500/10 rounded-xl flex items-center justify-center border border-emerald-500/20">
                <Brain className="w-5 h-5 text-emerald-400" />
              </div>
              <div>
                <h3 className="font-bold text-white text-sm">Top Skills in Talent Pool</h3>
                <p className="text-xs text-slate-500">Most common skills across all screened resumes</p>
              </div>
            </div>
            {data.top_skills.length === 0 ? (
              <p className="text-slate-600 text-sm text-center py-8">No skills data yet. Upload resumes to see skill distribution.</p>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
                {data.top_skills.map((item, i) => {
                  const maxCount = data.top_skills[0]?.count || 1
                  const intensity = Math.max(0.1, item.count / maxCount)
                  return (
                    <div
                      key={item.skill}
                      className="flex items-center justify-between p-3 rounded-xl border border-white/5 overflow-hidden relative"
                      style={{ background: `rgba(59,130,246,${intensity * 0.15})`, borderColor: `rgba(59,130,246,${intensity * 0.3})` }}
                    >
                      <span className="text-xs font-semibold text-slate-200 capitalize truncate">{item.skill}</span>
                      <span
                        className="text-xs font-bold ml-2 flex-shrink-0 px-1.5 py-0.5 rounded text-blue-400"
                        style={{ background: `rgba(59,130,246,0.15)` }}
                      >
                        {item.count}
                      </span>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Recent Activity */}
          {data.recent_activity.length > 0 && (
            <div className="glass rounded-[2rem] p-8 border border-white/5">
              <h3 className="font-bold text-white text-sm mb-6 flex items-center gap-2">
                <Zap className="w-4 h-4 text-blue-400" />
                Recent Activity
              </h3>
              <div className="space-y-2">
                {data.recent_activity.map((event, i) => (
                  <div key={i} className="flex items-center justify-between py-2.5 border-b border-white/[0.04] last:border-0">
                    <div className="flex items-center gap-3">
                      <div className="w-2 h-2 rounded-full bg-blue-500" />
                      <span className="text-sm text-slate-300 font-medium capitalize">{event.event_type.replace(/_/g, ' ')}</span>
                      {event.payload?.final_score && (
                        <span className="text-xs text-slate-500">score: {event.payload.final_score}%</span>
                      )}
                    </div>
                    <span className="text-xs text-slate-600">
                      {new Date(event.created_at).toLocaleTimeString()}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
