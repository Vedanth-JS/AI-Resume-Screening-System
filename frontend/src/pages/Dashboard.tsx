import React from 'react';
import { 
  Zap, 
  Target, 
  Users, 
  Clock, 
  ArrowRight, 
  Sparkles,
  Bot,
  BrainCircuit,
  PieChart
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Link } from 'react-router-dom';

export default function Dashboard() {
  return (
    <div className="space-y-10 pb-20">
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2 text-primary font-bold text-xs uppercase tracking-widest">
           <Sparkles className="w-4 h-4 animate-pulse" /> Welcome back, Scout
        </div>
        <h1 className="text-4xl font-bold font-display tracking-tight leading-tight">Your Recruitment Lab is <span className="text-primary italic">running at 120% efficiency.</span></h1>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        <div className="md:col-span-2 bg-primary text-primary-foreground rounded-[40px] p-10 relative overflow-hidden group shadow-2xl shadow-primary/20">
           <div className="relative z-10 space-y-6">
              <div className="p-3 bg-white/10 rounded-2xl w-fit shadow-inner">
                <Bot className="w-8 h-8" />
              </div>
              <h3 className="text-3xl font-bold font-display leading-tight italic">"Screening Intelligence active."</h3>
              <p className="text-primary-foreground/70 text-sm max-w-sm font-medium">Over 240 resumes were screened this morning using the v2.1-prod model. Peak accuracy reached 98.4%.</p>
              <div className="pt-6">
                 <Link to="/upload" className="px-8 py-4 bg-white text-primary rounded-3xl font-black text-sm shadow-xl hover:-translate-y-1 transition-all inline-block">Launch New Batch</Link>
              </div>
           </div>
           <div className="absolute -right-20 -bottom-20 w-96 h-96 bg-white/10 rounded-full blur-[100px] pointer-events-none transition-transform duration-1000 group-hover:scale-110" />
           <div className="absolute top-10 right-10 flex items-center gap-2 text-[10px] font-black uppercase tracking-widest bg-white/10 px-4 py-1.5 rounded-full">
              System: Operational
           </div>
        </div>

        <div className="bg-card border rounded-[40px] p-10 flex flex-col justify-between border-accent shadow-sm group hover:border-primary/40 transition-all duration-300">
           <div className="space-y-6">
              <div className="p-3 bg-accent rounded-2xl w-fit group-hover:bg-primary/10 transition-colors">
                <BrainCircuit className="w-8 h-8 text-muted-foreground group-hover:text-primary transition-colors" />
              </div>
              <h3 className="text-xl font-bold font-display">Interview Assistant</h3>
              <p className="text-muted-foreground text-xs font-medium leading-relaxed italic">Draft AI-powered questions for <span className="text-foreground font-bold italic underline decoration-primary decoration-4">Arjun Sharma</span> who matched at 92%.</p>
           </div>
           <Link to="/interview/1" className="flex items-center gap-2 text-xs font-black uppercase tracking-widest text-primary hover:gap-4 transition-all mt-10">
              Start Kit Preview <ArrowRight className="w-4 h-4" />
           </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
         {[
           { label: 'Screened today', value: '242', icon: Zap, color: 'primary' },
           { label: 'Avg Match', value: '74%', icon: Target, color: 'blue-500' },
           { label: 'Active Jobs', value: '12', icon: Users, color: 'purple-500' },
           { label: 'Time-to-Hire', value: '14d', icon: Clock, color: 'green-500' },
         ].map((stat, i) => (
           <div key={i} className="bg-card border border-accent/20 rounded-3xl p-6 hover:shadow-lg transition-all duration-300 group">
              <div className="flex items-center gap-4">
                 <div className={cn("p-2 rounded-xl group-hover:ring-2 transition-all", `bg-${stat.color}/10 text-${stat.color}`)}>
                    <stat.icon className="w-5 h-5" />
                 </div>
                 <div>
                    <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">{stat.label}</p>
                    <p className="text-xl font-bold mt-0.5">{stat.value}</p>
                 </div>
              </div>
           </div>
         ))}
      </div>
    </div>
  );
}
