import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Legend,
  Tooltip
} from 'recharts';
import {
  CheckCircle2,
  XCircle,
  ShieldCheck,
  Zap,
  Target,
  ArrowRight,
  Sparkles,
  Bot,
  Loader2,
  Trophy,
  AlertTriangle,
  ChevronRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { comparisonService } from '../services/api';

const COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ec4899', '#3b82f6'];

export default function ComparisonPage() {
  const { id: jobId } = useParams<{ id: string }>();

  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  // Placeholder candidate IDs from search params or default demo
  const searchParams = new URLSearchParams(window.location.search);
  const candidateIdsParam = searchParams.get('candidates') || '';

  useEffect(() => {
    if (!jobId || !candidateIdsParam) return;
    setLoading(true);
    const ids = candidateIdsParam.split(',').map(Number).filter(Boolean);
    comparisonService.compare(Number(jobId), ids)
      .then(res => setData(res.data))
      .catch(e => setError(e?.response?.data?.detail || 'Failed to load comparison'))
      .finally(() => setLoading(false));
  }, [jobId, candidateIdsParam]);

  // Build radar chart data from real candidates
  const radarData = data?.candidates?.length
    ? ['keywords', 'skills', 'experience', 'semantic'].map((key) => {
        const entry: any = { subject: key.charAt(0).toUpperCase() + key.slice(1), fullMark: 100 };
        data.candidates.forEach((c: any, i: number) => {
          entry[`C${i}`] = Math.round(c.granular_scores?.[key] ?? 0);
        });
        return entry;
      })
    : [
        { subject: 'React', C0: 95, C1: 80, C2: 60, fullMark: 100 },
        { subject: 'Node.js', C0: 70, C1: 90, C2: 40, fullMark: 100 },
        { subject: 'Testing', C0: 85, C1: 75, C2: 90, fullMark: 100 },
        { subject: 'DevOps', C0: 60, C1: 65, C2: 70, fullMark: 100 },
      ];

  const candidates = data?.candidates ?? [
    { candidate_name: 'Arjun Sharma', overall_score: 88, verdict: 'ACCEPT', matched_skills: ['React', 'TypeScript'] },
    { candidate_name: 'Priya Patel',  overall_score: 72, verdict: 'REVIEW', matched_skills: ['Node.js', 'MongoDB'] },
    { candidate_name: 'Sohan Rao',    overall_score: 94, verdict: 'ACCEPT', matched_skills: ['Python', 'AWS'] },
  ];

  const aiSummary = data?.ai_summary;

  return (
    <div className="space-y-10 pb-20">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold font-display tracking-tight flex items-center gap-3 italic underline decoration-primary decoration-4 underline-offset-8">
            <Sparkles className="w-8 h-8 text-primary animate-pulse" />
            Comparison Mode
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Cross-analyzing top candidates for{' '}
            <strong>{data?.job_title ?? 'this role'}</strong>.
          </p>
        </div>
        <div className="flex -space-x-4">
          {candidates.map((c: any, i: number) => (
            <div
              key={i}
              className="w-10 h-10 rounded-full border-2 border-background flex items-center justify-center font-bold text-xs ring-2 ring-primary/20 ring-offset-2 ring-offset-background cursor-pointer hover:z-10 transition-all hover:-translate-y-1"
              style={{ background: COLORS[i % COLORS.length] + '33', color: COLORS[i % COLORS.length] }}
              title={c.candidate_name}
            >
              {(c.candidate_name || '?')[0]}
            </div>
          ))}
        </div>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-20 gap-3 text-muted-foreground">
          <Loader2 className="w-5 h-5 animate-spin" />
          Loading AI comparison...
        </div>
      )}

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-2xl p-5 text-red-400 text-sm flex items-center gap-3">
          <AlertTriangle className="w-4 h-4 shrink-0" /> {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Radar Chart */}
        <div className="lg:col-span-12 bg-card border rounded-[40px] p-10 pb-2 flex flex-col items-center justify-center relative overflow-hidden shadow-sm group border-accent">
          <div className="absolute inset-0 bg-primary/2 blur-3xl rounded-full scale-150 rotate-45 -z-10 group-hover:scale-[2] transition-transform duration-1000" />
          <div className="w-full max-w-2xl h-[460px]">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart cx="50%" cy="50%" outerRadius="80%" data={radarData}>
                <PolarGrid stroke="hsl(var(--muted))" />
                <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11, fontWeight: 800, fill: 'hsl(var(--muted-foreground))' }} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} axisLine={false} tick={false} />
                {candidates.map((c: any, i: number) => (
                  <Radar
                    key={i}
                    name={c.candidate_name}
                    dataKey={`C${i}`}
                    stroke={COLORS[i % COLORS.length]}
                    fill={COLORS[i % COLORS.length]}
                    fillOpacity={0.25}
                    animationDuration={1500}
                  />
                ))}
                <Tooltip contentStyle={{ borderRadius: '16px', border: 'none', background: 'hsl(var(--popover))' }} />
                <Legend wrapperStyle={{ paddingTop: '20px', fontSize: '12px', fontWeight: 700 }} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
          <div className="absolute top-8 right-8 flex items-center gap-2 px-6 py-2.5 bg-primary/10 text-primary border border-primary/20 rounded-full text-[11px] font-black italic shadow-lg shadow-primary/10 animate-in fade-in slide-in-from-right-10 duration-1000">
            <Bot className="w-4 h-4" /> COMPARING SKILLS DNA
          </div>
        </div>

        {/* Score Table */}
        <div className="lg:col-span-12 bg-card border rounded-[40px] overflow-hidden shadow-sm border-accent">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse min-w-[600px]">
              <thead>
                <tr className="bg-accent/40 border-b">
                  <th className="px-10 py-6 text-[10px] font-black uppercase tracking-widest text-muted-foreground">Criteria</th>
                  {candidates.map((c: any, i: number) => (
                    <th key={i} className="px-8 py-6 text-center border-l">
                      <div className="space-y-1">
                        <p className="text-foreground font-black text-xs leading-none">{c.candidate_name}</p>
                        <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-tighter italic">
                          {c.verdict ?? '—'}
                        </p>
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {[
                  { label: 'Overall Score', key: 'overall_score', format: (v: any) => `${Math.round(v ?? 0)}` },
                  { label: 'Experience', key: 'experience', format: (v: any) => `${v ?? 0} yrs` },
                  { label: 'Matched Skills', key: 'matched_skills', format: (v: any) => (Array.isArray(v) ? v.slice(0, 2).join(', ') || '—' : '—') },
                ].map((row, i) => (
                  <tr key={i} className="hover:bg-accent/10 transition-colors group">
                    <td className="px-10 py-6 text-sm font-bold text-muted-foreground group-hover:text-foreground transition-colors">{row.label}</td>
                    {candidates.map((c: any, ci: number) => (
                      <td key={ci} className="px-8 py-6 text-center border-l">
                        {row.key === 'overall_score' ? (
                          <div className="flex flex-col items-center gap-1.5">
                            <span className="text-2xl font-black font-display leading-none" style={{ color: COLORS[ci % COLORS.length] }}>
                              {Math.round(c.overall_score ?? 0)}
                            </span>
                            <div className="w-16 h-1 bg-muted rounded-full">
                              <div className="h-full rounded-full" style={{ width: `${c.overall_score ?? 0}%`, background: COLORS[ci % COLORS.length] }} />
                            </div>
                          </div>
                        ) : (
                          <span className="text-sm text-foreground font-medium">{row.format(c[row.key])}</span>
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* AI Summary Card — Real Gemini Output */}
        {aiSummary && !aiSummary.error && (
          <div className="lg:col-span-12 bg-gradient-to-br from-slate-900 to-slate-800 border border-slate-700/50 rounded-[40px] p-8 shadow-2xl space-y-6">
            {/* Header */}
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-violet-500/20 flex items-center justify-center">
                <Bot className="w-5 h-5 text-violet-400" />
              </div>
              <div>
                <p className="text-[10px] font-black uppercase tracking-widest text-violet-400">Gemini AI Analysis</p>
                <h3 className="text-lg font-bold text-slate-100">Candidate Comparison Report</h3>
              </div>
            </div>

            {/* Top Pick */}
            {aiSummary.top_pick && (
              <div className="flex items-center gap-3 bg-emerald-500/10 border border-emerald-500/20 rounded-2xl px-5 py-4">
                <Trophy className="w-5 h-5 text-emerald-400 shrink-0" />
                <div>
                  <p className="text-xs font-bold text-emerald-400 uppercase tracking-wider">Top Pick</p>
                  <p className="text-slate-100 font-semibold">{aiSummary.top_pick}</p>
                </div>
              </div>
            )}

            {/* Ranking */}
            {aiSummary.ranking?.length > 0 && (
              <div className="space-y-3">
                <p className="text-xs font-black uppercase tracking-widest text-slate-400">Candidate Ranking</p>
                <div className="space-y-2">
                  {aiSummary.ranking.map((r: any) => (
                    <div key={r.rank} className="flex items-start gap-3 bg-slate-800/60 border border-slate-700/50 rounded-xl px-4 py-3">
                      <span className={cn(
                        "w-6 h-6 rounded-lg flex items-center justify-center text-xs font-black shrink-0",
                        r.rank === 1 ? "bg-amber-500/20 text-amber-400" :
                        r.rank === 2 ? "bg-slate-500/20 text-slate-400" :
                        "bg-orange-800/20 text-orange-600"
                      )}>{r.rank}</span>
                      <div>
                        <p className="text-sm font-semibold text-slate-100">{r.name}</p>
                        <p className="text-xs text-slate-400 mt-0.5">{r.reason}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Differentiators */}
            {aiSummary.key_differentiators?.length > 0 && (
              <div className="space-y-3">
                <p className="text-xs font-black uppercase tracking-widest text-slate-400">Key Differentiators</p>
                <ul className="space-y-2">
                  {aiSummary.key_differentiators.map((d: string, i: number) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                      <ChevronRight className="w-4 h-4 text-violet-400 mt-0.5 shrink-0" />
                      {d}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Recommendation */}
            {aiSummary.recommendation && (
              <div className="bg-violet-500/5 border border-violet-500/20 rounded-2xl px-5 py-4">
                <p className="text-xs font-bold text-violet-400 uppercase tracking-wider mb-2">Recommendation</p>
                <p className="text-sm text-slate-300 leading-relaxed">{aiSummary.recommendation}</p>
              </div>
            )}

            {/* Risk flags */}
            {aiSummary.risk_flags?.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-black uppercase tracking-widest text-slate-400 flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-400" /> Risk Flags
                </p>
                <ul className="space-y-1">
                  {aiSummary.risk_flags.map((f: string, i: number) => (
                    <li key={i} className="text-xs text-amber-300/80 flex items-start gap-2">
                      <span className="mt-1 w-1.5 h-1.5 rounded-full bg-amber-400 shrink-0" />
                      {f}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Fallback static AI summary when no real data */}
        {!aiSummary && !loading && (
          <div className="lg:col-span-12 p-10 bg-primary/95 text-primary-foreground rounded-[40px] relative overflow-hidden group">
            <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-10">
              <div className="space-y-4 max-w-2xl">
                <div className="flex items-center gap-2 bg-white/10 px-4 py-1 rounded-full text-[10px] font-black uppercase tracking-widest w-fit">
                  <Target className="w-4 h-4" /> AI Insights
                </div>
                <h3 className="text-3xl font-bold font-display italic leading-tight">
                  Select candidates from a job to run AI comparison.
                </h3>
                <p className="text-primary-foreground/70 text-sm italic font-medium leading-relaxed">
                  Navigate to a job's candidate list and use the Compare button to get a Gemini-powered ranking.
                </p>
              </div>
            </div>
            <div className="absolute top-0 right-0 w-96 h-96 bg-white/5 rounded-full blur-[100px] pointer-events-none" />
          </div>
        )}
      </div>
    </div>
  );
}
