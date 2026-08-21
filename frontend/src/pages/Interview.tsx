import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
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
  Bot,
  AlertCircle,
  Loader2,
  Check,
  X
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { interviewService, atsService, scheduleService, extractErrorMessage } from '../services/api';

interface Question {
  id: number;
  question: string;
  type: 'TECHNICAL' | 'BEHAVIORAL' | 'SITUATIONAL';
  expected: string[];
}

const fallbackQuestions: Question[] = [
  { id: 1, type: 'TECHNICAL', question: 'How would you handle global state in a complex React application with high mutation frequency?', expected: ['Context API vs Redux', 'Performance optimization', 'State normalization'] },
  { id: 2, type: 'BEHAVIORAL', question: 'Tell me about a time you had a conflict with a designer over a specific UI implementation.', expected: ['Communication', 'Compromise', 'User-first logic'] },
  { id: 3, type: 'SITUATIONAL', question: 'A critical production bug is discovered on a Friday at 5 PM. How do you triage it?', expected: ['Isolation', 'Communication', 'Quick-fix vs robust fix'] },
];

export default function InterviewPage() {
  const { id } = useParams<{ id: string }>();
  const kitId = Number(id) || 1;

  const [loading, setLoading] = useState(true);
  const [candidateName, setCandidateName] = useState('Arjun Sharma');
  const [jobTitle, setJobTitle] = useState('L3 Senior Developer Interview • Stage 2: Technical Deep Dive');
  const [applicationId, setApplicationId] = useState<number | null>(1);
  const [questions, setQuestions] = useState<Question[]>(fallbackQuestions);
  
  const [scores, setScores] = useState<Record<number, number>>({});
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [candidateStatus, setCandidateStatus] = useState<'scheduled' | 'advanced' | 'rejected'>('scheduled');
  const [statusMessage, setStatusMessage] = useState('');

  // ─── Scheduling state ────────────────────────────────────────────────────────
  const [showSchedulePanel, setShowSchedulePanel] = useState(false);
  const [scheduledAt, setScheduledAt] = useState('');
  const [scheduleLocation, setScheduleLocation] = useState('');
  const [meetingLink, setMeetingLink] = useState('');
  const [scheduleLoading, setScheduleLoading] = useState(false);
  const [scheduledConfirmed, setScheduledConfirmed] = useState<string | null>(null);

  // Custom Toast/Notification state
  const [toast, setToast] = useState<{ show: boolean; message: string; type: 'success' | 'error' | 'info' }>({
    show: false,
    message: '',
    type: 'success'
  });

  const showToast = (message: string, type: 'success' | 'error' | 'info' = 'success') => {
    setToast({ show: true, message, type });
  };

  useEffect(() => {
    if (toast.show) {
      const timer = setTimeout(() => {
        setToast(prev => ({ ...prev, show: false }));
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [toast.show]);

  // Load Kit Details from Backend
  useEffect(() => {
    async function loadKit() {
      try {
        setLoading(true);
        const res = await interviewService.getKit(kitId);
        if (res.data) {
          const kitData = res.data;
          setCandidateName(kitData.candidate_name || 'Arjun Sharma');
          setJobTitle(`${kitData.job_title || 'Developer'} Interview • Difficulty: ${kitData.difficulty || 'SENIOR'}`);
          setApplicationId(kitData.application_id || 1);
          
          if (kitData.questions && kitData.questions.length > 0) {
            // Map backend questions to local schema
            const mapped: Question[] = kitData.questions.map((q: any, index: number) => ({
              id: q.id || index + 1,
              type: q.type || 'TECHNICAL',
              question: q.question,
              expected: q.expected_answer_points || q.expected || []
            }));
            setQuestions(mapped);
          }
        }
      } catch (err) {
        console.error('Failed to fetch kit, using mocked/fallback data:', err);
        // We fallback silently to let the page function offline/standalone
      } finally {
        setLoading(false);
      }
    }
    loadKit();
  }, [kitId]);

  const totalQuestions = questions.length;
  const scoredCount = Object.keys(scores).length;
  const avgScore = scoredCount > 0 
    ? (Object.values(scores).reduce((a, b) => a + b, 0) / scoredCount).toFixed(1)
    : '0.0';

  // 1. Print Kit Action
  const handlePrint = () => {
    window.print();
  };

  // 2. Submit Scorecard Action
  const handleSubmitScorecard = async () => {
    if (scoredCount < totalQuestions) {
      showToast(`Please score all ${totalQuestions} questions before submitting.`, 'error');
      return;
    }

    try {
      await interviewService.submitScorecard(kitId, scores);
      setIsSubmitted(true);
      showToast('Scorecard submitted successfully! Recruiter recommendation: ' + 
        (Number(avgScore) > 4 ? 'Strong Hire' : Number(avgScore) > 3 ? 'Hire' : 'No Hire'), 'success');
    } catch (err) {
      showToast(extractErrorMessage(err, 'Failed to submit scorecard.'), 'error');
    }
  };

  // 3. Move to Final Round Action
  const handleMoveToFinalRound = async () => {
    if (!applicationId) {
      showToast('No active application linked to this interview kit.', 'error');
      return;
    }

    try {
      // ONSITE_INTERVIEW serves as the final round in our PipelineStageEnum
      await atsService.advanceStage(applicationId, 'ONSITE_INTERVIEW', 'Advanced from Technical Deep Dive stage via Interview Kit.');
      setCandidateStatus('advanced');
      setStatusMessage('Candidate advanced to Onsite Interview (Final Round)');
      showToast('Candidate successfully moved to the final round!', 'success');
    } catch (err) {
      showToast(extractErrorMessage(err, 'Failed to advance candidate stage.'), 'error');
    }
  };

  // 4. Reject Candidate Action
  const handleRejectCandidate = async () => {
    if (!applicationId) {
      showToast('No active application linked to this interview kit.', 'error');
      return;
    }

    try {
      await atsService.rejectCandidate(applicationId, null, 'Rejected during Technical Deep Dive stage.');
      setCandidateStatus('rejected');
      setStatusMessage('Candidate rejected during Technical Deep Dive');
      showToast('Candidate status set to Rejected.', 'info');
    } catch (err) {
      showToast(extractErrorMessage(err, 'Failed to reject candidate.'), 'error');
    }
  };

  // 5. Schedule Interview Action
  const handleScheduleInterview = async () => {
    if (!scheduledAt) {
      showToast('Please select a date and time for the interview.', 'error');
      return;
    }
    setScheduleLoading(true);
    try {
      await scheduleService.schedule(kitId, {
        scheduled_at: new Date(scheduledAt).toISOString(),
        location: scheduleLocation || null,
        meeting_link: meetingLink || null,
      });
      const dateLabel = new Date(scheduledAt).toLocaleString();
      setScheduledConfirmed(dateLabel);
      setShowSchedulePanel(false);
      showToast(`Interview scheduled for ${dateLabel}`, 'success');
    } catch (err) {
      showToast(extractErrorMessage(err, 'Failed to schedule interview.'), 'error');
    } finally {
      setScheduleLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-[50vh] flex flex-col items-center justify-center gap-4">
        <Loader2 className="w-10 h-10 animate-spin text-primary" />
        <p className="text-muted-foreground text-sm font-semibold animate-pulse">Loading Interview Kit...</p>
      </div>
    );
  }

  return (
    <div className="space-y-8 pb-20 relative">
      {/* CSS for print layouts and general polish */}
      <style dangerouslySetInnerHTML={{ __html: `
        @media print {
          body {
            background: white !important;
            color: black !important;
          }
          main, .page-container, div {
            padding: 0 !important;
            margin: 0 !important;
            box-shadow: none !important;
          }
          header, aside, nav, button, .no-print, [role="alert"] {
            display: none !important;
          }
          .print-full-width {
            width: 100% !important;
            max-width: 100% !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
          }
        }
      `}} />

      {/* Sleek Custom Glassmorphism Toast */}
      {toast.show && (
        <div className={cn(
          "fixed top-6 right-6 z-50 flex items-center gap-3 px-6 py-4 rounded-2xl border backdrop-blur-md shadow-2xl transition-all duration-300 animate-slide-in-right",
          toast.type === 'success' ? "bg-green-500/10 border-green-500/30 text-green-500" :
          toast.type === 'error' ? "bg-red-500/10 border-red-500/30 text-red-500" :
          "bg-blue-500/10 border-blue-500/30 text-blue-400"
        )}>
          {toast.type === 'success' && <CheckCircle className="w-5 h-5" />}
          {toast.type === 'error' && <AlertCircle className="w-5 h-5" />}
          {toast.type === 'info' && <Info className="w-5 h-5" />}
          <span className="text-xs font-bold font-sans tracking-wide">{toast.message}</span>
          <button onClick={() => setToast(prev => ({ ...prev, show: false }))} className="ml-2 hover:opacity-75">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className={cn(
            "w-14 h-14 rounded-2xl flex items-center justify-center font-bold text-xl shadow-lg transition-colors duration-300",
            candidateStatus === 'advanced' ? "bg-green-500 text-white shadow-green-500/20" :
            candidateStatus === 'rejected' ? "bg-red-500 text-white shadow-red-500/20" :
            "bg-primary text-primary-foreground shadow-primary/20"
          )}>
            {candidateName.split(' ').map(n => n[0]).join('')}
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-bold font-display tracking-tight text-foreground">{candidateName}</h1>
              {candidateStatus !== 'scheduled' && (
                <span className={cn(
                  "text-[9px] font-black uppercase tracking-widest px-2.5 py-1 rounded-full leading-none",
                  candidateStatus === 'advanced' ? "bg-green-500/10 text-green-500 border border-green-500/20" :
                  "bg-red-500/10 text-red-500 border border-red-500/20"
                )}>
                  {candidateStatus}
                </span>
              )}
            </div>
            <p className="text-muted-foreground text-sm flex items-center gap-2 mt-1">
              {jobTitle}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 no-print">
          <button 
            onClick={handlePrint}
            className="flex items-center gap-2 px-4 py-2 bg-background border border-border text-foreground rounded-full text-xs font-bold hover:bg-accent transition-all shadow-sm active:scale-95"
          >
            <Printer className="w-4 h-4" /> Print Kit
          </button>
          <button
            onClick={() => setShowSchedulePanel(!showSchedulePanel)}
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-full text-xs font-bold transition-all active:scale-95 border",
              scheduledConfirmed
                ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                : showSchedulePanel
                ? "bg-violet-500/20 border-violet-500/40 text-violet-300"
                : "bg-background border-border text-foreground hover:bg-accent"
            )}
          >
            <Calendar className="w-4 h-4" />
            {scheduledConfirmed ? 'Rescheduling' : 'Schedule Interview'}
          </button>
          <button 
            onClick={handleSubmitScorecard}
            disabled={isSubmitted}
            className={cn(
              "flex items-center gap-2 px-6 py-2 rounded-full text-xs font-bold transition-all active:scale-95",
              isSubmitted 
                ? "bg-muted text-muted-foreground border border-border cursor-not-allowed"
                : "bg-primary text-primary-foreground shadow-xl shadow-primary/20 hover:opacity-90"
            )}
          >
            <Save className="w-4 h-4" /> {isSubmitted ? 'Scorecard Submitted' : 'Submit Scorecard'}
          </button>
        </div>
      </div>

      {statusMessage && (
        <div className={cn(
          "p-4 border rounded-2xl text-sm font-bold flex items-center gap-3 no-print",
          candidateStatus === 'advanced' ? "bg-green-500/5 border-green-500/20 text-green-500" :
          "bg-red-500/5 border-red-500/20 text-red-500"
        )}>
          <Bot className="w-5 h-5" />
          {statusMessage}
        </div>
      )}

      {/* ─── Confirmed schedule badge ─────────────────────────────────────── */}
      {scheduledConfirmed && (
        <div className="flex items-center gap-3 bg-emerald-500/5 border border-emerald-500/20 rounded-2xl px-5 py-3 text-sm text-emerald-400 no-print">
          <CheckCircle className="w-4 h-4 shrink-0" />
          <span>Interview confirmed for <strong>{scheduledConfirmed}</strong>. Email notification sent.</span>
        </div>
      )}

      {/* ─── Schedule Interview Panel ─────────────────────────────────────── */}
      {showSchedulePanel && (
        <div className="bg-card border border-border rounded-2xl p-6 shadow-md no-print space-y-4">
          <h3 className="text-base font-bold flex items-center gap-2 text-foreground">
            <Calendar className="w-4 h-4 text-violet-400" />
            Schedule Interview
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Date &amp; Time *</label>
              <input
                type="datetime-local"
                value={scheduledAt}
                onChange={(e) => setScheduledAt(e.target.value)}
                className="w-full bg-background border border-border rounded-xl px-3 py-2.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-violet-500/50"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Location</label>
              <input
                type="text"
                placeholder="e.g. Meeting Room A or Online"
                value={scheduleLocation}
                onChange={(e) => setScheduleLocation(e.target.value)}
                className="w-full bg-background border border-border rounded-xl px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-violet-500/50"
              />
            </div>
            <div className="space-y-1.5 sm:col-span-2">
              <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Meeting Link</label>
              <input
                type="url"
                placeholder="https://meet.google.com/..."
                value={meetingLink}
                onChange={(e) => setMeetingLink(e.target.value)}
                className="w-full bg-background border border-border rounded-xl px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-violet-500/50"
              />
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button onClick={() => setShowSchedulePanel(false)} className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
              Cancel
            </button>
            <button
              onClick={handleScheduleInterview}
              disabled={scheduleLoading}
              className="flex items-center gap-2 px-5 py-2 bg-violet-600 hover:bg-violet-500 text-white rounded-xl text-sm font-semibold transition-colors disabled:opacity-50"
            >
              {scheduleLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
              Confirm Schedule
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 print-full-width">
        {/* Left Column: Kit Details */}
        <div className="lg:col-span-2 space-y-6 print-full-width">
          <div className="bg-card border rounded-3xl p-8 shadow-sm print-full-width">
            <div className="flex items-center justify-between mb-8 no-print">
              <h3 className="text-xl font-bold font-display flex items-center gap-3">
                <Bot className="w-6 h-6 text-primary" />
                AI-Generated Interview Kit
              </h3>
              <div className="px-3 py-1 bg-accent/50 text-muted-foreground rounded-full text-[10px] font-bold uppercase tracking-widest flex items-center gap-1.5 leading-none">
                <History className="w-3 h-3" /> Updated recently
              </div>
            </div>

            <div className="space-y-8">
              {questions.map((q, i) => (
                <div key={q.id} className="relative pl-10 group">
                  <div className="absolute left-4 top-2 bottom-0 w-[1px] bg-border group-last:bg-transparent" />
                  <div className="absolute left-0 top-0 w-8 h-8 rounded-full bg-accent border flex items-center justify-center text-xs font-bold text-primary group-hover:scale-110 transition-transform">
                    {i + 1}
                  </div>
                  <div className="space-y-4">
                    <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                      <div className="space-y-2 flex-1">
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
                      <div className="flex items-center gap-1 no-print">
                        {[1, 2, 3, 4, 5].map(score => (
                          <button 
                            key={score}
                            disabled={isSubmitted}
                            onClick={() => setScores(prev => ({ ...prev, [q.id]: score }))}
                            className={cn(
                              "w-8 h-8 rounded-lg text-xs font-bold transition-all border",
                              scores[q.id] === score 
                                ? "bg-primary text-primary-foreground border-primary shadow-lg shadow-primary/20" 
                                : isSubmitted
                                  ? "bg-muted text-muted-foreground border-transparent cursor-not-allowed"
                                  : "hover:bg-accent text-muted-foreground hover:text-foreground"
                            )}
                          >
                            {score}
                          </button>
                        ))}
                      </div>
                    </div>
                    
                    {q.expected && q.expected.length > 0 && (
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
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: Score Summary */}
        <div className="space-y-6 no-print">
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
                      <p className="text-xs font-bold leading-tight mt-1">
                        {isSubmitted 
                          ? `Based on scorecard score ${avgScore}, recruiter recommends: ${Number(avgScore) > 3.5 ? 'Proceed with offer / next rounds.' : 'Do not hire candidate.'}`
                          : `"Based on match score ${avgScore}, candidate is highly recommended for hire."`
                        }
                      </p>
                   </div>
                </div>
              </div>

              <div className="pt-10 flex flex-col gap-3">
                 <button 
                   onClick={handleMoveToFinalRound}
                   disabled={candidateStatus === 'advanced' || candidateStatus === 'rejected'}
                   className={cn(
                     "w-full py-4 text-white rounded-2xl font-bold text-sm shadow-xl transition-all hover:scale-[1.02] active:scale-95",
                     candidateStatus === 'advanced'
                       ? "bg-green-600/50 cursor-not-allowed shadow-none"
                       : candidateStatus === 'rejected'
                         ? "bg-muted text-muted-foreground cursor-not-allowed shadow-none"
                         : "bg-green-500 shadow-green-500/20"
                   )}
                 >
                   {candidateStatus === 'advanced' ? 'Moved to Final Round' : 'Move to Final Round'}
                 </button>
                 <button 
                   onClick={handleRejectCandidate}
                   disabled={candidateStatus === 'rejected'}
                   className={cn(
                     "w-full py-4 border rounded-2xl font-bold text-sm transition-all",
                     candidateStatus === 'rejected'
                       ? "bg-red-500/20 text-red-500 border-red-500/30 cursor-not-allowed"
                       : "bg-red-500/10 text-red-500 border-red-500/20 hover:bg-red-500/20"
                   )}
                 >
                   {candidateStatus === 'rejected' ? 'Rejected' : 'Reject Candidate'}
                 </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
