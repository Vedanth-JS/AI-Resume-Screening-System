import React from 'react';
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
  Bot
} from 'lucide-react';
import { cn } from '@/lib/utils';

const comparisonData = [
  { subject: 'React', A: 95, B: 80, C: 60, fullMark: 100 },
  { subject: 'Node.js', A: 70, B: 90, C: 40, fullMark: 100 },
  { subject: 'Testing', A: 85, B: 75, C: 90, fullMark: 100 },
  { subject: 'DevOps', A: 60, B: 65, C: 70, fullMark: 100 },
  { subject: 'Design', A: 90, B: 40, C: 50, fullMark: 100 },
  { subject: 'Soft Skills', A: 80, B: 85, C: 95, fullMark: 100 },
];

const candidates = [
  { id: 'A', name: 'Arjun Sharma', score: 88, match: 'Primary Choice', color: '#3b82f6' },
  { id: 'B', name: 'Priya Patel', score: 72, match: 'Strong Backup', color: '#10b981' },
  { id: 'C', name: 'Sohan Rao', score: 94, match: 'Tech Expert', color: '#8b5cf6' },
];

export default function ComparisonPage() {
  return (
    <div className="space-y-10 pb-20">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold font-display tracking-tight flex items-center gap-3 italic underline decoration-primary decoration-4 underline-offset-8">
            <Sparkles className="w-8 h-8 text-primary animate-pulse" />
            Comparison Mode
          </h1>
          <p className="text-muted-foreground text-sm mt-1">Cross-analyzing top candidates for the <strong>Senior Frontend Engineer</strong> role.</p>
        </div>
        <div className="flex -space-x-4">
          {candidates.map(c => (
             <div key={c.id} className="w-10 h-10 rounded-full border-2 border-background bg-accent flex items-center justify-center font-bold text-xs ring-2 ring-primary/20 ring-offset-2 ring-offset-background cursor-pointer hover:z-10 transition-all hover:-translate-y-1" title={c.name}>
               {c.name[0]}
             </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Radar Chart Panel */}
        <div className="lg:col-span-12 bg-card border rounded-[40px] p-10 pb-2 flex flex-col items-center justify-center relative overflow-hidden shadow-sm group border-accent">
           <div className="absolute inset-0 bg-primary/2 blur-3xl rounded-full scale-150 rotate-45 -z-10 group-hover:scale-[2] transition-transform duration-1000" />
           <div className="w-full max-w-2xl h-[500px]">
             <ResponsiveContainer width="100%" height="100%">
               <RadarChart cx="50%" cy="50%" outerRadius="80%" data={comparisonData}>
                 <PolarGrid stroke="hsl(var(--muted))" />
                 <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11, fontWeight: 800, fill: 'hsl(var(--muted-foreground))' }} />
                 <PolarRadiusAxis angle={30} domain={[0, 100]} axisLine={false} tick={false} />
                 <Radar name="Arjun Sharma" dataKey="A" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.3} animationDuration={1500} />
                 <Radar name="Priya Patel" dataKey="B" stroke="#10b981" fill="#10b981" fillOpacity={0.3} animationDuration={1500} />
                 <Radar name="Sohan Rao" dataKey="C" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.3} animationDuration={1500} />
                 <Tooltip contentStyle={{ borderRadius: '16px', border: 'none', background: 'hsl(var(--popover))' }} />
                 <Legend wrapperStyle={{ paddingTop: '20px', fontSize: '12px', fontWeight: 700 }} />
               </RadarChart>
             </ResponsiveContainer>
           </div>
           {/* Floating AI Insights Badge */}
           <div className="absolute top-8 right-8 flex items-center gap-2 px-6 py-2.5 bg-primary/10 text-primary border border-primary/20 rounded-full text-[11px] font-black italic shadow-lg shadow-primary/10 animate-in fade-in slide-in-from-right-10 duration-1000">
              <Bot className="w-4 h-4" /> COMPARING SKILLS DNA
           </div>
        </div>

        {/* Side-by-Side Table Panel */}
        <div className="lg:col-span-12 bg-card border rounded-[40px] overflow-hidden shadow-sm border-accent">
           <div className="overflow-x-auto">
             <table className="w-full text-left border-collapse min-w-[800px]">
                <thead>
                   <tr className="bg-accent/40 border-b">
                      <th className="px-10 py-6 text-[10px] font-black uppercase tracking-widest text-muted-foreground">Criteria</th>
                      {candidates.map(c => (
                         <th key={c.id} className="px-10 py-6 text-center border-l group">
                            <div className="space-y-1">
                               <p className="text-foreground font-black text-xs leading-none group-hover:text-primary transition-colors">{c.name}</p>
                               <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-tighter italic">{c.match}</p>
                            </div>
                         </th>
                      ))}
                   </tr>
                </thead>
                <tbody className="divide-y divide-border">
                   {[
                      { label: 'Overall Score', key: 'score' },
                      { label: 'Technical Depth', key: 'tech' },
                      { label: 'Cultural Fit', key: 'fit' },
                      { label: 'Availability', key: 'avail' },
                      { label: 'Expected Salary', key: 'sal' },
                   ].map((row, i) => (
                      <tr key={i} className="hover:bg-accent/10 transition-colors group">
                         <td className="px-10 py-6 text-sm font-bold text-muted-foreground group-hover:text-foreground transition-colors">{row.label}</td>
                         {candidates.map(c => (
                            <td key={c.id} className="px-10 py-6 text-center border-l">
                               {row.key === 'score' ? (
                                  <div className="flex flex-col items-center gap-1.5">
                                     <span className={cn("text-2xl font-black font-display leading-none", 
                                        c.id === 'A' ? "text-blue-500" : c.id === 'B' ? "text-green-500" : "text-purple-500"
                                     )}>
                                       {c.id === 'A' ? 88 : c.id === 'B' ? 72 : 94}%
                                     </span>
                                     <div className="w-16 h-1 bg-muted rounded-full">
                                        <div className="h-full bg-current rounded-full" style={{ width: `${c.id === 'A' ? 88 : c.id === 'B' ? 72 : 94}%`, color: c.color }} />
                                     </div>
                                  </div>
                               ) : (
                                  <CheckCircle2 className="w-5 h-5 mx-auto text-green-500/50" />
                               )}
                            </td>
                         ))}
                      </tr>
                   ))}
                </tbody>
             </table>
           </div>
        </div>

        {/* AI Final Aggregator Summary */}
        <div className="lg:col-span-12 p-10 bg-primary/95 text-primary-foreground rounded-[40px] relative overflow-hidden group">
           <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-10">
              <div className="space-y-4 max-w-2xl">
                 <div className="flex items-center gap-2 bg-white/10 px-4 py-1 rounded-full text-[10px] font-black uppercase tracking-widest w-fit">
                    <Target className="w-4 h-4" /> Final Selection logic
                 </div>
                 <h3 className="text-3xl font-bold font-display italic leading-tight">"Candidate Arjun Sharma is your best technical value match."</h3>
                 <p className="text-primary-foreground/70 text-sm italic font-medium leading-relaxed">
                   While Sohan Rao has higher raw scores in DevOps, Arjun balances <strong>95% React proficiency</strong> with superior design sensibilities, making him more suitable for this Frontend role. Priority hire recommended.
                 </p>
              </div>
              <button className="flex items-center gap-3 px-10 py-5 bg-white text-primary rounded-3xl font-black text-sm shadow-xl shadow-white/10 hover:shadow-2xl hover:-translate-y-1 transition-all active:scale-95 group">
                Proceed to Offer Stage <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </button>
           </div>
           <div className="absolute top-0 right-0 w-96 h-96 bg-white/5 rounded-full blur-[100px] pointer-events-none group-hover:scale-110 transition-transform duration-1000" />
        </div>
      </div>
    </div>
  );
}
