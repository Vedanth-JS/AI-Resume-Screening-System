import React, { useState, useCallback, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { 
  Upload as UploadIcon, 
  FileText, 
  X, 
  CheckCircle2, 
  AlertCircle, 
  Zap, 
  Bot,
  UploadCloud,
  FileType
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { candidateService, jobService, taskService, extractErrorMessage } from '@/services/api';

interface UploadingFile {
  id: string;
  name: string;
  size: number;
  progress: number;
  status: 'PENDING' | 'UPLOADING' | 'SCREENING' | 'COMPLETED' | 'ERROR';
  error?: string;
  score?: number;
  verdict?: string;
  file?: File;
  canRetry?: boolean;
  task_id?: string;
  currentStep?: string;
}

// Pipeline step labels keyed by progress range
const PIPELINE_STEPS = [
  { from: 0,  to: 14,  label: 'Queued',                 icon: '⏳' },
  { from: 15, to: 29,  label: 'Checking cache',          icon: '💾' },
  { from: 30, to: 44,  label: 'Parsing resume',          icon: '📄' },
  { from: 45, to: 64,  label: 'Generating embeddings',   icon: '🧠' },
  { from: 65, to: 79,  label: 'Scoring (keyword+semantic)', icon: '📊' },
  { from: 80, to: 89,  label: 'XAI reasoning',           icon: '✨' },
  { from: 90, to: 99,  label: 'Saving results',          icon: '💾' },
  { from: 100, to: 100, label: 'Complete!',              icon: '✅' },
]

function getStepLabel(progress: number): { label: string; icon: string } {
  return PIPELINE_STEPS.find(s => progress >= s.from && progress <= s.to)
    ?? { label: 'Processing…', icon: '⚙️' }
}



export default function UploadPage() {
  const [files, setFiles] = useState<UploadingFile[]>([]);
  const [isBatchProcessing, setIsBatchProcessing] = useState(false);
  const [jobs, setJobs] = useState<any[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string>('');

  useEffect(() => {
    const fetchJobs = async () => {
      try {
        const res = await jobService.getJobs();
        const items = res.data?.items ?? (Array.isArray(res.data) ? res.data : []);
        if (items.length > 0) {
          setJobs(items);
          setSelectedJobId(String(items[0].id));
        }
      } catch (err) {
        console.error("Failed to fetch jobs", err);
      }
    };
    fetchJobs();
  }, []);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const validFiles = acceptedFiles.filter(file => {
      // Validate file type
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        return false;
      }
      // Validate file size (10MB)
      if (file.size > 10 * 1024 * 1024) {
        return false;
      }
      return true;
    });

    const newFiles = validFiles.map(file => ({
      id: Math.random().toString(36).substr(2, 9),
      name: file.name,
      size: file.size,
      progress: 0,
      status: 'PENDING' as const,
      file,
      canRetry: true
    }));
    setFiles(prev => [...prev, ...newFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ 
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 50
  });

  const retryFile = async (id: string) => {
    const file = files.find(f => f.id === id);
    if (!file || !file.file) return;

    setFiles(current => current.map(curr => 
      curr.id === id ? { ...curr, status: 'PENDING', progress: 0, error: undefined } : curr
    ));

    // Trigger upload immediately
    await processSingleFile(file);
  };

  const processSingleFile = async (file: UploadingFile) => {
    if (!file.file) return;

    setFiles(current => current.map(curr =>
      curr.id === file.id ? { ...curr, progress: 20, status: 'UPLOADING', currentStep: 'Uploading…' } : curr
    ));

    try {
      setFiles(current => current.map(curr =>
        curr.id === file.id ? { ...curr, status: 'SCREENING', progress: 30, currentStep: 'Starting AI pipeline…' } : curr
      ));

      const res = await candidateService.uploadResume(selectedJobId, file.file);

      if (res.data && res.data.success === false) {
        throw new Error(res.data.message || 'Upload failed');
      }

      // Check if we got a task_id for async polling
      const taskId = res.data?.task_id;
      const analysis = res.data?.analysis;

      if (taskId) {
        // Poll Celery task status every 2 seconds
        let done = false;
        let attempts = 0;
        const MAX_ATTEMPTS = 90; // max 3 min

        setFiles(current => current.map(curr =>
          curr.id === file.id ? { ...curr, task_id: taskId, currentStep: 'AI pipeline running…' } : curr
        ));

        while (!done && attempts < MAX_ATTEMPTS) {
          await new Promise(r => setTimeout(r, 2000));
          attempts++;

          try {
            const statusRes = await taskService.getStatus(taskId);
            const statusData = statusRes.data;
            const pct = Math.min(statusData.progress ?? 30, 99);
            const step = statusData.current_step || getStepLabel(pct).label;

            setFiles(current => current.map(curr =>
              curr.id === file.id ? { ...curr, progress: pct, currentStep: step } : curr
            ));

            if (['SUCCESS', 'FAILED', 'REVOKED'].includes(statusData.status)) {
              done = true;
              if (statusData.status === 'SUCCESS') {
                const score = statusData.result?.score ?? analysis?.score;
                const verdict = statusData.result?.verdict ?? analysis?.breakdown?.xai?.verdict;
                setFiles(current => current.map(curr =>
                  curr.id === file.id
                    ? { ...curr, status: 'COMPLETED', progress: 100, score, verdict, currentStep: 'Complete!' }
                    : curr
                ));
              } else {
                throw new Error(statusData.error || 'Task failed');
              }
            }
          } catch (pollErr) {
            // Ignore transient poll errors, keep retrying
          }
        }

        if (!done) {
          // Timed out — show best-effort result
          setFiles(current => current.map(curr =>
            curr.id === file.id ? { ...curr, status: 'COMPLETED', progress: 100, score: res.data?.analysis?.score, currentStep: 'Complete (timed out polling)' } : curr
          ));
        }
      } else {
        // Synchronous response (no task_id)
        const score = analysis?.score ?? res.data?.score;
        const verdict = analysis?.breakdown?.xai?.verdict;
        setFiles(current => current.map(curr =>
          curr.id === file.id
            ? { ...curr, status: 'COMPLETED', progress: 100, score, verdict, currentStep: 'Complete!' }
            : curr
        ));
      }
    } catch (err: any) {
      console.error('Upload error:', err);

      const errorMessage = extractErrorMessage(err, 'Upload failed');

      setFiles(current => current.map(curr =>
        curr.id === file.id ? { ...curr, status: 'ERROR', progress: 100, error: errorMessage } : curr
      ));
    }
  };


  const startUpload = async () => {
    if (!selectedJobId) {
      alert("Please select a job first.");
      return;
    }
    
    setIsBatchProcessing(true);
    
    const pendingFiles = files.filter(f => f.status === 'PENDING');
    
    for (const f of pendingFiles) {
      await processSingleFile(f);
    }
    
    setIsBatchProcessing(false);
  };

  const canStartBatch = () => {
    const pendingFiles = files.filter(f => f.status === 'PENDING');
    return pendingFiles.length > 0 && !!selectedJobId && !isBatchProcessing;
  };

  const removeFile = (id: string) => {
    setFiles(prev => prev.filter(f => f.id !== id));
  };

  return (
    <div className="max-w-4xl mx-auto space-y-10 pb-20">
      <div className="text-center space-y-4">
        <h1 className="text-4xl font-bold font-display tracking-tight uppercase italic underline decoration-primary underline-offset-8">Bulk Screening Lab</h1>
        <p className="text-muted-foreground max-w-lg mx-auto text-sm">Upload up to 50 resumes simultaneously. Our AI engine will deduplicate, parse, and score them in real-time.</p>
        
        <div className="pt-4 max-w-md mx-auto animate-in fade-in slide-in-from-top-2">
          <label className="block text-xs font-bold uppercase tracking-widest text-muted-foreground mb-2">Target Job Requisition</label>
          {jobs.length > 0 ? (
            <select 
              value={selectedJobId} 
              onChange={(e) => setSelectedJobId(e.target.value)}
              className="w-full h-12 px-4 bg-card border rounded-2xl text-sm font-medium focus:ring-2 focus:ring-primary outline-none shadow-sm transition-all"
            >
              {jobs.map(job => (
                <option key={job.id} value={job.id}>{job.title}</option>
              ))}
            </select>
          ) : (
            <p className="text-sm text-amber-500 font-medium">
              No jobs found. Create a job posting first, then return here to screen resumes.
            </p>
          )}
        </div>
      </div>

      {/* Dropzone */}
      <div 
        {...getRootProps()} 
        className={cn(
          "relative h-80 border-4 border-dashed rounded-[40px] flex flex-col items-center justify-center transition-all cursor-pointer overflow-hidden group",
          isDragActive ? "border-primary bg-primary/5 scale-[1.02]" : "border-border hover:border-primary/50 hover:bg-accent/20"
        )}
      >
        <div className="absolute inset-0 bg-primary/5 rounded-full blur-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-1000 -z-10" />
        <div className="flex flex-col items-center space-y-6 text-center px-10">
          <div className="w-20 h-20 rounded-3xl bg-accent fill-primary/10 flex items-center justify-center shadow-inner group-hover:scale-110 transition-transform">
            <UploadCloud className="w-10 h-10 text-primary" />
          </div>
          <div className="space-y-2">
            <p className="text-xl font-bold font-display">Drag & Drop Resumes</p>
            <p className="text-xs text-muted-foreground font-medium italic underline decoration-muted-foreground/30 underline-offset-4">Supports original PDF files only (Max 10MB each)</p>
          </div>
          <button className="px-8 py-3 bg-primary text-primary-foreground rounded-full text-xs font-black uppercase tracking-widest shadow-xl shadow-primary/20 hover:-translate-y-1 transition-all">Select Files</button>
        </div>
        <input {...getInputProps()} />
      </div>

      {/* File List */}
      {files.length > 0 && (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
          <div className="flex items-center justify-between">
             <h3 className="text-xl font-bold font-display flex items-center gap-2 underline decoration-primary/20 underline-offset-4 decoration-2">
               Queue Management ({files.length})
             </h3>
             <button 
               onClick={startUpload}
               disabled={!canStartBatch()}
               className="flex items-center gap-2 px-6 py-2.5 bg-primary text-primary-foreground rounded-full text-xs font-black uppercase tracking-widest disabled:opacity-50 disabled:cursor-not-allowed shadow-xl shadow-primary/20 hover:scale-105 active:scale-95 transition-all"
             >
               {isBatchProcessing ? (
                 <>
                   <div className="w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                   Processing...
                 </>
               ) : (
                 <>
                   <Zap className="w-4 h-4 fill-primary-foreground" />
                   Start AI Batch Script
                 </>
               )}
             </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {files.map((file) => (
              <div key={file.id} className="bg-card border rounded-3xl p-6 relative overflow-hidden group hover:border-primary/50 transition-all shadow-sm">
                <div className="flex items-start justify-between relative z-10">
                  <div className="flex items-center gap-4">
                    <div className={cn(
                      "w-12 h-12 rounded-2xl flex items-center justify-center border shadow-sm",
                      file.status === 'COMPLETED' ? "bg-green-500/10 text-green-500 border-green-500/20" : "bg-accent/50 text-muted-foreground"
                    )}>
                      {file.status === 'COMPLETED' ? <CheckCircle2 className="w-6 h-6" /> : <FileType className="w-6 h-6" />}
                    </div>
                    <div className="min-w-0">
                      <p className="text-[11px] font-black uppercase tracking-widest leading-none truncate max-w-[150px]">{file.name}</p>
                      <p className="text-[10px] text-muted-foreground font-bold mt-1">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                    </div>
                  </div>
                  <button onClick={() => removeFile(file.id)} className="p-1 hover:bg-destructive/10 text-muted-foreground hover:text-destructive rounded-lg transition-all">
                    <X className="w-4 h-4" />
                  </button>
                </div>

                <div className="mt-6 space-y-2 relative z-10">
                   <div className="flex justify-between items-center text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                      <span>{file.status}</span>
                      <span>{file.status === 'COMPLETED' ? '100%' : `${Math.round(file.progress)}%`}</span>
                   </div>
                   <div className="w-full h-1.5 bg-accent rounded-full overflow-hidden">
                      <div 
                        className={cn(
                          "h-full rounded-full transition-all duration-300",
                          file.status === 'ERROR' ? "bg-red-500" :
                          file.status === 'COMPLETED' ? "bg-green-500" : "bg-primary"
                        )}
                        style={{ width: `${file.status === 'COMPLETED' ? 100 : file.progress}%` }}
                      />
                   </div>
                </div>

                {file.status === 'ERROR' && (
                   <div className="mt-4 flex items-center gap-2">
                     <button 
                       onClick={() => retryFile(file.id)}
                       className="flex-1 px-3 py-1.5 bg-primary text-primary-foreground rounded-lg text-[10px] font-bold uppercase tracking-wider hover:bg-primary/90 transition-all"
                     >
                       Retry
                     </button>
                     <button 
                       onClick={() => removeFile(file.id)}
                       className="px-3 py-1.5 bg-destructive/10 text-destructive rounded-lg text-[10px] font-bold uppercase tracking-wider hover:bg-destructive/20 transition-all"
                     >
                       Remove
                     </button>
                   </div>
                )}

                {file.status === 'ERROR' && file.error && (
                   <div className="mt-2 text-[9px] text-destructive font-medium truncate">
                     {file.error}
                   </div>
                )}

                {file.status === 'COMPLETED' && file.score != null && (
                   <div className="absolute top-2 right-12 flex items-center gap-1.5 px-3 py-1 bg-green-500 text-white rounded-full text-[10px] font-black italic shadow-lg shadow-green-500/20 animate-in zoom-in-50 duration-500">
                      <Bot className="w-3.5 h-3.5" />
                      SCORE: {file.score}
                   </div>
                )}
                
                <div className="absolute inset-0 bg-primary/2 opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {files.length === 0 && (
        <div className="text-center py-20 opacity-30">
          <FileText className="w-16 h-16 mx-auto text-muted-foreground mb-4" />
          <p className="text-sm font-bold uppercase tracking-widest">No candidates in queue</p>
        </div>
      )}
    </div>
  );
}
