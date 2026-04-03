import React, { useState } from 'react';
import { 
  RadialBarChart, 
  RadialBar, 
  Legend, 
  ResponsiveContainer,
  PolarAngleAxis,
  Tooltip
} from 'recharts';
import { 
  Star, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  FileText, 
  ExternalLink,
  ChevronRight,
  ShieldCheck,
  Zap,
  Info,
  MoreVertical,
  Mail,
  UserCheck,
  UserPlus
} from 'lucide-react';
import { cn } from '@/lib/utils';

const mockCandidates = [
  { id: 1, name: 'Arjun Sharma', score: 88, status: 'Shortlisted', role: 'Senior React Developer' },
  { id: 2, name: 'Priya Patel', score: 72, status: 'Under Review', role: 'Frontend Engineer' },
  { id: 3, name: 'Sohan Rao', score: 94, status: 'Interviewing', role: 'Staff Engineer' },
  { id: 4, name: 'Nisha Gupta', score: 45, status: 'Rejected', role: 'Junior Dev' },
];

const scoreData = [
  { name: 'Keywords', value: 85, fill: '#3b82f6' },
  { name: 'Skills', value: 92, fill: '#10b981' },
  { name: 'Experience', value: 78, fill: '#f59e0b' },
  { name: 'Education', value: 95, fill: '#8b5cf6' },
];

export default function ScreeningPage() {
  const [selectedId, setSelectedId] = useState(1);
  const selected = mockCandidates.find(c => c.id === selectedId) || mockCandidates[0];

  return (
    <div className="flex h-[calc(100vh-12rem)] gap-6 overflow-hidden">
      {/* Candidate List (Left) */}
      <div className="w-1/3 bg-card border rounded-2xl flex flex-col overflow-hidden shadow-sm">
        <div className="p-6 border-b flex items-center justify-between">
          <h2 className="font-display font-bold text-lg">Candidates</h2>
          <div className="relative">
            <Filter className="w-4 h-4 text-muted-foreground cursor-pointer hover:text-foreground transition-all" />
          </div>
        </div>
        <div className="flex-1 overflow-y-auto divide-y divide-border">
          {mockCandidates.map((c) => (
            <div 
              key={c.id} 
              onClick={() => setSelectedId(c.id)}
              className={cn(
                "p-5 cursor-pointer transition-all hover:bg-accent/30 relative group",
                selectedId === c.id ? "bg-primary/5 border-l-4 border-primary" : "border-l-4 border-transparent"
              )}
            >
              <div className="flex justify-between items-start">
                <div className="space-y-1">
                  <h4 className="font-bold text-sm leading-none">{c.name}</h4>
                  <p className="text-[10px] text-muted-foreground font-medium">{c.role}</p>
                </div>
                <div className={cn(
                  "p-1.5 rounded-lg flex items-center justify-center font-bold text-xs ring-1 ring-inset shadow-sm",
                  c.score > 80 ? "bg-green-500/10 text-green-500 ring-green-500/20" :
                  c.score > 60 ? "bg-yellow-500/10 text-yellow-500 ring-yellow-500/20" :
                  "bg-red-500/10 text-red-500 ring-red-500/20"
                )}>
                  {c.score}
                </div>
              </div>
              <div className="flex items-center gap-3 mt-4">
                <div className="flex items-center gap-1 text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
                  <Clock className="w-3 h-3" /> 2d ago
                </div>
                <div className={cn(
                  "px-2 py-0.5 rounded-full text-[9px] font-bold tracking-tighter uppercase",
                  c.status === 'Shortlisted' ? "bg-blue-500/10 text-blue-500" :
                  c.status === 'Interviewing' ? "bg-purple-500/10 text-purple-500" :
                  "bg-muted text-muted-foreground"
                )}>
                  {c.status}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Candidate Profile (Right) */}
      <div className="flex-1 bg-card border rounded-2xl flex flex-col overflow-hidden shadow-sm relative">
        <div className="p-8 border-b flex items-center justify-between">
          <div className="flex items-center gap-6">
            <div className="w-16 h-16 rounded-2xl bg-accent flex items-center justify-center font-bold font-display text-2xl text-primary border shadow-sm">
              {selected.name.split(' ').map(n => n[0]).join('')}
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h2 className="text-2xl font-bold font-display">{selected.name}</h2>
                {selected.score > 90 && <ShieldCheck className="w-5 h-5 text-green-500 fill-green-500/20" />}
              </div>
              <p className="text-muted-foreground text-sm flex items-center gap-2 mt-1">
                {selected.role} • <Mail className="w-3 h-3" /> {selected.name.toLowerCase().replace(' ', '.')}@example.com
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button className="flex items-center gap-2 px-4 py-2 bg-muted/30 text-foreground border rounded-lg text-sm font-bold hover:bg-accent transition-all">
              <Mail className="w-4 h-4" /> Message
            </button>
            <button className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-bold shadow-lg shadow-primary/20 hover:opacity-90 transition-all">
              <UserCheck className="w-4 h-4" /> Shortlist
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-10 space-y-12">
          {/* Top Row: Score & AI Reasoning */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
            <div className="lg:col-span-5 relative group">
              <div className="absolute inset-0 bg-primary/5 rounded-3xl blur-3xl group-hover:bg-primary/10 transition-colors duration-1000" />
              <div className="h-64 flex flex-col items-center justify-center relative p-8 bg-accent/20 rounded-3xl border border-primary/20">
                <ResponsiveContainer width="100%" height="100%">
                  <RadialBarChart cx="50%" cy="50%" innerRadius="30%" outerRadius="100%" barSize={10} data={scoreData} startAngle={90} endAngle={450}>
                    <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
                    <RadialBar background dataKey="value" cornerRadius={10} />
                    <Tooltip cursor={{ stroke: 'red', strokeWidth: 2 }} wrapperStyle={{ outline: 'none' }} />
                  </RadialBarChart>
                </ResponsiveContainer>
                <div className="absolute flex flex-col items-center">
                  <span className="text-4xl font-bold font-display">{selected.score}%</span>
                  <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mt-1">Overall Match</span>
                </div>
              </div>
            </div>
            
            <div className="lg:col-span-7 flex flex-col justify-center">
              <div className="flex items-center gap-2 text-primary font-bold text-xs uppercase tracking-widest mb-4">
                <Zap className="w-4 h-4" /> AI Insights
              </div>
              <h3 className="text-xl font-bold mb-4 font-display">Why this candidate?</h3>
              <div className="bg-accent/10 border-l-4 border-primary p-6 rounded-r-2xl space-y-4">
                <p className="text-sm leading-relaxed text-muted-foreground">
                  The candidate demonstrates <span className="text-foreground font-bold italic">exceptional mastery</span> of React 18 and state management patterns. Their previous experience at a high-scale fintech firm aligns perfectly with our need for backend-aware frontend engineers.
                </p>
                <div className="flex flex-wrap gap-2">
                  {['Strong React 18', 'Fintech Exp', 'Fast Pinned'].map(tag => (
                    <span key={tag} className="px-3 py-1 bg-primary/10 text-primary rounded-full text-[10px] font-bold uppercase tracking-wider">{tag}</span>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Bottom Row: Skills & Breakdown */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="space-y-6">
              <h4 className="font-bold flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-green-500" />
                Matched Skills
              </h4>
              <div className="flex flex-wrap gap-3">
                {['TypeScript', 'TailwindCSS', 'Redux', 'Unit Testing', 'GitHub Actions', 'Performance Optimization', 'UX Design'].map(skill => (
                  <div key={skill} className="px-4 py-2 bg-green-500/10 border border-green-500/20 text-green-600 rounded-2xl text-xs font-bold transition-all shadow-sm shadow-green-500/5 hover:scale-105">
                    {skill}
                  </div>
                ))}
              </div>
            </div>
            <div className="space-y-6">
              <h4 className="font-bold flex items-center gap-2 text-muted-foreground">
                <XCircle className="w-5 h-5 text-red-500/70" />
                Missing / Gaps
              </h4>
              <div className="flex flex-wrap gap-3">
                {['Kubernetes', 'WebAssembly', 'Go'].map(skill => (
                  <div key={skill} className="px-4 py-2 bg-muted border border-border text-muted-foreground rounded-2xl text-xs font-bold transition-all hover:scale-105">
                    {skill}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Raw Resume Preview placeholder */}
          <div className="pt-8 border-t">
             <button className="flex items-center gap-3 w-full p-6 bg-accent/20 rounded-3xl border border-dashed border-muted-foreground/30 hover:border-primary/50 transition-all font-bold text-sm text-muted-foreground">
               <FileText className="w-6 h-6 text-primary" />
               View Full Original Resume (PDF)
               <ChevronRight className="ml-auto w-5 h-5 opacity-30" />
             </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function Filter({ className }: { className?: string }) {
  return <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" /></svg>;
}
