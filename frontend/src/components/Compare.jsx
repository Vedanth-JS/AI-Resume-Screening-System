import React, { useState, useEffect } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { Radar } from 'react-chartjs-2'
import { Users, Zap, ShieldAlert, CheckCircle, Scale, ArrowLeftRight, TrendingUp } from 'lucide-react'
import { comparisonService } from '../services/api'
import {
  Chart as ChartJS,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
} from 'chart.js'

ChartJS.register(RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend)

export function Compare() {
  const { id } = useParams() // Job ID
  const [searchParams] = useSearchParams()
  const candidateIds = searchParams.get('ids')?.split(',') || []
  
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetch = async () => {
      try {
        const res = await comparisonService.compare(id, candidateIds)
        setData(res.data)
      } catch (err) {
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    fetch()
  }, [id, candidateIds.join(',')])

  if (loading) return <div className="p-10 text-slate-500">Normalizing candidate data...</div>
  if (!data) return <div className="p-10 text-red-500">Failed to load comparison.</div>

  const radarData = {
    labels: ['Keywords', 'Semantic', 'Format', 'Experience', 'Culture'],
    datasets: data.candidates.map((c, i) => ({
      label: c.name,
      data: [
        c.breakdown?.keyword_score || 0,
        c.breakdown?.semantic_score || 0,
        c.breakdown?.format_score || 0,
        c.breakdown?.experience_score || 0,
        80 + (i * 5), // Mock culture score for now
      ],
      backgroundColor: i === 0 ? 'rgba(59, 130, 246, 0.2)' : 'rgba(168, 85, 247, 0.2)',
      borderColor: i === 0 ? 'rgba(59, 130, 246, 1)' : 'rgba(168, 85, 247, 1)',
      borderWidth: 2,
    })),
  }

  const radarOptions = {
    scales: {
      r: {
        angleLines: { color: 'rgba(255, 255, 255, 0.05)' },
        grid: { color: 'rgba(255, 255, 255, 0.05)' },
        pointLabels: { color: '#94a3b8', font: { size: 10, weight: 'bold' } },
        ticks: { display: false, count: 5 },
        suggestedMin: 0,
        suggestedMax: 100,
      },
    },
    plugins: {
      legend: { labels: { color: '#fff', font: { size: 12, weight: 'bold' } } },
    },
  }

  return (
    <div className="space-y-10 animate-in fade-in slide-in-from-bottom-6 duration-1000">
      <header className="flex items-end justify-between">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <div className="w-1.5 h-1.5 rounded-full bg-purple-500 animate-pulse" />
            <p className="text-[10px] font-bold text-purple-500/80 uppercase tracking-widest">Decision Intelligence</p>
          </div>
          <h2 className="text-4xl font-bold text-gradient">Candidate Comparison</h2>
        </div>
        <div className="bg-white/5 border border-white/10 rounded-2xl px-6 py-3 flex items-center gap-4">
          <Users className="w-5 h-5 text-slate-500" />
          <span className="text-sm font-bold text-white">{data.candidates.length} Profiles Selected</span>
        </div>
      </header>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
        {/* Radar Chart */}
        <div className="glass rounded-[2.5rem] p-10 border border-white/5 flex flex-col items-center justify-center">
          <h3 className="text-xl font-bold text-white mb-8 flex items-center gap-3">
            <TrendingUp className="w-5 h-5 text-blue-400" />
            Competency Radar
          </h3>
          <div className="w-full h-80">
            <Radar data={radarData} options={radarOptions} />
          </div>
          <p className="text-[11px] text-slate-500 mt-6 text-center leading-relaxed">
            Multidimensional analysis across technical skills, semantic alignment, and structural quality.
          </p>
        </div>

        {/* AI Insight */}
        <div className="xl:col-span-2 glass rounded-[2.5rem] p-10 border border-white/5 relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-[300px] h-[300px] bg-purple-600/5 blur-[100px] -z-10 group-hover:bg-purple-600/10 transition-colors" />
          <div className="flex items-center gap-4 mb-8">
            <div className="w-12 h-12 rounded-2xl bg-purple-500/10 flex items-center justify-center border border-purple-500/20">
              <Zap className="w-6 h-6 text-purple-400" />
            </div>
            <h3 className="text-2xl font-bold text-white">AI Verdict</h3>
          </div>
          <div className="space-y-6">
            <p className="text-lg text-slate-300 leading-relaxed italic border-l-2 border-purple-500 pl-6 py-2">
              "{data.ai_comparison}"
            </p>
            <div className="grid grid-cols-2 gap-6 pt-4">
              <div className="p-5 rounded-3xl bg-white/[0.02] border border-white/5">
                <h4 className="text-xs font-bold text-blue-400 uppercase tracking-widest mb-3">Key Differentiator</h4>
                <p className="text-sm text-slate-400">Candidate A shows significantly higher semantic alignment with the JD's core responsibilities.</p>
              </div>
              <div className="p-5 rounded-3xl bg-white/[0.02] border border-white/5">
                <h4 className="text-xs font-bold text-amber-400 uppercase tracking-widest mb-3">Recommendation</h4>
                <p className="text-sm text-slate-400">Prioritize A for technical depth, B for organizational experience.</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Side-by-Side Table */}
      <div className="glass rounded-[2.5rem] p-10 border border-white/5">
        <div className="flex items-center gap-4 mb-10">
          <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center border border-blue-500/20">
            <ArrowLeftRight className="w-5 h-5 text-blue-400" />
          </div>
          <h3 className="text-2xl font-bold text-white">Detailed Breakdown</h3>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-white/5">
                <th className="pb-6 text-xs text-slate-500 uppercase tracking-widest font-black">Metric</th>
                {data.candidates.map(c => (
                  <th key={c.id} className="pb-6 px-4 text-sm font-bold text-white">{c.name}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {[
                { label: 'Overall Score', key: 'score' },
                { label: 'Keyword Match', subKey: 'keyword_score' },
                { label: 'Semantic Match', subKey: 'semantic_score' },
                { label: 'Format Quality', subKey: 'format_score' },
              ].map(metric => (
                <tr key={metric.label} className="group hover:bg-white/[0.01] transition-colors">
                  <td className="py-5 text-sm font-medium text-slate-400">{metric.label}</td>
                  {data.candidates.map(c => (
                    <td key={c.id} className="py-5 px-4 font-bold text-white">
                      {metric.key ? `${Math.round(c[metric.key])}%` : `${Math.round(c.breakdown?.[metric.subKey])}%`}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
