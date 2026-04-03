import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { 
  Upload as UploadIcon, 
  FileText, 
  X, 
  CheckCircle2, 
  AlertCircle, 
  Zap, 
  Bot,
  CloudUpload,
  FileType
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface UploadingFile {
  id: string;
  name: string;
  size: number;
  progress: number;
  status: 'PENDING' | 'UPLOADING' | 'SCREENING' | 'COMPLETED' | 'ERROR';
  error?: string;
  score?: number;
}

export default function UploadPage() {
  const [files, setFiles] = useState<UploadingFile[]>([]);
  const [isBatchProcessing, setIsBatchProcessing] = useState(false);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles = acceptedFiles.map(file => ({
      id: Math.random().toString(36).substr(2, 9),
      name: file.name,
      size: file.size,
      progress: 0,
      status: 'PENDING' as const
    }));
    setFiles(prev => [...prev, ...newFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ 
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 50
  });

  const startUpload = () => {
    setIsBatchProcessing(true);
    // Simulated upload and SSE logic
    setFiles(prev => prev.map(f => {
      if (f.status === 'PENDING') {
        let progress = 0;
        const interval = setInterval(() => {
          progress += Math.random() * 30;
          if (progress >= 100) {
            progress = 100;
            clearInterval(interval);
            // Move to SCREENING
            setFiles(current => current.map(curr => 
              curr.id === f.id ? { ...curr, status: 'SCREENING', progress: 100 } : curr
            ));
            // Simulate screening completion
            setTimeout(() => {
              setFiles(current => current.map(curr => 
                curr.id === f.id ? { 
                  ...curr, 
                  status: 'COMPLETED', 
                  score: Math.floor(Math.random() * 40) + 60 
                } : curr
              ));
            }, 2000);
          } else {
            setFiles(current => current.map(curr => 
              curr.id === f.id ? { ...curr, progress, status: 'UPLOADING' } : curr
            ));
          }
        }, 300);
      }
      return f;
    }));
  };

  const removeFile = (id: string) => {
    setFiles(prev => prev.filter(f => f.id !== id));
  };

  return (
    <div className="max-w-4xl mx-auto space-y-10 pb-20">
      <div className="text-center space-y-4">
        <h1 className="text-4xl font-bold font-display tracking-tight uppercase italic underline decoration-primary underline-offset-8">Bulk Screening Lab</h1>
        <p className="text-muted-foreground max-w-lg mx-auto text-sm">Upload up to 50 resumes simultaneously. Our AI engine will deduplicate, parse, and score them in real-time.</p>
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
            <CloudUpload className="w-10 h-10 text-primary" />
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
               disabled={isBatchProcessing}
               className="flex items-center gap-2 px-6 py-2.5 bg-primary text-primary-foreground rounded-full text-xs font-black uppercase tracking-widest disabled:opacity-50 shadow-xl shadow-primary/20 hover:scale-105 active:scale-95 transition-all"
             >
               <Zap className="w-4 h-4 fill-primary-foreground" />
               Start AI Batch Script
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

                {file.status === 'COMPLETED' && file.score && (
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
