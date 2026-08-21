import React, { useState, useEffect, useCallback, useRef } from "react";
import { pipelineService, jobService } from "../services/api";
import { Users, ChevronDown, GripVertical, Star, AlertCircle, CheckCircle2, Clock, XCircle, Gift } from "lucide-react";

/* ─── Stage configuration ─────────────────────────────────────────────── */
const STAGES = [
  {
    key: "APPLIED",
    label: "Applied",
    color: "from-violet-500/20 to-violet-600/10",
    border: "border-violet-500/30",
    badge: "bg-violet-500/20 text-violet-300",
    icon: Clock,
    dot: "bg-violet-400",
  },
  {
    key: "SCREENING",
    label: "Screening",
    color: "from-blue-500/20 to-blue-600/10",
    border: "border-blue-500/30",
    badge: "bg-blue-500/20 text-blue-300",
    icon: AlertCircle,
    dot: "bg-blue-400",
  },
  {
    key: "INTERVIEW",
    label: "Interview",
    color: "from-amber-500/20 to-amber-600/10",
    border: "border-amber-500/30",
    badge: "bg-amber-500/20 text-amber-300",
    icon: Star,
    dot: "bg-amber-400",
  },
  {
    key: "OFFER",
    label: "Offer",
    color: "from-emerald-500/20 to-emerald-600/10",
    border: "border-emerald-500/30",
    badge: "bg-emerald-500/20 text-emerald-300",
    icon: Gift,
    dot: "bg-emerald-400",
  },
  {
    key: "REJECTED",
    label: "Rejected",
    color: "from-red-500/20 to-red-600/10",
    border: "border-red-500/30",
    badge: "bg-red-500/20 text-red-300",
    icon: XCircle,
    dot: "bg-red-400",
  },
];

const VERDICT_COLORS: Record<string, string> = {
  ACCEPT: "text-emerald-400 bg-emerald-400/10 border-emerald-400/30",
  REVIEW: "text-amber-400 bg-amber-400/10 border-amber-400/30",
  REJECT: "text-red-400 bg-red-400/10 border-red-400/30",
};

/* ─── Candidate Card ──────────────────────────────────────────────────── */
function CandidateCard({
  card,
  onDragStart,
}: {
  card: any;
  onDragStart: (e: React.DragEvent, card: any) => void;
}) {
  const initials = (card.candidate_name || "?")
    .split(" ")
    .map((n: string) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  const score = card.score != null ? Math.round(card.score) : null;
  const scoreColor =
    score === null
      ? "text-slate-400"
      : score >= 70
      ? "text-emerald-400"
      : score >= 40
      ? "text-amber-400"
      : "text-red-400";

  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, card)}
      className="group bg-slate-800/60 border border-slate-700/50 rounded-xl p-3.5 cursor-grab active:cursor-grabbing hover:border-slate-600 hover:bg-slate-800/90 transition-all duration-150 shadow-sm hover:shadow-md"
    >
      <div className="flex items-start gap-3">
        {/* Avatar */}
        <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center text-white text-xs font-bold shrink-0 shadow-sm">
          {initials}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-slate-100 truncate leading-tight">
            {card.candidate_name}
          </p>
          <p className="text-xs text-slate-400 truncate mt-0.5">
            {card.candidate_email}
          </p>
        </div>
        {/* Drag handle */}
        <GripVertical className="w-4 h-4 text-slate-600 group-hover:text-slate-400 transition-colors shrink-0 mt-0.5" />
      </div>

      {/* Score row */}
      <div className="flex items-center justify-between mt-3">
        {score !== null ? (
          <span className={`text-xs font-bold ${scoreColor}`}>
            {score}
            <span className="text-slate-500 font-normal">/100</span>
          </span>
        ) : (
          <span className="text-xs text-slate-500">No score yet</span>
        )}
        {card.verdict && (
          <span
            className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${
              VERDICT_COLORS[card.verdict] || "text-slate-400 bg-slate-400/10 border-slate-400/20"
            }`}
          >
            {card.verdict}
          </span>
        )}
      </div>

      {/* Matched skills */}
      {card.matched_skills && card.matched_skills.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2.5">
          {(card.matched_skills as string[]).slice(0, 3).map((s: string) => (
            <span
              key={s}
              className="text-[10px] bg-violet-500/10 text-violet-300 px-1.5 py-0.5 rounded-md border border-violet-500/20"
            >
              {s}
            </span>
          ))}
          {card.matched_skills.length > 3 && (
            <span className="text-[10px] text-slate-500">
              +{card.matched_skills.length - 3} more
            </span>
          )}
        </div>
      )}
    </div>
  );
}

/* ─── Column ──────────────────────────────────────────────────────────── */
function Column({
  stage,
  cards,
  onDrop,
  onDragOver,
}: {
  stage: (typeof STAGES)[0];
  cards: any[];
  onDrop: (e: React.DragEvent, stageKey: string) => void;
  onDragOver: (e: React.DragEvent) => void;
}) {
  const [isDragOver, setIsDragOver] = useState(false);
  const Icon = stage.icon;

  return (
    <div
      className={`flex-1 min-w-[220px] flex flex-col rounded-xl border ${stage.border} bg-gradient-to-b ${stage.color} transition-all duration-150 ${isDragOver ? "ring-2 ring-inset ring-white/20 scale-[1.01]" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragOver(true);
        onDragOver(e);
      }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={(e) => {
        setIsDragOver(false);
        onDrop(e, stage.key);
      }}
    >
      {/* Column header */}
      <div className="px-4 py-3 border-b border-white/5 flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${stage.dot}`} />
        <Icon className="w-3.5 h-3.5 text-slate-400" />
        <span className="text-sm font-semibold text-slate-200">{stage.label}</span>
        <span
          className={`ml-auto text-xs font-bold px-2 py-0.5 rounded-full ${stage.badge}`}
        >
          {cards.length}
        </span>
      </div>

      {/* Cards */}
      <div className="flex-1 p-2 space-y-2 overflow-y-auto max-h-[calc(100vh-220px)] min-h-[80px]">
        {cards.length === 0 && (
          <div className="flex items-center justify-center h-16 text-slate-600 text-xs select-none">
            Drop here
          </div>
        )}
        {cards.map((card: any) => (
          <CandidateCard
            key={card.application_id}
            card={card}
            onDragStart={(e, c) => {
              e.dataTransfer.setData("application_id", String(c.application_id));
              e.dataTransfer.setData("from_stage", stage.key);
            }}
          />
        ))}
      </div>
    </div>
  );
}

/* ─── Main Pipeline Page ─────────────────────────────────────────────── */
export default function Pipeline() {
  const [stages, setStages] = useState<Record<string, any[]>>({
    APPLIED: [],
    SCREENING: [],
    INTERVIEW: [],
    OFFER: [],
    REJECTED: [],
  });
  const [jobs, setJobs] = useState<any[]>([]);
  const [selectedJob, setSelectedJob] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

  const fetchPipeline = useCallback(async (jobId?: number | null) => {
    setLoading(true);
    setError(null);
    try {
      const res = await pipelineService.getStages(jobId || undefined);
      setStages(res.data.stages);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Failed to load pipeline");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    jobService.getJobs().then((res) => {
      const items = res.data?.items || res.data || [];
      setJobs(items);
    });
    fetchPipeline();
  }, [fetchPipeline]);

  const handleDrop = async (e: React.DragEvent, toStage: string) => {
    e.preventDefault();
    const appId = parseInt(e.dataTransfer.getData("application_id"));
    const fromStage = e.dataTransfer.getData("from_stage");
    if (!appId || fromStage === toStage) return;

    // Optimistic update
    setStages((prev) => {
      const card = prev[fromStage]?.find((c: any) => c.application_id === appId);
      if (!card) return prev;
      return {
        ...prev,
        [fromStage]: prev[fromStage].filter((c: any) => c.application_id !== appId),
        [toStage]: [...(prev[toStage] || []), card],
      };
    });

    try {
      await pipelineService.updateStatus(appId, toStage);
      showToast(`Moved to ${toStage}`);
    } catch {
      // Revert on failure
      fetchPipeline(selectedJob);
      showToast("Failed to update status — reverted");
    }
  };

  const totalCandidates = Object.values(stages).reduce(
    (acc, arr) => acc + (arr?.length || 0),
    0
  );

  return (
    <div className="h-full flex flex-col gap-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-3">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shadow-md shadow-violet-500/20">
            <Users className="w-4.5 h-4.5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-100">Candidate Pipeline</h1>
            <p className="text-xs text-slate-400">
              {totalCandidates} candidate{totalCandidates !== 1 ? "s" : ""} · Drag to move stages
            </p>
          </div>
        </div>

        {/* Job filter */}
        <div className="sm:ml-auto flex items-center gap-2">
          <div className="relative">
            <select
              className="appearance-none bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-2 pr-8 focus:outline-none focus:ring-2 focus:ring-violet-500/50 cursor-pointer"
              value={selectedJob ?? ""}
              onChange={(e) => {
                const val = e.target.value ? Number(e.target.value) : null;
                setSelectedJob(val);
                fetchPipeline(val);
              }}
            >
              <option value="">All Jobs</option>
              {jobs.map((j: any) => (
                <option key={j.id} value={j.id}>
                  {j.title}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400 pointer-events-none" />
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3 text-red-300 text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Kanban Board */}
      {loading ? (
        <div className="flex-1 grid grid-cols-5 gap-3">
          {STAGES.map((s) => (
            <div
              key={s.key}
              className="rounded-xl bg-slate-800/40 border border-slate-700/30 animate-pulse h-64"
            />
          ))}
        </div>
      ) : (
        <div className="flex-1 flex gap-3 overflow-x-auto pb-2">
          {STAGES.map((stage) => (
            <Column
              key={stage.key}
              stage={stage}
              cards={stages[stage.key] || []}
              onDrop={handleDrop}
              onDragOver={(e) => e.preventDefault()}
            />
          ))}
        </div>
      )}

      {/* Toast notification */}
      {toast && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 bg-slate-800 border border-slate-700 shadow-2xl rounded-xl px-5 py-3 flex items-center gap-2 text-sm text-slate-200 animate-fade-in">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          {toast}
        </div>
      )}
    </div>
  );
}
