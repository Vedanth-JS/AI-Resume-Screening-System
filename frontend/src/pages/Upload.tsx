import React, { useState, useCallback, useEffect, useMemo } from 'react';
import { useDropzone } from 'react-dropzone';
import {
  UploadCloud,
  FileText,
  X,
  CheckCircle2,
  AlertCircle,
  Zap,
  Bot,
  FileType,
  Search,
  Filter,
  Download,
  FileSpreadsheet,
  Sliders,
  Sparkles,
  GraduationCap,
  Briefcase,
  Code,
  Award,
  ChevronDown,
  RefreshCw,
  Check,
  RotateCcw,
  Info,
  ChevronRight,
  TrendingUp,
  UserCheck,
  AlertTriangle,
  BarChart3,
  Building,
  Calendar,
  Phone,
  Mail
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { atsScoringService, jobService, extractErrorMessage } from '@/services/api';

// ─── 16 Predefined Industry-Standard Job Roles ─────────────────────────────────
const PREDEFINED_ROLES = [
  'Software Engineer',
  'Senior Full Stack Engineer',
  'Java Developer',
  'Python Developer',
  'Frontend Developer',
  'Backend Developer',
  'Data Analyst',
  'Data Scientist',
  'Machine Learning Engineer',
  'AI Engineer',
  'DevOps Engineer',
  'Cloud Engineer',
  'Cybersecurity Engineer',
  'Database Administrator',
  'QA Engineer',
  'UI/UX Designer',
];

// ─── Default 8-Criteria Evaluation Weights ─────────────────────────────────────
const DEFAULT_WEIGHTS = {
  technical_skills: 30,
  jd_relevance: 20,
  relevant_experience: 15,
  project_relevance: 10,
  education_match: 10,
  certifications: 5,
  keywords_match: 5,
  resume_quality: 5,
};

interface CustomJDState {
  title: string;
  description: string;
  required_skills: string;
  preferred_skills: string;
  min_experience: number;
  educational_qualifications: string;
  mandatory_requirements: string;
}

interface UploadingFile {
  id: string;
  name: string;
  size: number;
  progress: number;
  status: 'PENDING' | 'UPLOADING' | 'SCREENING' | 'COMPLETED' | 'ERROR';
  error?: string;
  file?: File;
  currentStep?: string;
}

interface CandidateResult {
  id: string;
  rank: number;
  candidate: {
    name: string;
    email?: string;
    phone?: string;
    education?: string;
    college?: string;
    graduation_year?: string;
    technical_skills: string[];
    programming_languages: string[];
    frameworks: string[];
    databases: string[];
    tools_and_technologies: string[];
    work_experience_years: number;
    experience_entries: any[];
    internship_experience: any[];
    projects: any[];
    certifications: string[];
    achievements: string[];
    raw_text: string;
  };
  overall_ats_score: number | null;
  match_tier: string | null;
  recommendation?: {
    verdict: 'Shortlist' | 'Consider for Interview' | 'Needs Further Review' | 'Not Recommended';
    reasoning: string;
    score_explanation: string;
  };
  breakdown?: {
    technical_skills_score: number;
    jd_relevance_score: number;
    relevant_experience_score: number;
    project_relevance_score: number;
    education_match_score: number;
    certifications_score: number;
    keywords_match_score: number;
    resume_quality_score: number;
  };
  skill_gap_analysis?: {
    matching_skills: Array<{ skill: string; reason: string }>;
    missing_mandatory_skills: Array<{ skill: string; reason: string }>;
    missing_preferred_skills: Array<{ skill: string; reason: string }>;
    partially_matching_skills: Array<{ skill: string; reason: string }>;
    additional_skills: string[];
    relevant_technologies: string[];
  };
  keyword_analysis?: {
    matched_keywords: string[];
    missing_critical_keywords: string[];
    semantic_matches: Array<{ jd_term: string; resume_term: string }>;
  };
  strengths: string[];
  weaknesses: string[];
  actionable_improvements: Array<{ section: string; issue: string; suggested_fix: string }>;
  status: 'COMPLETED' | 'ERROR';
  extraction_error?: string | null;
  file_name: string;
  file_size: number;
}

// ─── Classification Color & Badge Helpers ─────────────────────────────────────
function getScoreBadge(score: number | null) {
  if (score === null || score === undefined) {
    return {
      label: 'Extraction Error',
      colorClass: 'bg-red-500/10 text-red-400 border-red-500/30',
      barColor: 'bg-red-500',
    };
  }
  if (score >= 90) {
    return {
      label: 'Excellent Match (90-100)',
      colorClass: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
      barColor: 'bg-emerald-500',
    };
  }
  if (score >= 80) {
    return {
      label: 'Strong Match (80-89)',
      colorClass: 'bg-green-500/10 text-green-400 border-green-500/30',
      barColor: 'bg-green-500',
    };
  }
  if (score >= 70) {
    return {
      label: 'Good Match (70-79)',
      colorClass: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
      barColor: 'bg-cyan-500',
    };
  }
  if (score >= 60) {
    return {
      label: 'Moderate Match (60-69)',
      colorClass: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
      barColor: 'bg-amber-500',
    };
  }
  if (score >= 40) {
    return {
      label: 'Low Match (40-59)',
      colorClass: 'bg-orange-500/10 text-orange-400 border-orange-500/30',
      barColor: 'bg-orange-500',
    };
  }
  return {
    label: 'Poor Match (0-39)',
    colorClass: 'bg-red-500/10 text-red-400 border-red-500/30',
    barColor: 'bg-red-500',
  };
}

function getRecommendationBadge(verdict?: string) {
  switch (verdict) {
    case 'Shortlist':
      return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
    case 'Consider for Interview':
      return 'bg-blue-500/10 text-blue-400 border-blue-500/30';
    case 'Needs Further Review':
      return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
    case 'Not Recommended':
      return 'bg-red-500/10 text-red-400 border-red-500/30';
    default:
      return 'bg-muted text-muted-foreground border-border';
  }
}

export default function UploadPage() {
  // ─── Mode & Requirements State ──────────────────────────────────────────────
  const [screeningMode, setScreeningMode] = useState<'PREDEFINED' | 'CUSTOM'>('PREDEFINED');
  const [selectedRole, setSelectedRole] = useState<string>('Senior Full Stack Engineer');
  const [customJD, setCustomJD] = useState<CustomJDState>({
    title: '',
    description: '',
    required_skills: '',
    preferred_skills: '',
    min_experience: 3,
    educational_qualifications: "Bachelor's Degree in Computer Science or related STEM field",
    mandatory_requirements: '',
  });

  // Configurable Weights
  const [weights, setWeights] = useState(DEFAULT_WEIGHTS);
  const [showWeightsModal, setShowWeightsModal] = useState(false);

  // Re-evaluation detection
  const [hasRequirementsChanged, setHasRequirementsChanged] = useState(false);
  const [lastScreenedRole, setLastScreenedRole] = useState<string>('');

  // ─── Files & Upload Queue ───────────────────────────────────────────────────
  const [files, setFiles] = useState<UploadingFile[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);

  // ─── Results & Report Modal ─────────────────────────────────────────────────
  const [candidates, setCandidates] = useState<CandidateResult[]>([]);
  const [selectedCandidate, setSelectedCandidate] = useState<CandidateResult | null>(null);

  // ─── Dashboard Filters & Search ─────────────────────────────────────────────
  const [searchQuery, setSearchQuery] = useState('');
  const [scoreFilter, setScoreFilter] = useState<string>('ALL');
  const [skillFilter, setSkillFilter] = useState<string>('ALL');
  const [expFilter, setExpFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [sortBy, setSortBy] = useState<'SCORE_DESC' | 'SCORE_ASC' | 'EXP_DESC' | 'NAME_ASC'>('SCORE_DESC');

  // Track role/JD changes after screening has run
  useEffect(() => {
    if (candidates.length > 0) {
      setHasRequirementsChanged(true);
    }
  }, [selectedRole, customJD, weights, screeningMode]);

  // ─── Dropzone Config ────────────────────────────────────────────────────────
  const onDrop = useCallback((acceptedFiles: File[]) => {
    const validFiles = acceptedFiles.filter((file) => {
      const name = file.name.toLowerCase();
      const isValidExt = name.endsWith('.pdf') || name.endsWith('.docx') || name.endsWith('.doc') || name.endsWith('.txt');
      if (!isValidExt) return false;
      if (file.size > 10 * 1024 * 1024) return false; // 10MB limit
      return true;
    });

    // Up to 50 files
    const newFiles: UploadingFile[] = validFiles.map((file) => ({
      id: Math.random().toString(36).substring(2, 11),
      name: file.name,
      size: file.size,
      progress: 0,
      status: 'PENDING',
      file,
      currentStep: 'Queued',
    }));

    setFiles((prev) => {
      const combined = [...prev, ...newFiles];
      return combined.slice(0, 50);
    });
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/msword': ['.doc'],
      'text/plain': ['.txt'],
    },
    maxFiles: 50,
  });

  const removeFile = (id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  };

  const clearQueue = () => {
    setFiles([]);
  };

  // ─── Format Custom JD Payload ───────────────────────────────────────────────
  const buildCustomJDPayload = () => {
    if (screeningMode !== 'CUSTOM') return null;
    return {
      title: customJD.title || 'Custom Role',
      description: customJD.description || '',
      required_skills: customJD.required_skills
        ? customJD.required_skills.split(',').map((s) => s.trim()).filter(Boolean)
        : [],
      preferred_skills: customJD.preferred_skills
        ? customJD.preferred_skills.split(',').map((s) => s.trim()).filter(Boolean)
        : [],
      min_experience: Number(customJD.min_experience) || 0,
      educational_qualifications: customJD.educational_qualifications || '',
      mandatory_requirements: customJD.mandatory_requirements
        ? customJD.mandatory_requirements.split('\n').map((s) => s.trim()).filter(Boolean)
        : [],
    };
  };

  // ─── Bulk Screen Execution ──────────────────────────────────────────────────
  const startBulkScreening = async () => {
    const pendingFiles = files.filter((f) => f.file);
    if (pendingFiles.length === 0) return;

    setIsProcessing(true);
    setHasRequirementsChanged(false);

    // Update steps
    setFiles((prev) =>
      prev.map((f) => ({ ...f, status: 'UPLOADING', progress: 25, currentStep: 'Uploading...' }))
    );

    try {
      const rawFiles = pendingFiles.map((f) => f.file as File);
      const customPayload = buildCustomJDPayload();

      // Step indicator: Extracting & Parsing
      setFiles((prev) =>
        prev.map((f) => ({ ...f, status: 'SCREENING', progress: 50, currentStep: 'Parsing & Extracting...' }))
      );

      const res = await atsScoringService.bulkScreen(
        rawFiles,
        screeningMode === 'PREDEFINED' ? selectedRole : (customPayload?.title || 'Custom Role'),
        customPayload?.description || '',
        customPayload,
        weights
      );

      // Step indicator: Scoring complete
      setFiles((prev) =>
        prev.map((f) => ({ ...f, status: 'COMPLETED', progress: 100, currentStep: 'Complete!' }))
      );

      const returnedCandidates = res.data?.candidates || [];
      setCandidates(returnedCandidates);
      setLastScreenedRole(screeningMode === 'PREDEFINED' ? selectedRole : customJD.title || 'Custom Role');
    } catch (err: any) {
      console.error('Bulk screening failed:', err);
      const msg = extractErrorMessage(err, 'Bulk screening failed');
      setFiles((prev) =>
        prev.map((f) => ({ ...f, status: 'ERROR', progress: 100, error: msg }))
      );
    } finally {
      setIsProcessing(false);
    }
  };

  // ─── Instant Re-Evaluation ──────────────────────────────────────────────────
  const reEvaluateCandidates = async () => {
    if (candidates.length === 0) return;
    setIsProcessing(true);

    try {
      const customPayload = buildCustomJDPayload();
      const res = await atsScoringService.rescore(
        candidates,
        screeningMode === 'PREDEFINED' ? selectedRole : (customPayload?.title || 'Custom Role'),
        customPayload?.description || '',
        customPayload,
        weights
      );

      if (res.data?.candidates) {
        setCandidates(res.data.candidates);
        setHasRequirementsChanged(false);
        setLastScreenedRole(screeningMode === 'PREDEFINED' ? selectedRole : customJD.title || 'Custom Role');
      }
    } catch (err) {
      console.error('Re-evaluation error:', err);
    } finally {
      setIsProcessing(false);
    }
  };

  // ─── Export Functions ───────────────────────────────────────────────────────
  const exportToCSV = async () => {
    if (candidates.length === 0) return;
    try {
      const res = await atsScoringService.exportCsv(candidates);
      const blob = new Blob([res.data], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `ats_screening_${Date.now()}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (e) {
      // Fallback client-side CSV generator
      const headers = ['Rank,Name,Email,Phone,ATS Score,Match Tier,Recommendation,Experience,Education,Top Skills\n'];
      const rows = candidates.map((c) =>
        [
          c.rank,
          `"${c.candidate.name}"`,
          c.candidate.email || '',
          c.candidate.phone || '',
          c.overall_ats_score ?? 'N/A',
          `"${c.match_tier || ''}"`,
          `"${c.recommendation?.verdict || c.status}"`,
          c.candidate.work_experience_years,
          `"${c.candidate.education || ''}"`,
          `"${c.candidate.technical_skills.slice(0, 6).join(', ')}"`,
        ].join(',')
      );
      const blob = new Blob([headers.concat(rows.join('\n'))], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `ats_screening_${Date.now()}.csv`;
      a.click();
    }
  };

  const exportToExcel = async () => {
    if (candidates.length === 0) return;
    try {
      const res = await atsScoringService.exportExcel(candidates);
      const blob = new Blob([res.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `ats_screening_${Date.now()}.xlsx`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (e) {
      // Fallback to CSV if server excel fails
      exportToCSV();
    }
  };

  const downloadCandidateReport = (candidate: CandidateResult) => {
    const reportText = `
================================================================================
ATS CANDIDATE SCREENING REPORT
================================================================================
Candidate Name: ${candidate.candidate.name}
Email:          ${candidate.candidate.email || 'N/A'}
Phone:          ${candidate.candidate.phone || 'N/A'}
Education:      ${candidate.candidate.education || 'N/A'} (${candidate.candidate.college || 'N/A'})
Experience:     ${candidate.candidate.work_experience_years} Years
Role Evaluated: ${lastScreenedRole || selectedRole}

--------------------------------------------------------------------------------
OVERALL ATS SCORE: ${candidate.overall_ats_score !== null ? candidate.overall_ats_score + '/100' : 'EXTRACTION ERROR'}
MATCH TIER:        ${candidate.match_tier || 'N/A'}
RECOMMENDATION:    ${candidate.recommendation?.verdict || 'N/A'}
--------------------------------------------------------------------------------

SCORE CALCULATION BREAKDOWN:
• Technical Skills Match (30%):  ${candidate.breakdown?.technical_skills_score ?? 0}/100
• JD Relevance (20%):            ${candidate.breakdown?.jd_relevance_score ?? 0}/100
• Relevant Experience (15%):     ${candidate.breakdown?.relevant_experience_score ?? 0}/100
• Project Relevance (10%):       ${candidate.breakdown?.project_relevance_score ?? 0}/100
• Education Match (10%):         ${candidate.breakdown?.education_match_score ?? 0}/100
• Certifications (5%):           ${candidate.breakdown?.certifications_score ?? 0}/100
• Keywords Match (5%):           ${candidate.breakdown?.keywords_match_score ?? 0}/100
• Resume Quality (5%):           ${candidate.breakdown?.resume_quality_score ?? 0}/100

SKILL GAP ANALYSIS:
Matching Skills:
${candidate.skill_gap_analysis?.matching_skills.map((m) => `  ✓ ${m.skill}: ${m.reason}`).join('\n') || '  None'}

Missing Mandatory Skills:
${candidate.skill_gap_analysis?.missing_mandatory_skills.map((m) => `  ✗ ${m.skill}: ${m.reason}`).join('\n') || '  None'}

Missing Preferred Skills:
${candidate.skill_gap_analysis?.missing_preferred_skills.map((m) => `  - ${m.skill}: ${m.reason}`).join('\n') || '  None'}

STRENGTHS:
${candidate.strengths.map((s) => `  • ${s}`).join('\n') || '  None'}

CRITICAL GAPS / WEAKNESSES:
${candidate.weaknesses.map((w) => `  • ${w}`).join('\n') || '  None'}

ACTIONABLE IMPROVEMENTS (XYZ FORMULA):
${candidate.actionable_improvements.map((a) => `  [${a.section}] ${a.issue}\n    Fix: ${a.suggested_fix}`).join('\n\n') || '  None'}

RECRUITER REASONING:
${candidate.recommendation?.reasoning || 'N/A'}
================================================================================
Generated deterministically by AI ATS Screening Engine.
    `.trim();

    const blob = new Blob([reportText], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${candidate.candidate.name.replace(/\s+/g, '_')}_ATS_Report.txt`;
    link.click();
  };

  // ─── Filter & Sort Logic ────────────────────────────────────────────────────
  const filteredCandidates = useMemo(() => {
    return candidates
      .filter((c) => {
        // Search
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase();
          const nameMatch = c.candidate.name.toLowerCase().includes(q);
          const emailMatch = c.candidate.email?.toLowerCase().includes(q);
          const skillMatch = c.candidate.technical_skills.some((s) => s.toLowerCase().includes(q));
          if (!nameMatch && !emailMatch && !skillMatch) return false;
        }

        // Score range filter
        if (scoreFilter !== 'ALL') {
          const s = c.overall_ats_score ?? -1;
          if (scoreFilter === '90_100' && (s < 90 || s > 100)) return false;
          if (scoreFilter === '80_89' && (s < 80 || s > 89)) return false;
          if (scoreFilter === '70_79' && (s < 70 || s > 79)) return false;
          if (scoreFilter === '60_69' && (s < 60 || s > 69)) return false;
          if (scoreFilter === '40_59' && (s < 40 || s > 59)) return false;
          if (scoreFilter === '0_39' && (s < 0 || s > 39)) return false;
          if (scoreFilter === 'ERROR' && c.status !== 'ERROR') return false;
        }

        // Skill filter
        if (skillFilter !== 'ALL') {
          if (!c.candidate.technical_skills.some((s) => s.toLowerCase() === skillFilter.toLowerCase())) {
            return false;
          }
        }

        // Experience filter
        if (expFilter !== 'ALL') {
          const yrs = c.candidate.work_experience_years;
          if (expFilter === '0_1' && yrs > 1) return false;
          if (expFilter === '1_3' && (yrs < 1 || yrs > 3)) return false;
          if (expFilter === '3_5' && (yrs < 3 || yrs > 5)) return false;
          if (expFilter === '5_PLUS' && yrs < 5) return false;
        }

        // Status filter
        if (statusFilter !== 'ALL') {
          if (c.recommendation?.verdict !== statusFilter && c.status !== statusFilter) {
            return false;
          }
        }

        return true;
      })
      .sort((a, b) => {
        if (sortBy === 'SCORE_DESC') {
          return (b.overall_ats_score ?? -1) - (a.overall_ats_score ?? -1);
        }
        if (sortBy === 'SCORE_ASC') {
          return (a.overall_ats_score ?? 101) - (b.overall_ats_score ?? 101);
        }
        if (sortBy === 'EXP_DESC') {
          return b.candidate.work_experience_years - a.candidate.work_experience_years;
        }
        if (sortBy === 'NAME_ASC') {
          return a.candidate.name.localeCompare(b.candidate.name);
        }
        return 0;
      });
  }, [candidates, searchQuery, scoreFilter, skillFilter, expFilter, statusFilter, sortBy]);

  // Unique skills across candidates for skill filter dropdown
  const allDetectedSkills = useMemo(() => {
    const set = new Set<string>();
    candidates.forEach((c) => {
      c.candidate.technical_skills.forEach((s) => set.add(s));
    });
    return Array.from(set).sort();
  }, [candidates]);

  // Summary Metrics
  const metrics = useMemo(() => {
    const valid = candidates.filter((c) => c.overall_ats_score !== null);
    const avg = valid.length ? Math.round(valid.reduce((acc, c) => acc + (c.overall_ats_score || 0), 0) / valid.length) : 0;
    const shortlisted = candidates.filter((c) => c.recommendation?.verdict === 'Shortlist').length;
    const interview = candidates.filter((c) => c.recommendation?.verdict === 'Consider for Interview').length;
    const review = candidates.filter((c) => c.recommendation?.verdict === 'Needs Further Review').length;
    const low = candidates.filter((c) => c.recommendation?.verdict === 'Not Recommended' || (c.overall_ats_score ?? 0) < 40).length;
    const errors = candidates.filter((c) => c.status === 'ERROR').length;
    return { total: candidates.length, avg, shortlisted, interview, review, low, errors };
  }, [candidates]);

  return (
    <div className="max-w-6xl mx-auto space-y-10 pb-28">
      {/* ─── Header ─────────────────────────────────────────────────────────── */}
      <div className="text-center space-y-4">
        <h1 className="text-4xl font-bold font-display tracking-tight uppercase italic underline decoration-primary underline-offset-8">
          Bulk Screening Lab
        </h1>
        <p className="text-muted-foreground max-w-xl mx-auto text-sm">
          Upload up to 50 resumes simultaneously. Our AI engine will deduplicate, parse, and score them in real-time.
        </p>
      </div>

      {/* ─── Dynamic Job Role Selection (Option A vs Option B) ───────────────── */}
      <div className="bg-card border rounded-3xl p-6 shadow-sm space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border/50 pb-4">
          <div className="space-y-1">
            <h2 className="text-sm font-bold uppercase tracking-wider text-foreground flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-primary" /> Target Job Requisition & Scoring Model
            </h2>
            <p className="text-xs text-muted-foreground">
              Select an industry role benchmark or provide an exact custom Job Description.
            </p>
          </div>

          <div className="flex items-center gap-2">
            {/* Mode Switcher */}
            <div className="flex p-1 bg-accent/40 rounded-2xl border border-border/50">
              <button
                type="button"
                onClick={() => setScreeningMode('PREDEFINED')}
                className={cn(
                  "px-4 py-1.5 rounded-xl text-xs font-bold transition-all",
                  screeningMode === 'PREDEFINED'
                    ? "bg-primary text-primary-foreground shadow-md shadow-primary/20"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                Option A: Predefined Role
              </button>
              <button
                type="button"
                onClick={() => setScreeningMode('CUSTOM')}
                className={cn(
                  "px-4 py-1.5 rounded-xl text-xs font-bold transition-all",
                  screeningMode === 'CUSTOM'
                    ? "bg-primary text-primary-foreground shadow-md shadow-primary/20"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                Option B: Custom JD
              </button>
            </div>

            {/* Configurable Weights Button */}
            <button
              type="button"
              onClick={() => setShowWeightsModal(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-accent/60 hover:bg-accent text-foreground border border-border/80 rounded-xl text-xs font-bold transition-all"
            >
              <Sliders className="w-3.5 h-3.5 text-primary" />
              Weights (100%)
            </button>
          </div>
        </div>

        {/* Option A: Predefined Role Dropdown */}
        {screeningMode === 'PREDEFINED' ? (
          <div className="space-y-3">
            <label className="block text-xs font-bold uppercase tracking-widest text-muted-foreground">
              Select Predefined Role ({PREDEFINED_ROLES.length} Roles Available)
            </label>
            <div className="relative">
              <select
                value={selectedRole}
                onChange={(e) => setSelectedRole(e.target.value)}
                className="w-full h-12 px-4 pr-10 bg-card border rounded-2xl text-sm font-medium focus:ring-2 focus:ring-primary outline-none shadow-sm transition-all appearance-none cursor-pointer"
              >
                {PREDEFINED_ROLES.map((role) => (
                  <option key={role} value={role}>
                    {role}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
            </div>
            <p className="text-[11px] text-muted-foreground italic">
              Dynamically benchmarks core competencies, mandatory tools, action verbs, and experience levels for <strong className="text-primary">{selectedRole}</strong>.
            </p>
          </div>
        ) : (
          /* Option B: Custom Job Description Form */
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Job Title</label>
              <input
                type="text"
                placeholder="e.g. Lead React Native Developer"
                value={customJD.title}
                onChange={(e) => setCustomJD({ ...customJD, title: e.target.value })}
                className="w-full h-10 px-3 bg-card border rounded-xl text-xs font-medium focus:ring-2 focus:ring-primary outline-none"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Min Experience (Years)</label>
              <input
                type="number"
                min="0"
                max="25"
                value={customJD.min_experience}
                onChange={(e) => setCustomJD({ ...customJD, min_experience: Number(e.target.value) })}
                className="w-full h-10 px-3 bg-card border rounded-xl text-xs font-medium focus:ring-2 focus:ring-primary outline-none"
              />
            </div>

            <div className="md:col-span-2 space-y-1">
              <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Complete Job Description</label>
              <textarea
                rows={3}
                placeholder="Paste the full job description here (responsibilities, requirements, qualifications)..."
                value={customJD.description}
                onChange={(e) => setCustomJD({ ...customJD, description: e.target.value })}
                className="w-full p-3 bg-card border rounded-xl text-xs font-medium focus:ring-2 focus:ring-primary outline-none resize-y"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Required Technical Skills (Mandatory)
              </label>
              <input
                type="text"
                placeholder="e.g. React, TypeScript, Redux, Jest (comma-separated)"
                value={customJD.required_skills}
                onChange={(e) => setCustomJD({ ...customJD, required_skills: e.target.value })}
                className="w-full h-10 px-3 bg-card border rounded-xl text-xs font-medium focus:ring-2 focus:ring-primary outline-none"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Preferred Skills (Bonus / Nice-to-Have)
              </label>
              <input
                type="text"
                placeholder="e.g. GraphQL, Tailwind, CI/CD, Next.js"
                value={customJD.preferred_skills}
                onChange={(e) => setCustomJD({ ...customJD, preferred_skills: e.target.value })}
                className="w-full h-10 px-3 bg-card border rounded-xl text-xs font-medium focus:ring-2 focus:ring-primary outline-none"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Educational Qualifications</label>
              <input
                type="text"
                placeholder="e.g. Bachelor's in CS / IT or relevant STEM degree"
                value={customJD.educational_qualifications}
                onChange={(e) => setCustomJD({ ...customJD, educational_qualifications: e.target.value })}
                className="w-full h-10 px-3 bg-card border rounded-xl text-xs font-medium focus:ring-2 focus:ring-primary outline-none"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Mandatory Requirements / Constraints</label>
              <input
                type="text"
                placeholder="e.g. Production microservices experience, AWS certified"
                value={customJD.mandatory_requirements}
                onChange={(e) => setCustomJD({ ...customJD, mandatory_requirements: e.target.value })}
                className="w-full h-10 px-3 bg-card border rounded-xl text-xs font-medium focus:ring-2 focus:ring-primary outline-none"
              />
            </div>
          </div>
        )}

        {/* Dynamic Re-Evaluation Notice */}
        {hasRequirementsChanged && candidates.length > 0 && (
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-3.5 bg-primary/10 border border-primary/30 rounded-2xl animate-in fade-in duration-300">
            <div className="flex items-center gap-2.5 text-xs text-foreground">
              <RefreshCw className="w-4 h-4 text-primary animate-spin" />
              <span>
                Job requirements updated from <strong>{lastScreenedRole}</strong>. Re-evaluate uploaded resumes with one click.
              </span>
            </div>
            <button
              onClick={reEvaluateCandidates}
              disabled={isProcessing}
              className="px-4 py-1.5 bg-primary text-primary-foreground rounded-xl text-xs font-bold shadow-md shadow-primary/20 hover:scale-105 active:scale-95 transition-all whitespace-nowrap"
            >
              ⚡ Re-Evaluate Resumes ({candidates.length})
            </button>
          </div>
        )}
      </div>

      {/* ─── Drag & Drop Dropzone (Up to 50 Resumes) ─────────────────────────── */}
      <div
        {...getRootProps()}
        className={cn(
          "relative h-72 border-4 border-dashed rounded-[40px] flex flex-col items-center justify-center transition-all cursor-pointer overflow-hidden group",
          isDragActive ? "border-primary bg-primary/5 scale-[1.01]" : "border-border hover:border-primary/50 hover:bg-accent/20"
        )}
      >
        <div className="absolute inset-0 bg-primary/5 rounded-full blur-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-1000 -z-10" />
        <div className="flex flex-col items-center space-y-4 text-center px-10">
          <div className="w-16 h-16 rounded-3xl bg-accent fill-primary/10 flex items-center justify-center shadow-inner group-hover:scale-110 transition-transform">
            <UploadCloud className="w-8 h-8 text-primary" />
          </div>
          <div className="space-y-1">
            <p className="text-xl font-bold font-display">Drag & Drop Resumes</p>
            <p className="text-xs text-muted-foreground font-medium italic underline decoration-muted-foreground/30 underline-offset-4">
              Supports PDF, DOCX, DOC, and TXT files (Max 10MB each, up to 50 files)
            </p>
          </div>
          <button
            type="button"
            className="px-6 py-2.5 bg-primary text-primary-foreground rounded-full text-xs font-black uppercase tracking-widest shadow-xl shadow-primary/20 hover:-translate-y-0.5 transition-all"
          >
            Select Files
          </button>
        </div>
        <input {...getInputProps()} />
      </div>

      {/* ─── Queue Management ─────────────────────────────────────────────────── */}
      {files.length > 0 && (
        <div className="space-y-4 animate-in fade-in duration-300">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-bold font-display flex items-center gap-2">
              Queue Management ({files.length} / 50 Resumes)
            </h3>
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={clearQueue}
                disabled={isProcessing}
                className="text-xs text-muted-foreground hover:text-destructive transition-all"
              >
                Clear Queue
              </button>
              <button
                onClick={startBulkScreening}
                disabled={isProcessing || files.length === 0}
                className="flex items-center gap-2 px-6 py-2.5 bg-primary text-primary-foreground rounded-full text-xs font-black uppercase tracking-widest disabled:opacity-50 disabled:cursor-not-allowed shadow-xl shadow-primary/20 hover:scale-105 active:scale-95 transition-all"
              >
                {isProcessing ? (
                  <>
                    <div className="w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <Zap className="w-4 h-4 fill-primary-foreground" />
                    Start AI Bulk Screening ({files.length})
                  </>
                )}
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {files.map((file) => (
              <div
                key={file.id}
                className="bg-card border rounded-2xl p-4 relative overflow-hidden group hover:border-primary/50 transition-all shadow-sm"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3 min-w-0">
                    <div
                      className={cn(
                        "w-10 h-10 rounded-xl flex items-center justify-center border shadow-sm shrink-0",
                        file.status === 'COMPLETED'
                          ? "bg-green-500/10 text-green-500 border-green-500/20"
                          : file.status === 'ERROR'
                          ? "bg-red-500/10 text-red-500 border-red-500/20"
                          : "bg-accent/50 text-muted-foreground"
                      )}
                    >
                      {file.status === 'COMPLETED' ? (
                        <CheckCircle2 className="w-5 h-5" />
                      ) : file.status === 'ERROR' ? (
                        <AlertCircle className="w-5 h-5" />
                      ) : (
                        <FileType className="w-5 h-5" />
                      )}
                    </div>
                    <div className="min-w-0">
                      <p className="text-xs font-bold truncate">{file.name}</p>
                      <p className="text-[10px] text-muted-foreground">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                    </div>
                  </div>
                  {!isProcessing && (
                    <button
                      onClick={() => removeFile(file.id)}
                      className="p-1 text-muted-foreground hover:text-destructive rounded-lg transition-all"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>

                <div className="mt-3 space-y-1">
                  <div className="flex justify-between items-center text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                    <span>{file.currentStep || file.status}</span>
                    <span>{file.status === 'COMPLETED' ? '100%' : `${file.progress}%`}</span>
                  </div>
                  <div className="w-full h-1 bg-accent rounded-full overflow-hidden">
                    <div
                      className={cn(
                        "h-full rounded-full transition-all duration-300",
                        file.status === 'ERROR' ? "bg-red-500" : file.status === 'COMPLETED' ? "bg-green-500" : "bg-primary"
                      )}
                      style={{ width: `${file.status === 'COMPLETED' ? 100 : file.progress}%` }}
                    />
                  </div>
                  {file.error && <p className="text-[10px] text-red-400 truncate mt-1">{file.error}</p>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ─── Candidate Screening Results Dashboard ────────────────────────────── */}
      {candidates.length > 0 && (
        <div className="space-y-6 pt-4 animate-in fade-in slide-in-from-bottom-4 duration-500">
          {/* Summary Metric Cards */}
          <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
            <div className="bg-card border rounded-2xl p-4 shadow-sm">
              <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Total Resumes</p>
              <p className="text-2xl font-black font-display text-foreground mt-1">{metrics.total}</p>
            </div>
            <div className="bg-card border rounded-2xl p-4 shadow-sm">
              <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Avg ATS Score</p>
              <p className="text-2xl font-black font-display text-primary mt-1">{metrics.avg}%</p>
            </div>
            <div className="bg-card border rounded-2xl p-4 shadow-sm">
              <p className="text-[11px] font-bold uppercase tracking-wider text-emerald-400">Shortlisted</p>
              <p className="text-2xl font-black font-display text-emerald-400 mt-1">{metrics.shortlisted}</p>
            </div>
            <div className="bg-card border rounded-2xl p-4 shadow-sm">
              <p className="text-[11px] font-bold uppercase tracking-wider text-blue-400">Interview</p>
              <p className="text-2xl font-black font-display text-blue-400 mt-1">{metrics.interview}</p>
            </div>
            <div className="bg-card border rounded-2xl p-4 shadow-sm">
              <p className="text-[11px] font-bold uppercase tracking-wider text-amber-400">Review Required</p>
              <p className="text-2xl font-black font-display text-amber-400 mt-1">{metrics.review}</p>
            </div>
            <div className="bg-card border rounded-2xl p-4 shadow-sm">
              <p className="text-[11px] font-bold uppercase tracking-wider text-red-400">Low / Error</p>
              <p className="text-2xl font-black font-display text-red-400 mt-1">{metrics.low + metrics.errors}</p>
            </div>
          </div>

          {/* Search, Filter & Export Toolbar */}
          <div className="bg-card border rounded-3xl p-5 shadow-sm space-y-4">
            <div className="flex flex-col md:flex-row items-center justify-between gap-4">
              <div className="relative w-full md:w-80">
                <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Search candidate name, email, skill..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full h-10 pl-9 pr-4 bg-accent/40 border border-border/80 rounded-xl text-xs font-medium focus:ring-2 focus:ring-primary outline-none"
                />
              </div>

              <div className="flex flex-wrap items-center gap-2 w-full md:w-auto justify-end">
                {/* Score Range Filter */}
                <select
                  value={scoreFilter}
                  onChange={(e) => setScoreFilter(e.target.value)}
                  className="h-9 px-3 bg-accent/40 border border-border/80 rounded-xl text-xs font-bold text-foreground outline-none cursor-pointer"
                >
                  <option value="ALL">All Scores</option>
                  <option value="90_100">90–100: Excellent Match</option>
                  <option value="80_89">80–89: Strong Match</option>
                  <option value="70_79">70–79: Good Match</option>
                  <option value="60_69">60–69: Moderate Match</option>
                  <option value="40_59">40–59: Low Match</option>
                  <option value="0_39">0–39: Poor Match</option>
                  <option value="ERROR">Extraction Errors</option>
                </select>

                {/* Technical Skills Filter */}
                {allDetectedSkills.length > 0 && (
                  <select
                    value={skillFilter}
                    onChange={(e) => setSkillFilter(e.target.value)}
                    className="h-9 px-3 bg-accent/40 border border-border/80 rounded-xl text-xs font-bold text-foreground outline-none cursor-pointer max-w-[150px]"
                  >
                    <option value="ALL">All Skills</option>
                    {allDetectedSkills.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                )}

                {/* Experience Filter */}
                <select
                  value={expFilter}
                  onChange={(e) => setExpFilter(e.target.value)}
                  className="h-9 px-3 bg-accent/40 border border-border/80 rounded-xl text-xs font-bold text-foreground outline-none cursor-pointer"
                >
                  <option value="ALL">All Experience</option>
                  <option value="0_1">Fresher / 0–1 Yrs</option>
                  <option value="1_3">1–3 Yrs</option>
                  <option value="3_5">3–5 Yrs</option>
                  <option value="5_PLUS">5+ Yrs</option>
                </select>

                {/* Status Filter */}
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="h-9 px-3 bg-accent/40 border border-border/80 rounded-xl text-xs font-bold text-foreground outline-none cursor-pointer"
                >
                  <option value="ALL">All Status</option>
                  <option value="Shortlist">Shortlist</option>
                  <option value="Consider for Interview">Consider for Interview</option>
                  <option value="Needs Further Review">Needs Further Review</option>
                  <option value="Not Recommended">Not Recommended</option>
                </select>

                {/* Sort By */}
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as any)}
                  className="h-9 px-3 bg-accent/40 border border-border/80 rounded-xl text-xs font-bold text-foreground outline-none cursor-pointer"
                >
                  <option value="SCORE_DESC">Sort: Highest ATS Score</option>
                  <option value="SCORE_ASC">Sort: Lowest Score</option>
                  <option value="EXP_DESC">Sort: Experience</option>
                  <option value="NAME_ASC">Sort: Candidate Name</option>
                </select>

                {/* Export Buttons */}
                <button
                  type="button"
                  onClick={exportToCSV}
                  className="flex items-center gap-1.5 px-3 py-2 bg-accent/60 hover:bg-accent text-foreground border border-border/80 rounded-xl text-xs font-bold transition-all shadow-sm"
                  title="Export results to CSV"
                >
                  <Download className="w-3.5 h-3.5 text-primary" /> CSV
                </button>
                <button
                  type="button"
                  onClick={exportToExcel}
                  className="flex items-center gap-1.5 px-3 py-2 bg-accent/60 hover:bg-accent text-foreground border border-border/80 rounded-xl text-xs font-bold transition-all shadow-sm"
                  title="Export results to Excel (.xlsx)"
                >
                  <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" /> Excel
                </button>
              </div>
            </div>
          </div>

          {/* ─── Candidate Ranking Table ─────────────────────────────────────── */}
          <div className="bg-card border rounded-3xl overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-border bg-accent/20 text-muted-foreground uppercase tracking-widest font-bold">
                    <th className="py-4 px-4 w-16 text-center">Rank</th>
                    <th className="py-4 px-4">Candidate</th>
                    <th className="py-4 px-4 w-48">ATS Score</th>
                    <th className="py-4 px-4 w-44">Skills Match</th>
                    <th className="py-4 px-4 w-28">Experience</th>
                    <th className="py-4 px-4 w-40">Status</th>
                    <th className="py-4 px-4 w-32 text-center">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/50">
                  {filteredCandidates.map((cand) => {
                    const badge = getScoreBadge(cand.overall_ats_score);
                    const isError = cand.status === 'ERROR' || cand.overall_ats_score === null;
                    const skillsPercent = cand.breakdown?.technical_skills_score ?? 0;

                    return (
                      <tr
                        key={cand.id}
                        className="hover:bg-accent/30 transition-all cursor-pointer group"
                        onClick={() => setSelectedCandidate(cand)}
                      >
                        {/* Rank */}
                        <td className="py-4 px-4 text-center font-black">
                          <span
                            className={cn(
                              "inline-flex items-center justify-center w-7 h-7 rounded-full text-xs font-black",
                              cand.rank === 1
                                ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                                : cand.rank === 2
                                ? "bg-slate-300/20 text-slate-300 border border-slate-300/30"
                                : cand.rank === 3
                                ? "bg-amber-700/20 text-amber-600 border border-amber-700/30"
                                : "text-muted-foreground"
                            )}
                          >
                            #{cand.rank}
                          </span>
                        </td>

                        {/* Candidate Information */}
                        <td className="py-4 px-4">
                          <div className="space-y-0.5">
                            <p className="font-bold text-sm text-foreground group-hover:text-primary transition-colors">
                              {cand.candidate.name}
                            </p>
                            <p className="text-[11px] text-muted-foreground truncate max-w-[220px]">
                              {cand.candidate.email || cand.file_name}
                            </p>
                            {cand.candidate.education && (
                              <p className="text-[10px] text-muted-foreground/80 truncate max-w-[220px]">
                                {cand.candidate.education} {cand.candidate.college ? `• ${cand.candidate.college}` : ''}
                              </p>
                            )}
                          </div>
                        </td>

                        {/* ATS Score & Visual Progress Bar */}
                        <td className="py-4 px-4">
                          {isError ? (
                            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[10px] font-bold bg-red-500/10 text-red-400 border border-red-500/20">
                              <AlertCircle className="w-3 h-3" /> Extraction Error
                            </span>
                          ) : (
                            <div className="space-y-1.5">
                              <div className="flex items-center justify-between">
                                <span className="text-base font-black font-display text-foreground">
                                  {cand.overall_ats_score}
                                  <span className="text-[10px] text-muted-foreground font-normal">/100</span>
                                </span>
                                <span className={cn("px-2 py-0.5 rounded-md text-[9px] font-bold border", badge.colorClass)}>
                                  {cand.match_tier?.split('(')[0].trim() || badge.label}
                                </span>
                              </div>
                              <div className="w-full h-1.5 bg-accent rounded-full overflow-hidden">
                                <div
                                  className={cn("h-full rounded-full transition-all duration-500", badge.barColor)}
                                  style={{ width: `${cand.overall_ats_score}%` }}
                                />
                              </div>
                            </div>
                          )}
                        </td>

                        {/* Skills Match */}
                        <td className="py-4 px-4">
                          {isError ? (
                            <span className="text-muted-foreground text-[11px]">N/A</span>
                          ) : (
                            <div className="space-y-1">
                              <div className="flex items-center gap-1.5">
                                <span className="font-bold text-xs text-foreground">{Math.round(skillsPercent)}%</span>
                                <span className="text-[10px] text-muted-foreground">match</span>
                              </div>
                              <div className="flex flex-wrap gap-1 max-w-[170px]">
                                {cand.candidate.technical_skills.slice(0, 3).map((sk) => (
                                  <span key={sk} className="px-1.5 py-0.5 bg-accent/60 rounded text-[9px] font-medium text-muted-foreground">
                                    {sk}
                                  </span>
                                ))}
                                {cand.candidate.technical_skills.length > 3 && (
                                  <span className="text-[9px] text-muted-foreground">+{cand.candidate.technical_skills.length - 3}</span>
                                )}
                              </div>
                            </div>
                          )}
                        </td>

                        {/* Experience */}
                        <td className="py-4 px-4">
                          <div className="space-y-0.5">
                            <span className="font-bold text-xs text-foreground">
                              {cand.candidate.work_experience_years > 0
                                ? `${cand.candidate.work_experience_years} yrs`
                                : 'Fresher'}
                            </span>
                            <p className="text-[10px] text-muted-foreground truncate max-w-[100px]">
                              {cand.candidate.experience_entries[0]?.title || 'Profile'}
                            </p>
                          </div>
                        </td>

                        {/* Status / Recruiter Recommendation */}
                        <td className="py-4 px-4">
                          {isError ? (
                            <span className="text-[10px] text-red-400 font-medium truncate block max-w-[150px]">
                              {cand.extraction_error || 'Extraction Failed'}
                            </span>
                          ) : (
                            <span
                              className={cn(
                                "inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold border",
                                getRecommendationBadge(cand.recommendation?.verdict)
                              )}
                            >
                              <UserCheck className="w-3 h-3" />
                              {cand.recommendation?.verdict || 'Reviewed'}
                            </span>
                          )}
                        </td>

                        {/* Action */}
                        <td className="py-4 px-4 text-center">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedCandidate(cand);
                            }}
                            className="px-3 py-1.5 bg-primary/10 hover:bg-primary text-primary hover:text-primary-foreground border border-primary/30 rounded-xl text-xs font-bold transition-all shadow-sm"
                          >
                            View Report
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {filteredCandidates.length === 0 && (
              <div className="text-center py-12 text-muted-foreground space-y-2">
                <AlertCircle className="w-8 h-8 mx-auto opacity-40" />
                <p className="text-xs font-bold uppercase tracking-wider">No candidates match your active filters</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ─── Individual Candidate Detailed Report Modal ───────────────────────── */}
      {selectedCandidate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-card border border-border w-full max-w-4xl max-h-[90vh] rounded-3xl overflow-hidden flex flex-col shadow-2xl">
            {/* Modal Header */}
            <div className="p-6 border-b border-border flex items-start justify-between bg-accent/20">
              <div className="space-y-1">
                <div className="flex items-center gap-3">
                  <h3 className="text-2xl font-bold font-display text-foreground">{selectedCandidate.candidate.name}</h3>
                  {selectedCandidate.overall_ats_score !== null && (
                    <span
                      className={cn(
                        "px-3 py-1 rounded-full text-xs font-bold border",
                        getScoreBadge(selectedCandidate.overall_ats_score).colorClass
                      )}
                    >
                      {selectedCandidate.match_tier}
                    </span>
                  )}
                  {selectedCandidate.recommendation && (
                    <span
                      className={cn(
                        "px-3 py-1 rounded-full text-xs font-bold border",
                        getRecommendationBadge(selectedCandidate.recommendation.verdict)
                      )}
                    >
                      {selectedCandidate.recommendation.verdict}
                    </span>
                  )}
                </div>
                <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground pt-1">
                  {selectedCandidate.candidate.email && (
                    <span className="flex items-center gap-1">
                      <Mail className="w-3.5 h-3.5 text-primary" /> {selectedCandidate.candidate.email}
                    </span>
                  )}
                  {selectedCandidate.candidate.phone && (
                    <span className="flex items-center gap-1">
                      <Phone className="w-3.5 h-3.5 text-primary" /> {selectedCandidate.candidate.phone}
                    </span>
                  )}
                  {selectedCandidate.candidate.college && (
                    <span className="flex items-center gap-1">
                      <Building className="w-3.5 h-3.5 text-primary" /> {selectedCandidate.candidate.college}
                    </span>
                  )}
                  <span className="flex items-center gap-1">
                    <Briefcase className="w-3.5 h-3.5 text-primary" /> {selectedCandidate.candidate.work_experience_years} Years Experience
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => downloadCandidateReport(selectedCandidate)}
                  className="p-2 hover:bg-accent text-muted-foreground hover:text-foreground rounded-xl transition-all"
                  title="Download candidate report"
                >
                  <Download className="w-5 h-5 text-primary" />
                </button>
                <button
                  type="button"
                  onClick={() => setSelectedCandidate(null)}
                  className="p-2 hover:bg-accent text-muted-foreground hover:text-foreground rounded-xl transition-all"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-6">
              {/* Extraction Error Notice */}
              {selectedCandidate.status === 'ERROR' && (
                <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-2xl text-xs text-red-400 space-y-1">
                  <p className="font-bold flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4" /> Extraction Error Detected
                  </p>
                  <p>{selectedCandidate.extraction_error || 'Failed to extract text from document.'}</p>
                </div>
              )}

              {/* Overall ATS Score & Criteria Breakdown */}
              {selectedCandidate.breakdown && (
                <div className="bg-accent/20 border border-border/80 rounded-2xl p-5 space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
                        Overall ATS Compatibility Score
                      </p>
                      <p className="text-3xl font-black font-display text-primary mt-0.5">
                        {selectedCandidate.overall_ats_score}
                        <span className="text-sm font-normal text-muted-foreground">/100</span>
                      </p>
                    </div>
                    <p className="text-xs text-muted-foreground max-w-sm text-right italic">
                      Deterministic-plus-semantic weighted evaluation against target role:{' '}
                      <strong className="text-foreground">{lastScreenedRole || selectedRole}</strong>.
                    </p>
                  </div>

                  {/* 8 Criteria Progress Bars */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
                    <div>
                      <div className="flex justify-between text-[11px] font-bold mb-1">
                        <span>Technical Skills Match (30%)</span>
                        <span className="text-primary">{selectedCandidate.breakdown.technical_skills_score}%</span>
                      </div>
                      <div className="h-1.5 bg-accent rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary rounded-full"
                          style={{ width: `${selectedCandidate.breakdown.technical_skills_score}%` }}
                        />
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between text-[11px] font-bold mb-1">
                        <span>Job Description Relevance (20%)</span>
                        <span className="text-primary">{selectedCandidate.breakdown.jd_relevance_score}%</span>
                      </div>
                      <div className="h-1.5 bg-accent rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary rounded-full"
                          style={{ width: `${selectedCandidate.breakdown.jd_relevance_score}%` }}
                        />
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between text-[11px] font-bold mb-1">
                        <span>Relevant Experience (15%)</span>
                        <span className="text-primary">{selectedCandidate.breakdown.relevant_experience_score}%</span>
                      </div>
                      <div className="h-1.5 bg-accent rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary rounded-full"
                          style={{ width: `${selectedCandidate.breakdown.relevant_experience_score}%` }}
                        />
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between text-[11px] font-bold mb-1">
                        <span>Project Relevance (10%)</span>
                        <span className="text-primary">{selectedCandidate.breakdown.project_relevance_score}%</span>
                      </div>
                      <div className="h-1.5 bg-accent rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary rounded-full"
                          style={{ width: `${selectedCandidate.breakdown.project_relevance_score}%` }}
                        />
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between text-[11px] font-bold mb-1">
                        <span>Education Match (10%)</span>
                        <span className="text-primary">{selectedCandidate.breakdown.education_match_score}%</span>
                      </div>
                      <div className="h-1.5 bg-accent rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary rounded-full"
                          style={{ width: `${selectedCandidate.breakdown.education_match_score}%` }}
                        />
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between text-[11px] font-bold mb-1">
                        <span>Certifications (5%)</span>
                        <span className="text-primary">{selectedCandidate.breakdown.certifications_score}%</span>
                      </div>
                      <div className="h-1.5 bg-accent rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary rounded-full"
                          style={{ width: `${selectedCandidate.breakdown.certifications_score}%` }}
                        />
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between text-[11px] font-bold mb-1">
                        <span>Keywords Match (5%)</span>
                        <span className="text-primary">{selectedCandidate.breakdown.keywords_match_score}%</span>
                      </div>
                      <div className="h-1.5 bg-accent rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary rounded-full"
                          style={{ width: `${selectedCandidate.breakdown.keywords_match_score}%` }}
                        />
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between text-[11px] font-bold mb-1">
                        <span>Resume Quality (5%)</span>
                        <span className="text-primary">{selectedCandidate.breakdown.resume_quality_score}%</span>
                      </div>
                      <div className="h-1.5 bg-accent rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary rounded-full"
                          style={{ width: `${selectedCandidate.breakdown.resume_quality_score}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* AI-Powered Recruiter Recommendation */}
              {selectedCandidate.recommendation && (
                <div className="bg-card border border-border rounded-2xl p-5 space-y-2">
                  <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-primary">
                    <Bot className="w-4 h-4" /> Recruiter Recommendation
                  </div>
                  <p className="text-sm font-semibold text-foreground">{selectedCandidate.recommendation.reasoning}</p>
                  <p className="text-[11px] text-muted-foreground italic">
                    {selectedCandidate.recommendation.score_explanation}
                  </p>
                  <p className="text-[10px] text-muted-foreground/70 pt-1">
                    🔒 Anti-Bias Guarantee: Candidate evaluated strictly against job qualifications and skills without demographic inference.
                  </p>
                </div>
              )}

              {/* Skill Gap Analysis (6 Categories) */}
              {selectedCandidate.skill_gap_analysis && (
                <div className="space-y-4">
                  <h4 className="text-sm font-bold uppercase tracking-wider text-foreground flex items-center gap-2">
                    <Code className="w-4 h-4 text-primary" /> Skill Gap Analysis & Technology Mapping
                  </h4>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Matching Skills */}
                    <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-2xl p-4 space-y-2">
                      <p className="text-xs font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
                        <CheckCircle2 className="w-4 h-4" /> Matching Skills ({selectedCandidate.skill_gap_analysis.matching_skills.length})
                      </p>
                      {selectedCandidate.skill_gap_analysis.matching_skills.length > 0 ? (
                        <div className="space-y-1.5">
                          {selectedCandidate.skill_gap_analysis.matching_skills.map((item) => (
                            <div key={item.skill} className="text-xs bg-background/50 p-2 rounded-xl">
                              <span className="font-bold text-emerald-400">{item.skill}: </span>
                              <span className="text-muted-foreground text-[11px]">{item.reason}</span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-xs text-muted-foreground italic">No verified matching skills found.</p>
                      )}
                    </div>

                    {/* Missing Mandatory Skills */}
                    <div className="bg-red-500/5 border border-red-500/20 rounded-2xl p-4 space-y-2">
                      <p className="text-xs font-bold uppercase tracking-wider text-red-400 flex items-center gap-1.5">
                        <AlertCircle className="w-4 h-4" /> Missing Mandatory Skills ({selectedCandidate.skill_gap_analysis.missing_mandatory_skills.length})
                      </p>
                      {selectedCandidate.skill_gap_analysis.missing_mandatory_skills.length > 0 ? (
                        <div className="space-y-1.5">
                          {selectedCandidate.skill_gap_analysis.missing_mandatory_skills.map((item) => (
                            <div key={item.skill} className="text-xs bg-background/50 p-2 rounded-xl">
                              <span className="font-bold text-red-400">{item.skill}: </span>
                              <span className="text-muted-foreground text-[11px]">{item.reason}</span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-xs text-emerald-400 italic">All mandatory requirements satisfied!</p>
                      )}
                    </div>

                    {/* Missing Preferred Skills */}
                    <div className="bg-amber-500/5 border border-amber-500/20 rounded-2xl p-4 space-y-2">
                      <p className="text-xs font-bold uppercase tracking-wider text-amber-400 flex items-center gap-1.5">
                        <Info className="w-4 h-4" /> Missing Preferred Skills ({selectedCandidate.skill_gap_analysis.missing_preferred_skills.length})
                      </p>
                      {selectedCandidate.skill_gap_analysis.missing_preferred_skills.length > 0 ? (
                        <div className="space-y-1.5">
                          {selectedCandidate.skill_gap_analysis.missing_preferred_skills.map((item) => (
                            <div key={item.skill} className="text-xs bg-background/50 p-2 rounded-xl">
                              <span className="font-bold text-amber-400">{item.skill}: </span>
                              <span className="text-muted-foreground text-[11px]">{item.reason}</span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-xs text-muted-foreground italic">No preferred skills missing.</p>
                      )}
                    </div>

                    {/* Partially Matching Skills */}
                    <div className="bg-blue-500/5 border border-blue-500/20 rounded-2xl p-4 space-y-2">
                      <p className="text-xs font-bold uppercase tracking-wider text-blue-400 flex items-center gap-1.5">
                        <RotateCcw className="w-4 h-4" /> Partially Matching Skills ({selectedCandidate.skill_gap_analysis.partially_matching_skills.length})
                      </p>
                      {selectedCandidate.skill_gap_analysis.partially_matching_skills.length > 0 ? (
                        <div className="space-y-1.5">
                          {selectedCandidate.skill_gap_analysis.partially_matching_skills.map((item) => (
                            <div key={item.skill} className="text-xs bg-background/50 p-2 rounded-xl">
                              <span className="font-bold text-blue-400">{item.skill}: </span>
                              <span className="text-muted-foreground text-[11px]">{item.reason}</span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-xs text-muted-foreground italic">No partial matches noted.</p>
                      )}
                    </div>
                  </div>

                  {/* Additional Skills & Relevant Technologies */}
                  <div className="bg-card border border-border/80 rounded-2xl p-4 space-y-3">
                    {selectedCandidate.skill_gap_analysis.additional_skills.length > 0 && (
                      <div>
                        <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-1.5">
                          Candidate Additional Skills
                        </p>
                        <div className="flex flex-wrap gap-1.5">
                          {selectedCandidate.skill_gap_analysis.additional_skills.map((s) => (
                            <span key={s} className="px-2 py-0.5 bg-accent/60 rounded-lg text-xs font-medium text-foreground">
                              {s}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {selectedCandidate.skill_gap_analysis.relevant_technologies.length > 0 && (
                      <div>
                        <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-1.5">
                          Complementary Technologies Observed
                        </p>
                        <div className="flex flex-wrap gap-1.5">
                          {selectedCandidate.skill_gap_analysis.relevant_technologies.map((t) => (
                            <span key={t} className="px-2 py-0.5 bg-primary/10 text-primary border border-primary/20 rounded-lg text-xs font-medium">
                              {t}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Strengths & Weaknesses */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-card border border-border/80 rounded-2xl p-4 space-y-2">
                  <p className="text-xs font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4" /> Verified Candidate Strengths
                  </p>
                  <ul className="space-y-1.5 text-xs text-muted-foreground">
                    {selectedCandidate.strengths.map((str, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span className="text-emerald-400 font-bold">•</span>
                        <span>{str}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="bg-card border border-border/80 rounded-2xl p-4 space-y-2">
                  <p className="text-xs font-bold uppercase tracking-wider text-red-400 flex items-center gap-1.5">
                    <AlertCircle className="w-4 h-4" /> Critical Gaps & Weaknesses
                  </p>
                  <ul className="space-y-1.5 text-xs text-muted-foreground">
                    {selectedCandidate.weaknesses.map((w, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span className="text-red-400 font-bold">•</span>
                        <span>{w}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Actionable Improvements (XYZ formula rewrites) */}
              {selectedCandidate.actionable_improvements.length > 0 && (
                <div className="bg-card border border-border/80 rounded-2xl p-4 space-y-3">
                  <p className="text-xs font-bold uppercase tracking-wider text-primary flex items-center gap-1.5">
                    <TrendingUp className="w-4 h-4" /> Actionable Improvements & Targeted Rewrites
                  </p>
                  <div className="space-y-2">
                    {selectedCandidate.actionable_improvements.map((imp, idx) => (
                      <div key={idx} className="text-xs bg-accent/30 p-3 rounded-xl space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 bg-primary/20 text-primary rounded text-[10px] font-bold uppercase">
                            {imp.section}
                          </span>
                          <span className="font-semibold text-foreground">{imp.issue}</span>
                        </div>
                        <p className="text-muted-foreground text-[11px] pl-2 border-l-2 border-primary/40">
                          {imp.suggested_fix}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-border flex items-center justify-between bg-accent/20">
              <span className="text-xs text-muted-foreground">
                Document File: <strong>{selectedCandidate.file_name}</strong>
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => downloadCandidateReport(selectedCandidate)}
                  className="px-4 py-2 bg-accent hover:bg-accent/80 text-foreground rounded-xl text-xs font-bold transition-all"
                >
                  Download Report (.txt)
                </button>
                <button
                  type="button"
                  onClick={() => setSelectedCandidate(null)}
                  className="px-5 py-2 bg-primary text-primary-foreground rounded-xl text-xs font-bold shadow-md shadow-primary/20 hover:scale-105 active:scale-95 transition-all"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ─── Configurable Weights Modal ─────────────────────────────────────── */}
      {showWeightsModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-card border border-border w-full max-w-md rounded-3xl p-6 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h3 className="text-base font-bold font-display uppercase tracking-wide flex items-center gap-2 text-foreground">
                <Sliders className="w-4 h-4 text-primary" /> Evaluation Criteria Weights
              </h3>
              <button
                type="button"
                onClick={() => setShowWeightsModal(false)}
                className="p-1 text-muted-foreground hover:text-foreground rounded-lg"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-muted-foreground">
              Customize the relative importance of each ATS scoring criterion. Total is normalized to 100%.
            </p>

            <div className="space-y-3">
              {[
                { key: 'technical_skills', label: 'Technical Skills Match', defaultVal: 30 },
                { key: 'jd_relevance', label: 'Job Description Relevance', defaultVal: 20 },
                { key: 'relevant_experience', label: 'Relevant Experience', defaultVal: 15 },
                { key: 'project_relevance', label: 'Project Relevance', defaultVal: 10 },
                { key: 'education_match', label: 'Education Match', defaultVal: 10 },
                { key: 'certifications', label: 'Certifications', defaultVal: 5 },
                { key: 'keywords_match', label: 'Keywords Match', defaultVal: 5 },
                { key: 'resume_quality', label: 'Resume Quality', defaultVal: 5 },
              ].map(({ key, label }) => (
                <div key={key} className="space-y-1">
                  <div className="flex justify-between text-xs font-bold">
                    <span className="text-foreground">{label}</span>
                    <span className="text-primary font-mono">{(weights as any)[key]}%</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="50"
                    step="1"
                    value={(weights as any)[key]}
                    onChange={(e) =>
                      setWeights({
                        ...weights,
                        [key]: Number(e.target.value),
                      })
                    }
                    className="w-full accent-primary h-1.5 bg-accent rounded-lg cursor-pointer"
                  />
                </div>
              ))}
            </div>

            <div className="pt-2 flex items-center justify-between border-t border-border">
              <button
                type="button"
                onClick={() => setWeights(DEFAULT_WEIGHTS)}
                className="text-xs text-muted-foreground hover:text-primary transition-colors flex items-center gap-1 font-semibold"
              >
                <RotateCcw className="w-3.5 h-3.5" /> Reset to Default
              </button>
              <button
                type="button"
                onClick={() => setShowWeightsModal(false)}
                className="px-5 py-2 bg-primary text-primary-foreground rounded-xl text-xs font-bold shadow-md shadow-primary/20 hover:scale-105 active:scale-95 transition-all"
              >
                Apply Weights
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
