import React from 'react';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
  PieChart,
  Pie
} from 'recharts';
import { 
  TrendingUp, 
  Users, 
  Target, 
  Timer, 
  Download,
  Calendar,
  Filter,
  ArrowUpRight,
  ArrowDownRight
} from 'lucide-react';
import { cn } from '@/lib/utils';

const appTrendData = [
  { name: 'Mon', apps: 40 },
  { name: 'Tue', apps: 30 },
  { name: 'Wed', apps: 65 },
  { name: 'Thu', apps: 45 },
  { name: 'Fri', apps: 90 },
  { name: 'Sat', apps: 20 },
  { name: 'Sun', apps: 15 },
];

const scoreDistData = [
  { range: '0-20', count: 12 },
  { range: '21-40', count: 45 },
  { range: '41-60', count: 128 },
  { range: '61-80', count: 86 },
  { range: '81-100', count: 32 },
];

const COLORS = ['#ef4444', '#f59e0b', '#3b82f6', '#8b5cf6', '#10b981'];

export default function AnalyticsPage() {
  return (
    <div className="space-y-8 pb-10">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold font-display tracking-tight">Hiring Analytics</h1>
          <p className="text-muted-foreground text-sm mt-1">Deep insights into your recruitment pipeline and AI efficiency.</p>
        </div>
        <div className="flex items-center gap-2">
          <button className="flex items-center gap-2 px-4 py-2 border rounded-full text-xs font-bold hover:bg-accent transition-all">
            <Calendar className="w-4 h-4" />
            Last 30 Days
          </button>
          <button className="flex items-center gap-2 px-5 py-2 bg-primary text-primary-foreground rounded-full text-xs font-bold shadow-lg shadow-primary/20 hover:opacity-90 transition-all group">
            <Download className="w-4 h-4 group-hover:-translate-y-0.5 transition-transform" />
            Export Monthly Report (PDF)
          </button>
        </div>
      </div>

      {/* Hero Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[
          { label: 'Total Applications', value: '1,284', delta: '+12%', icon: Users, up: true },
          { label: 'Avg. Match Score', value: '74%', delta: '+5%', icon: Target, up: true },
          { label: 'Shortlist Rate', value: '18.5%', delta: '-2%', icon: TrendingUp, up: false },
          { label: 'Time to Screen', value: '4.2s', delta: '-0.5s', icon: Timer, up: true },
        ].map((stat, i) => (
          <div key={i} className="bg-card border rounded-3xl p-7 relative overflow-hidden group hover:border-primary/40 transition-all duration-500 shadow-sm border-accent/20">
            <div className="flex justify-between items-start">
              <div className="p-2.5 rounded-2xl bg-accent group-hover:bg-primary/10 transition-colors duration-500">
                <stat.icon className="w-5 h-5 text-muted-foreground group-hover:text-primary transition-colors" />
              </div>
              <div className={cn(
                "flex items-center gap-1 text-[10px] font-bold px-2 py-1 rounded-full",
                stat.up ? "bg-green-500/10 text-green-500" : "bg-red-500/10 text-red-500"
              )}>
                {stat.up ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                {stat.delta}
              </div>
            </div>
            <div className="mt-4">
              <p className="text-muted-foreground text-xs font-bold uppercase tracking-widest">{stat.label}</p>
              <h3 className="text-3xl font-bold mt-1 group-hover:tracking-tight transition-all">{stat.value}</h3>
            </div>
          </div>
        ))}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-11 gap-8">
        <div className="lg:col-span-7 bg-card border rounded-3xl p-8 shadow-sm">
          <div className="flex items-center justify-between mb-10">
            <div>
              <h3 className="text-xl font-bold font-display">Application Volume</h3>
              <p className="text-xs text-muted-foreground font-medium mt-1">Daily trend of candidates entering the funnel.</p>
            </div>
            <Filter className="w-4 h-4 text-muted-foreground hover:text-foreground cursor-pointer transition-colors" />
          </div>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={appTrendData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorApps" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--muted))" />
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 10, fontWeight: 700, fill: 'hsl(var(--muted-foreground))' }} dy={10} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 10, fontWeight: 700, fill: 'hsl(var(--muted-foreground))' }} />
                <Tooltip contentStyle={{ borderRadius: '16px', border: 'none', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)', background: 'hsl(var(--card))' }} />
                <Area type="monotone" dataKey="apps" stroke="hsl(var(--primary))" strokeWidth={4} fillOpacity={1} fill="url(#colorApps)" animationDuration={1500} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="lg:col-span-4 bg-card border rounded-3xl p-8 shadow-sm">
          <div className="mb-10">
            <h3 className="text-xl font-bold font-display">Score Distribution</h3>
            <p className="text-xs text-muted-foreground font-medium mt-1">How candidates are performing against models.</p>
          </div>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={scoreDistData} layout="vertical" margin={{ left: -20 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="hsl(var(--muted))" />
                <XAxis type="number" hide />
                <YAxis dataKey="range" type="category" axisLine={false} tickLine={false} tick={{ fontSize: 10, fontWeight: 700, fill: 'hsl(var(--muted-foreground))' }} />
                <Tooltip cursor={{ fill: 'transparent' }} contentStyle={{ borderRadius: '16px', border: 'none', background: 'hsl(var(--card))' }} />
                <Bar dataKey="count" radius={[0, 10, 10, 0]} barSize={20} animationDuration={1000}>
                  {scoreDistData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="bg-card border rounded-3xl p-8 flex items-center gap-10">
          <div className="flex-1 space-y-4">
             <h4 className="text-lg font-bold font-display leading-tight italic">"Bias Detection Engine"</h4>
             <p className="text-xs text-muted-foreground leading-relaxed italic">
               Our fairness auditors have verified that your current job postings have a <span className="text-primary font-bold">low-bias</span> risk rating of <span className="font-bold underline decoration-primary underline-offset-4">A+</span>.
             </p>
             <button className="px-4 py-2 bg-accent/50 rounded-full text-[10px] font-bold uppercase tracking-widest hover:bg-primary/10 hover:text-primary transition-all">View Audit Details</button>
          </div>
          <div className="w-1/3 aspect-square relative flex items-center justify-center">
             <div className="absolute inset-0 border-4 border-primary/20 rounded-full border-dashed animate-[spin_20s_linear_infinite]" />
             <div className="text-4xl font-bold font-display text-primary">A+</div>
          </div>
        </div>
        
        <div className="bg-primary/95 text-primary-foreground rounded-3xl p-8 relative overflow-hidden group">
          <div className="relative z-10 flex flex-col h-full justify-between">
            <div>
              <h4 className="text-2xl font-bold font-display leading-tight">Ready for your next scale?</h4>
              <p className="text-primary-foreground/70 text-xs mt-3 max-w-sm">Use our Interview Assistant to generate tailored questions for your best candidates automatically.</p>
            </div>
            <button className="md:w-fit mt-8 px-6 py-3 bg-white text-primary rounded-2xl font-bold text-sm shadow-xl hover:-translate-y-1 transition-all">Launch AI Assistant</button>
          </div>
          <div className="absolute -right-10 -top-10 w-48 h-48 bg-white/10 rounded-full blur-3xl group-hover:scale-150 transition-all duration-700" />
        </div>
      </div>
    </div>
  );
}
