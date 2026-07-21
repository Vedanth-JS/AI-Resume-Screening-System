import React, { useState, useEffect, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { Card, Button, Badge, ProgressBar } from "./ui";
import { jobService, candidateService } from "../services/api";
import api from "../services/api";
import { Briefcase, ArrowLeft, Users, Brain, Zap } from "lucide-react";

export default function JobDetail() {
  const { id } = useParams<{ id: string }>();
  const [job, setJob] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [jobRes, histRes] = await Promise.all([
        jobService.getJob(id!),
        api.get(`/history/${id}`),
      ]);
      setJob(jobRes.data);
      setHistory(histRes.data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    try {
      await candidateService.uploadResume(Number(id), file);
      setFile(null);
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-12 h-12 border-[4px] border-black border-t-[#FF6B35] rounded-full animate-spin" />
      </div>
    );
  }

  if (!job) {
    return (
      <div className="text-center py-20">
        <h2 className="text-3xl font-black mb-4">Job Not Found</h2>
        <Link to="/jobs" className="text-[#FF6B35] font-bold underline">
          ← Back to Jobs
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <Link to="/jobs" className="inline-flex items-center gap-2 text-black/60 font-bold hover:text-black">
        <ArrowLeft className="w-4 h-4" /> Back to Jobs
      </Link>

      <Card>
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="w-16 h-16 bg-[#FFE566] border-[3px] border-black rounded-2xl flex items-center justify-center flex-shrink-0">
              <Briefcase className="w-8 h-8 text-black" />
            </div>
            <div>
              <h2 className="text-3xl font-black mb-2">{job.title}</h2>
              <div className="flex flex-wrap gap-2 mb-3">
                {(job.required_skills || []).map((s: string) => (
                  <Badge key={s} variant="neutral">{s}</Badge>
                ))}
              </div>
              <p className="text-sm font-semibold text-black/60">{job.min_experience}+ yrs exp · {job.required_education}</p>
            </div>
          </div>
          <div className="text-right flex-shrink-0">
            <div className="text-xs font-black uppercase mb-1">Candidates</div>
            <div className="text-5xl font-black">{history.length}</div>
          </div>
        </div>
        {job.description && (
          <div className="mt-6 pt-6 border-t-[3px] border-black">
            <h4 className="font-black text-sm uppercase mb-2">Job Description</h4>
            <p className="text-sm font-semibold text-black/70 leading-relaxed">{job.description}</p>
          </div>
        )}
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Upload */}
        <Card header={<h3 className="font-black text-sm">Screen New Resume</h3>}>
          <div className="space-y-4">
            {!file ? (
              <label className="flex flex-col items-center justify-center h-40 border-[3px] border-dashed border-black/20 rounded-2xl cursor-pointer hover:border-[#FF6B35] transition-colors">
                <p className="font-bold text-black/50">Drop PDF or click to select</p>
                <input type="file" className="hidden" onChange={(e) => setFile(e.target.files?.[0] || null)} accept=".pdf,.txt" />
              </label>
            ) : (
              <div className="flex items-center justify-between p-4 rounded-xl bg-[#F0F0F0] border-[3px] border-black">
                <p className="font-bold text-sm truncate max-w-[200px]">{file.name}</p>
                <Button variant="ghost" size="sm" onClick={() => setFile(null)}>Remove</Button>
              </div>
            )}
            <Button onClick={handleUpload} loading={uploading} disabled={!file} className="w-full">
              <Zap className="w-4 h-4" /> Process Candidate
            </Button>
          </div>
        </Card>

        {/* Candidates */}
        <Card header={<h3 className="font-black text-sm">Screened Candidates ({history.length})</h3>}>
          {history.length === 0 ? (
            <p className="text-black/50 font-bold text-center py-8">No candidates screened yet.</p>
          ) : (
            <div className="space-y-2">
              {history
                .sort((a, b) => (b.final_score || 0) - (a.final_score || 0))
                .slice(0, 10)
                .map((h) => {
                  const score = h.final_score ?? 0;
                  const color = score >= 70 ? "green" : score >= 40 ? "amber" : "red";
                  return (
                    <div key={h.candidate_id} className="flex items-center justify-between p-3 rounded-xl bg-[#F5F5F5] border-[2px] border-black">
                      <div>
                        <p className="font-bold text-sm">{h.candidate_name}</p>
                        <p className="text-xs text-black/50">{new Date(h.created_at || Date.now()).toLocaleDateString()}</p>
                      </div>
                      <div className="flex items-center gap-3">
                        <ProgressBar value={score} color={color} className="w-24" />
                        <span className="font-black text-lg">{Math.round(score)}%</span>
                      </div>
                    </div>
                  );
                })}
              {history.length >= 2 && (
                <Link
                  to={`/compare/${id}?ids=${history.slice(0, 3).map((h: any) => h.candidate_id).join(",")}`}
                  className="block w-full mt-2 py-2 border-[2px] border-black rounded-xl bg-[#4D9DE0] text-white font-black text-xs uppercase text-center hover:bg-[#3A89CC] transition-colors"
                >
                  Compare Top 3
                </Link>
              )}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
