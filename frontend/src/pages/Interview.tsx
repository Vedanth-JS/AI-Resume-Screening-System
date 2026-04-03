import React, { useState } from 'react';
import { 
  Printer, 
  Save, 
  CheckCircle, 
  ShieldAlert, 
  User, 
  Calendar,
  Clock,
  MoreVertical,
  Star,
  Info,
  History,
  MessageSquare,
  Bot
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface Question {
  id: number;
  question: string;
  type: 'TECHNICAL' | 'BEHAVIORAL' | 'SITUATIONAL';
  expected: string[];
}

const mockQuestions: Question[] = [
  { id: 1, type: 'TECHNICAL', question: 'How would you handle global state in a complex React application with high mutation frequency?', expected: ['Context API vs Redux', 'Performance optimization', 'State normalization'] },
  { id: 2, type: 'BEHAVIORAL', question: 'Tell me about a time you had a conflict with a designer over a specific UI implementation.', expected: ['Communication', 'Compromise', 'User-first logic'] },
  { id: 3, type: 'SITUATIONAL', question: 'A critical production bug is discovered on a Friday at 5 PM. How do you triage it?', expected: ['Isolation', 'Communication', 'Quick-fix vs robust fix'] },
];

export default function InterviewPage() {
  const [scores, setScores] = useState<Record<number, number>>({});
  const totalQuestions = mockQuestions.length;
  const scoredCount = Object.keys(scores).length;
  const avgScore = scoredCount > 0 
    ? (Object.values(scores).reduce((a, b) => a + b, 0) / scoredCount).toFixed(1)
    : '0.0';

  return (
    <div className="space-y-8 pb-20">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-primary text-primary-foreground flex items-center justify-center font-bold text-xl shadow-lg shadow-primary/20">
            AS
          </div>
          <div>
            <h1 className="text-3xl font-bold font-display tracking-tight text-foreground">Arjun Sharma</h1>
            <p className="text-muted-foreground text-sm flex items-center gap-2">
              L3 Senior Developer Interview • Stage 2: Technical Deep Dive
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button className="flex items-center gap-2 px-4 py-2 bg-background border border-border text-foreground rounded-full text-xs font-bold hover:bg-accent transition-all shadow-sm">
            <Printer className="w-4 h-4" /> Print Kit
          </button>
          <button className="flex items-center gap-2 px-6 py-2 bg-primary text-primary-foreground rounded-full text-xs font-bold shadow-xl shadow-primary/20 hover:opacity-90 transition-all">
            <Save className="w-4 h-4" /> Submit Scorecard
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Kit Details */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-card border rounded-3xl p-8 shadow-sm">
            <div className="flex items-center justify-between mb-8">
              <h3 className="text-xl font-bold font-display flex items-center gap-3">
                <Bot className="w-6 h-6 text-primary" />
                AI-Generated Interview Kit
              </h3>
              <div className="px-3 py-1 bg-accent/50 text-muted-foreground rounded-full text-[10px] font-bold uppercase tracking-widest flex items-center gap-1.5 leading-none">
                <History className="w-3 h-3" /> Updated 10m ago
              </div>
            </div>

            <div className="space-y-8">
              {mockQuestions.map((q, i) => (
                <div key={q.id} className="relative pl-10 group">
                  <div className="absolute left-4 top-2 bottom-0 w-[1px] bg-border group-last:bg-transparent" />
                  <div className="absolute left-0 top-0 w-8 h-8 rounded-full bg-accent border flex items-center justify-center text-xs font-bold text-primary group-hover:scale-110 transition-transform">
                    {i + 1}
                  </div>
                  <div className="space-y-4">
                    <div className="flex items-start justify-between">
                      <div className="space-y-2">
                         <span className={cn(
                           "text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded-sm leading-none",
                           q.type === 'TECHNICAL' ? "bg-blue-500/10 text-blue-600" :
                           q.type === 'BEHAVIORAL' ? "bg-purple-500/10 text-purple-600" :
                           "bg-amber-500/10 text-amber-600"
                         )}>
                           {q.type} Question
                         </span>
                         <h4 className="text-lg font-medium leading-snug">{q.question}</h4>
                      </div>
                      <div className="flex items-center gap-1">
                        {[1, 2, 3, 4, 5].map(score => (
                          <button 
                            key={score}
                            onClick={() => setScores(prev => ({ ...prev, [q.id]: score }))}
                            className={cn(
                              "w-8 h-8 rounded-lg text-xs font-bold transition-all border",
                              scores[q.id] === score 
                                ? "bg-primary text-primary-foreground border-primary shadow-lg shadow-primary/20" 
                                : "hover:bg-accent text-muted-foreground hover:text-foreground"
                            )}
                          >
                            {score}
                          </button>
                        ))}
                      </div>
                    </div>
                    
                    <div className="bg-accent/20 rounded-2xl p-4 flex gap-4">
                       <Info className="w-5 h-5 text-primary opacity-50 flex-shrink-0" />
                       <div className="space-y-2">
                          <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground opacity-70">Expectations / Key Points</p>
                          <ul className="flex flex-wrap gap-2">
                            {q.expected.map(point => (
                              <li key={point} className="flex items-center gap-1.5 text-xs text-muted-foreground font-medium italic">
                                <CheckCircle className="w-3 h-3 text-green-500/50" />
                                {point}
                              </li>
                            ))}
                          </ul>
                       </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: Score Summary */}
        <div className="space-y-6">
          <div className="bg-primary/5 border border-primary/10 rounded-3xl p-8 sticky top-8">
            <h3 className="text-lg font-bold font-display mb-6">Scorecard Summary</h3>
            <div className="space-y-6">
              <div className="flex items-end justify-between border-b border-primary/10 pb-6">
                <div>
                  <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Average Score</p>
                  <h2 className="text-5xl font-bold font-display text-foreground mt-1">{avgScore}</h2>
                </div>
                <div className="text-right">
                   <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Scored</p>
                   <p className="text-lg font-bold">{scoredCount} / {totalQuestions}</p>
                </div>
              </div>

              <div className="space-y-4 pt-10">
                <div className="flex items-center gap-3 text-primary font-bold text-xs uppercase tracking-widest leading-none">
                  <Star className="w-4 h-4 fill-primary/20" /> AI Preliminary Match: <span className="text-foreground italic">92%</span>
                </div>
                <div className="flex items-center gap-4 p-5 bg-card border rounded-2xl shadow-sm relative group cursor-pointer hover:border-primary/50 transition-all overflow-hidden">
                   <div className="absolute inset-0 bg-primary/2 blur-2xl group-hover:bg-primary/5 transition-all" />
                   <MessageSquare className="w-6 h-6 text-primary flex-shrink-0 relative z-10" />
                   <div className="relative z-10">
                      <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">AI Verdict</p>
                      <p className="text-xs font-bold leading-tight mt-1">"Based on match score {avgScore}, candidate is highly recommended for hire."</p>
                   </div>
                </div>
              </div>

              <div className="pt-10 flex flex-col gap-3">
                 <button className="w-full py-4 bg-green-500 text-white rounded-2xl font-bold text-sm shadow-xl shadow-green-500/20 hover:scale-[1.02] active:scale-95 transition-all">Move to Final Round</button>
                 <button className="w-full py-4 bg-red-500/10 text-red-500 border border-red-500/20 rounded-2xl font-bold text-sm hover:bg-red-500/20 transition-all">Reject Candidate</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
