import React, { useState, useEffect, useCallback } from "react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Cell, PieChart, Pie, Legend } from "recharts";
import { Users, Target, Timer, TrendingUp, Download, Calendar, ArrowUpRight, ArrowDownRight, ChevronDown } from "lucide-react";
import { Card, StatCard, Badge, Button, Skeleton, EmptyState, ProgressBar } from "@/components/ui";
import { analyticsService } from "@/services/api";

const FALLBACK_COLORS = ["#10b981", "#f59e0b", "#ef4444", "#3b82f6", "#8b5cf6", "#ec4899"];

// ═══════════════════════════════════════════════════════════════════════════════
// Stat Card Wrapper
// ═══════════════════════════════════════════════════════════════════════════════

function MetricCard({ label, value, delta, up, icon: Icon, suffix = "" }: any) {
  return (
    <Card variant="bordered">
      <div className="flex justify-between items-start">
        <div className="p-2.5 rounded-xl bg-primary/10">
          <Icon className="w-5 h-5 text-primary" />
        </div>
        {delta != null && (
          <Badge variant={up ? "success" : "danger"}>
            {up ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
            {delta}{String(delta).includes("%") ? "" : "%"}
          </Badge>
        )}
      </div>
      <div className="mt-4">
        <p className="text-xs font-medium text-muted-foreground tracking-wide">{label}</p>
        <h3 className="text-2xl font-bold mt-0.5">
          {value}{suffix}
        </h3>
      </div>
    </Card>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// Chart Section Wrapper
// ═══════════════════════════════════════════════════════════════════════════════

function ChartSection({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <Card variant="bordered">
      <div className="mb-6">
        <h3 className="text-base font-semibold">{title}</h3>
        {subtitle && <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>}
      </div>
      {children}
    </Card>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// Main Analytics Page
// ═══════════════════════════════════════════════════════════════════════════════

export default function AnalyticsPage() {
  const [period, setPeriod] = useState(30);
  const [overview, setOverview] = useState<any>(null);
  const [funnel, setFunnel] = useState<any>(null);
  const [scores, setScores] = useState<any[]>([]);
  const [timeToHire, setTimeToHire] = useState<any>(null);
  const [skills, setSkills] = useState<any>(null);
  const [volumeTrends, setVolumeTrends] = useState<any[]>([]);
  const [diversity, setDiversity] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [exportLoading, setExportLoading] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const handleExportCSV = async () => {
    setExportLoading(true);
    setExportError(null);
    try {
      const res = await analyticsService.exportCSV();
      const blob = res.data instanceof Blob ? res.data : new Blob([res.data], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `analytics_export_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setExportError(err?.response?.data?.detail || 'Export failed. Please try again.');
      setTimeout(() => setExportError(null), 5000);
    } finally {
      setExportLoading(false);
    }
  };

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [ov, fn, sc, tth, sk, vt, div] = await Promise.allSettled([
        analyticsService.getOverview(period),
        analyticsService.getFunnel(),
        analyticsService.getScoreDistribution(),
        analyticsService.getTimeToHire(),
        analyticsService.getSkillTrends(),
        analyticsService.getVolumeTrends(period),
        analyticsService.getDiversity().catch(() => null),
      ]);
      setOverview(ov.status === "fulfilled" ? ov.value.data : null);
      setFunnel(fn.status === "fulfilled" ? fn.value.data : null);
      setScores(sc.status === "fulfilled" ? sc.value.data : []);
      setTimeToHire(tth.status === "fulfilled" ? tth.value.data : null);
      setSkills(sk.status === "fulfilled" ? sk.value.data : null);
      setVolumeTrends(vt.status === "fulfilled" ? vt.value.data : []);
      setDiversity(div.status === "fulfilled" ? div.value.data : null);
    } finally {
      setLoading(false);
    }
  }, [period]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton variant="text" width={260} height={28} />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 stagger">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} variant="card" />)}
        </div>
        <Skeleton variant="rectangular" height={320} />
      </div>
    );
  }

  if (!overview) {
    return <EmptyState icon={<TrendingUp className="w-8 h-8" />} title="No analytics data yet" description="Upload resumes and create jobs to see insights" />;
  }

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Hiring Analytics</h1>
          <p className="text-sm text-muted-foreground mt-1">Real-time recruitment pipeline insights</p>
        </div>
        <div className="flex items-center gap-2">
          <select value={period} onChange={(e) => setPeriod(Number(e.target.value))}
            className="h-9 px-3 text-xs font-medium rounded-lg border bg-background text-foreground focus:ring-2 focus:ring-ring">
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
            <option value={365}>Last year</option>
          </select>
          <Button
            variant="outline"
            size="sm"
            leftIcon={exportLoading ? undefined : <Download className="w-3.5 h-3.5" />}
            onClick={handleExportCSV}
            disabled={exportLoading}
          >
            {exportLoading ? 'Exporting…' : 'Export CSV'}
          </Button>
        </div>
      </div>

      {/* Export Error Banner */}
      {exportError && (
        <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-500 text-xs font-semibold">
          <span>⚠️</span> {exportError}
        </div>
      )}

      {/* KPI Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 stagger">
        <MetricCard label="Total Applications" value={overview.total_applications} delta={overview.trend_percent} up={overview.trend_percent > 0} icon={Users} />
        <MetricCard label="Average Score" value={overview.average_score} suffix="%" icon={Target} />
        <MetricCard label="Active Jobs" value={overview.active_jobs} icon={TrendingUp} />
        <MetricCard label="Time-to-Hire" value={timeToHire?.average_days ?? "—"} suffix=" days" icon={Timer} />
      </div>

      {/* Volume Trends */}
      <ChartSection title="Application Volume" subtitle="Daily applications received">
        <div className="h-72">
          {volumeTrends.length > 0 ? (
            <ResponsiveContainer>
              <AreaChart data={volumeTrends} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorVolume" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--muted))" />
                <XAxis dataKey="date" tickFormatter={(d: string) => new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric" })} tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "var(--shadow-lg)", background: "hsl(var(--card))" }} />
                <Area type="monotone" dataKey="count" stroke="hsl(var(--primary))" strokeWidth={3} fillOpacity={1} fill="url(#colorVolume)" />
              </AreaChart>
            </ResponsiveContainer>
          ) : <EmptyState title="No application data for this period" />}
        </div>
      </ChartSection>

      {/* Funnel + Score Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartSection title="Hiring Funnel" subtitle="Pipeline conversion">
          <div className="space-y-3">
            {funnel?.stages?.map((s: any, i: number) => {
              const maxCount = funnel.stages[0]?.count || 1;
              const pct = Math.round((s.count / maxCount) * 100);
              return (
                <div key={s.name} className="space-y-1">
                  <div className="flex justify-between text-xs font-medium">
                    <span>{s.name}</span>
                    <span className="text-muted-foreground">{s.count} ({pct}%)</span>
                  </div>
                  <ProgressBar value={pct} color={i === 0 ? "blue" : i === 1 ? "green" : i === 2 ? "amber" : "red"} />
                </div>
              );
            })}
            <div className="flex gap-4 pt-3 text-xs text-muted-foreground">
              <span>Conversion: <strong className="text-foreground">{funnel?.conversion_rate}%</strong></span>
              <span>Screen Pass: <strong className="text-foreground">{funnel?.screening_pass_rate}%</strong></span>
            </div>
          </div>
        </ChartSection>

        <ChartSection title="Score Distribution" subtitle="How candidates score against your ATS">
          <div className="h-64">
            {scores.length > 0 ? (
              <ResponsiveContainer>
                <BarChart data={scores} layout="vertical" margin={{ left: -20 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="hsl(var(--muted))" />
                  <XAxis type="number" hide />
                  <YAxis dataKey="range" type="category" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} width={60} />
                  <Bar dataKey="count" radius={[0, 8, 8, 0]} barSize={18}>
                    {scores.map((_: any, i: number) => <Cell key={i} fill={FALLBACK_COLORS[i % FALLBACK_COLORS.length]} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : <EmptyState title="No scores yet" />}
          </div>
        </ChartSection>
      </div>

      {/* Skills + Time to Hire */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartSection title="Skill Demand vs Supply" subtitle="Top skills in your job postings vs candidate pool">
          <div className="space-y-2 max-h-80 overflow-y-auto">
            {(skills?.skill_gaps || [])?.slice(0, 8).map((s: any) => (
              <div key={s.skill} className="flex items-center justify-between py-2 border-b last:border-0">
                <span className="text-sm font-medium capitalize">{s.skill}</span>
                <div className="flex items-center gap-3 text-xs">
                  <span className="text-muted-foreground">Demand: <strong className="text-foreground">{s.demand}</strong></span>
                  <span className="text-muted-foreground">Supply: <strong className="text-foreground">{s.supply}</strong></span>
                  <Badge variant={s.gap_percent > 30 ? "danger" : s.gap_percent > 10 ? "warning" : "success"}>{s.gap_percent > 0 ? `+${s.gap_percent}%` : "0%"}</Badge>
                </div>
              </div>
            ))}
            {(!skills?.skill_gaps || skills.skill_gaps.length === 0) && <EmptyState title="No skill data yet" />}
          </div>
        </ChartSection>

        <ChartSection title="Time to Hire by Job">
          <div className="space-y-2 max-h-80 overflow-y-auto">
            {(timeToHire?.by_job || []).slice(0, 8).map((j: any) => (
              <div key={j.job} className="flex items-center justify-between py-2 border-b last:border-0">
                <span className="text-sm font-medium truncate flex-1 mr-4">{j.job}</span>
                <span className="text-sm font-semibold tabular-nums">{j.days} days</span>
              </div>
            ))}
            {(!timeToHire?.by_job || timeToHire.by_job.length === 0) && <EmptyState title="No hires tracked yet" />}
          </div>
        </ChartSection>
      </div>

      {diversity && (
        <ChartSection title="Bias & Fairness Dashboard" subtitle="Screening fairness and bias detection">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            <div className="text-center">
              <div className="text-3xl font-bold text-primary">{diversity.total_flags || 0}</div>
              <div className="text-xs text-muted-foreground mt-1">Total Bias Flags</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold">{diversity.score_percentiles?.p50 ?? "—"}</div>
              <div className="text-xs text-muted-foreground mt-1">Median Score (P50)</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold">{diversity.score_std_dev ?? "—"}</div>
              <div className="text-xs text-muted-foreground mt-1">Score Std Deviation</div>
            </div>
          </div>
          {Object.keys(diversity.bias_flags || {}).length > 0 && (
            <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-2">
              {Object.entries(diversity.bias_flags).map(([k, v]: any) => (
                <Badge key={k} variant="neutral" className="justify-between">
                  <span className="capitalize">{k.replace(/_/g, " ")}</span>
                  <span className="font-bold ml-2">{v}</span>
                </Badge>
              ))}
            </div>
          )}
        </ChartSection>
      )}
    </div>
  );
}
