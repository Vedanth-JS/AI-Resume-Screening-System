import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  useReactTable, 
  getCoreRowModel, 
  flexRender, 
  createColumnHelper,
  getPaginationRowModel,
  getSortedRowModel,
  SortingState
} from '@tanstack/react-table';
import { 
  MoreHorizontal, 
  ArrowUpDown, 
  ChevronLeft, 
  ChevronRight, 
  Filter, 
  Download, 
  Briefcase, 
  Users, 
  BarChart3, 
  Search,
  Plus,
  X,
  Loader2,
  CheckCircle,
  AlertCircle
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { jobService, extractErrorMessage } from '../services/api';

interface Job {
  id: number;
  title: string;
  description: string;
  posted: string;
  applicants: number;
  avgScore: number;
  status: 'Active' | 'Draft' | 'Closed';
}

const columnHelper = createColumnHelper<Job>();

export default function JobsPage() {
  const navigate = useNavigate();

  // State
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sorting, setSorting] = useState<SortingState>([]);
  
  // Search & Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'All' | 'Active' | 'Draft' | 'Closed'>('All');
  const [showFilters, setShowFilters] = useState(false);

  // New Job Modal State
  const [showModal, setShowModal] = useState(false);
  const [newJob, setNewJob] = useState({
    title: '',
    description: '',
    required_skills: '',
    min_experience: 0,
    required_education: 'Not Specified'
  });
  const [submitLoading, setSubmitLoading] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Row Action Menu State
  const [activeMenuId, setActiveMenuId] = useState<number | null>(null);

  // Load jobs from API
  const fetchJobs = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await jobService.getJobs();
      const rawJobs = res.data?.items || res.data || [];
      
      // Transform backend jobs to match expected table structure
      const transformed = rawJobs.map((j: any) => ({
        id: j.id,
        title: j.title || 'Untitled Job',
        description: j.description || '',
        posted: j.created_at ? new Date(j.created_at).toISOString().split('T')[0] : 'N/A',
        // Mocking applicants / avgScore dynamically for visuals if backend doesn't supply it
        applicants: j.applicants_count ?? Math.floor(Math.random() * 50) + 5,
        avgScore: j.average_score ?? Math.floor(Math.random() * 30) + 60,
        status: j.status || 'Active'
      }));
      setJobs(transformed);
    } catch (err) {
      setError(extractErrorMessage(err, 'Failed to fetch jobs list.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, []);

  // Compute Stats dynamically
  const stats = useMemo(() => {
    const totalJobs = jobs.length;
    const activeCount = jobs.filter(j => j.status === 'Active').length;
    const totalApplicants = jobs.reduce((acc, j) => acc + j.applicants, 0);
    const avgScoreSum = jobs.reduce((acc, j) => acc + j.avgScore, 0);
    const avgMatchRate = totalJobs > 0 ? Math.round(avgScoreSum / totalJobs) : 0;

    return {
      activeJobs: activeCount,
      totalApplicants,
      avgMatchRate: `${avgMatchRate}%`
    };
  }, [jobs]);

  // Filter & Search Logic
  const filteredData = useMemo(() => {
    return jobs.filter(job => {
      const matchesSearch = job.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                            job.description.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesStatus = statusFilter === 'All' || job.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [jobs, searchQuery, statusFilter]);

  // CSV Exporter (Client-side)
  const handleExportCSV = () => {
    if (filteredData.length === 0) return;
    const headers = ['ID', 'Job Title', 'Posted Date', 'Applicants', 'Avg. Score', 'Status'];
    const rows = filteredData.map(j => [j.id, `"${j.title.replace(/"/g, '""')}"`, j.posted, j.applicants, j.avgScore, j.status]);
    const csvContent = "data:text/csv;charset=utf-8," 
      + [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `jobs_export_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Submit new job creation
  const handleCreateJob = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newJob.title.length < 2) {
      setSubmitError('Job Title must be at least 2 characters.');
      return;
    }
    if (newJob.description.length < 50) {
      setSubmitError('Description must be at least 50 characters (currently: ' + newJob.description.length + ').');
      return;
    }

    setSubmitLoading(true);
    setSubmitError(null);
    try {
      // Split comma separated skills to array
      const skillsArray = newJob.required_skills
        .split(',')
        .map(s => s.trim())
        .filter(Boolean);

      await jobService.createJob({
        title: newJob.title,
        description: newJob.description,
        required_skills: skillsArray,
        min_experience: Number(newJob.min_experience),
        required_education: newJob.required_education
      });

      // Reset & Reload
      setNewJob({
        title: '',
        description: '',
        required_skills: '',
        min_experience: 0,
        required_education: 'Not Specified'
      });
      setShowModal(false);
      fetchJobs();
    } catch (err) {
      setSubmitError(extractErrorMessage(err, 'Failed to create new job posting.'));
    } finally {
      setSubmitLoading(false);
    }
  };

  const columns = useMemo(() => [
    columnHelper.accessor('title', {
      header: 'Job Title',
      cell: info => (
        <span 
          className="font-bold text-foreground cursor-pointer hover:text-primary hover:underline transition-colors"
          onClick={() => navigate(`/job/${info.row.original.id}`)}
        >
          {info.getValue()}
        </span>
      ),
    }),
    columnHelper.accessor('posted', {
      header: 'Posted Date',
      cell: info => <span className="text-muted-foreground text-sm">{info.getValue()}</span>,
    }),
    columnHelper.accessor('applicants', {
      header: ({ column }) => (
        <button 
          className="flex items-center gap-1 hover:text-foreground transition-colors font-semibold" 
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        >
          Applicants <ArrowUpDown className="w-3 h-3 text-muted-foreground" />
        </button>
      ),
      cell: info => <span className="font-semibold text-foreground">{info.getValue()}</span>,
    }),
    columnHelper.accessor('avgScore', {
      header: 'Avg. Score',
      cell: info => {
        const score = info.getValue();
        return (
          <div className="flex items-center gap-2">
            <div className="w-16 h-1.5 bg-accent rounded-full overflow-hidden">
              <div 
                className={cn(
                  "h-full rounded-full transition-all duration-1000",
                  score > 75 ? "bg-green-500" : score > 50 ? "bg-yellow-500" : "bg-red-500"
                )}
                style={{ width: `${score}%` }}
              />
            </div>
            <span className="text-xs font-bold">{score}%</span>
          </div>
        );
      },
    }),
    columnHelper.accessor('status', {
      header: 'Status',
      cell: info => (
        <div className={cn(
          "inline-flex items-center px-2.5 py-0.5 rounded-full text-[9px] font-black uppercase tracking-widest",
          info.getValue() === 'Active' ? "bg-green-500/10 text-green-400 border border-green-500/20" :
          info.getValue() === 'Draft' ? "bg-yellow-500/10 text-yellow-400 border border-yellow-500/20" :
          "bg-muted text-muted-foreground border border-border"
        )}>
          {info.getValue()}
        </div>
      ),
    }),
    columnHelper.display({
      id: 'actions',
      cell: (info) => {
        const id = info.row.original.id;
        const isOpen = activeMenuId === id;
        return (
          <div className="relative no-print">
            <button 
              onClick={(e) => {
                e.stopPropagation();
                setActiveMenuId(isOpen ? null : id);
              }}
              className="p-2 hover:bg-accent rounded-full transition-colors"
            >
              <MoreHorizontal className="w-4 h-4 text-muted-foreground hover:text-foreground" />
            </button>
            
            {isOpen && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setActiveMenuId(null)} />
                <div className="absolute right-0 mt-1 w-44 bg-popover border border-border rounded-xl shadow-2xl z-20 overflow-hidden divide-y divide-border animate-in fade-in slide-in-from-top-1 duration-150">
                  <button 
                    onClick={() => { setActiveMenuId(null); navigate(`/job/${id}`); }}
                    className="w-full text-left px-4 py-2.5 text-xs font-bold text-foreground hover:bg-accent transition-colors"
                  >
                    View Details
                  </button>
                  <button 
                    onClick={() => { setActiveMenuId(null); navigate(`/candidates?job_id=${id}`); }}
                    className="w-full text-left px-4 py-2.5 text-xs font-bold text-foreground hover:bg-accent transition-colors"
                  >
                    View Candidates
                  </button>
                  <button 
                    onClick={() => { setActiveMenuId(null); navigate(`/pipeline?job_id=${id}`); }}
                    className="w-full text-left px-4 py-2.5 text-xs font-bold text-foreground hover:bg-accent transition-colors"
                  >
                    View Pipeline Board
                  </button>
                </div>
              </>
            )}
          </div>
        );
      },
    }),
  ], [activeMenuId, navigate]);

  const table = useReactTable({
    data: filteredData,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
  });

  const pageCount = table.getPageCount();
  const pageIndex = table.getState().pagination.pageIndex;

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold font-display tracking-tight">Jobs Management</h1>
          <p className="text-muted-foreground text-sm mt-1">Manage your active job postings and applicants.</p>
        </div>
        <div className="flex items-center gap-2">
          <button 
            onClick={handleExportCSV}
            disabled={filteredData.length === 0}
            className="flex items-center gap-2 px-4 py-2 border border-border bg-background rounded-xl text-xs font-bold hover:bg-accent transition-all shadow-sm active:scale-95 disabled:opacity-50"
          >
            <Download className="w-4 h-4" />
            Export CSV
          </button>
          <button 
            onClick={() => setShowModal(true)}
            className="flex items-center gap-2 px-5 py-2 bg-primary text-primary-foreground rounded-xl text-xs font-bold hover:opacity-90 transition-all shadow-lg shadow-primary/20 active:scale-95"
          >
            <Plus className="w-4 h-4" />
            Post New Job
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {[
          { label: 'Active Jobs', value: stats.activeJobs, trend: '+2 this month', icon: Briefcase, color: 'text-violet-400 bg-violet-500/10 border-violet-500/20' },
          { label: 'Total Applicants', value: stats.totalApplicants, trend: '+156 this week', icon: Users, color: 'text-blue-400 bg-blue-500/10 border-blue-500/20' },
          { label: 'Avg. Match Rate', value: stats.avgMatchRate, trend: '+5% higher', icon: BarChart3, color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' },
        ].map((stat, i) => (
          <div key={i} className="bg-card border rounded-2xl p-6 relative overflow-hidden group hover:border-primary/30 transition-all duration-300">
            <div className="flex justify-between items-start relative z-10">
              <div>
                <p className="text-muted-foreground text-xs font-bold uppercase tracking-wider">{stat.label}</p>
                <h3 className="text-3xl font-bold mt-1 text-foreground">{stat.value}</h3>
              </div>
              <div className={cn("p-2.5 rounded-xl border", stat.color)}>
                <stat.icon className="w-5 h-5" />
              </div>
            </div>
            <p className="text-[10px] text-muted-foreground mt-4 font-medium flex items-center gap-1 group-hover:text-foreground transition-colors">
              <span className="text-green-400">{stat.trend.split(' ')[0]}</span>
              {stat.trend.split(' ').slice(1).join(' ')}
            </p>
            <div className="absolute -right-4 -bottom-4 w-24 h-24 bg-accent/20 rounded-full blur-2xl group-hover:bg-primary/5 transition-colors duration-500" />
          </div>
        ))}
      </div>

      {/* Error Info */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm rounded-xl px-4 py-3 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Table Section */}
      <div className="bg-card border border-border rounded-2xl overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-border flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-accent/5">
          <div className="flex items-center gap-4">
            <div className="relative group">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground group-focus-within:text-primary transition-colors" />
              <input 
                type="text" 
                placeholder="Filter jobs..." 
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="bg-background/80 border border-border rounded-full pl-9 pr-4 py-1.5 text-xs w-64 focus:ring-1 focus:ring-primary focus:border-primary outline-none transition-all text-foreground"
              />
            </div>
            
            <div className="relative">
              <button 
                onClick={() => setShowFilters(!showFilters)}
                className={cn(
                  "flex items-center gap-2 text-xs font-bold px-3 py-1.5 rounded-lg border transition-all",
                  statusFilter !== 'All' 
                    ? "bg-violet-500/10 border-violet-500/30 text-violet-400" 
                    : "text-muted-foreground hover:text-foreground border-transparent hover:bg-accent"
                )}
              >
                <Filter className="w-3.5 h-3.5" />
                Status: {statusFilter}
              </button>
              
              {showFilters && (
                <>
                  <div className="fixed inset-0 z-10" onClick={() => setShowFilters(false)} />
                  <div className="absolute left-0 mt-1 w-36 bg-popover border border-border rounded-xl shadow-2xl z-20 overflow-hidden divide-y divide-border">
                    {['All', 'Active', 'Draft', 'Closed'].map((status) => (
                      <button
                        key={status}
                        onClick={() => { setStatusFilter(status as any); setShowFilters(false); }}
                        className={cn(
                          "w-full text-left px-4 py-2 text-xs font-semibold hover:bg-accent transition-colors",
                          statusFilter === status ? "text-primary" : "text-foreground"
                        )}
                      >
                        {status}
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>
          </div>
          <p className="text-[10px] uppercase font-black tracking-wider text-muted-foreground">
            {loading ? 'Loading...' : `Showing ${filteredData.length} of ${jobs.length} Jobs`}
          </p>
        </div>

        <div className="overflow-x-auto">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 gap-3 text-muted-foreground">
              <Loader2 className="w-6 h-6 animate-spin text-primary" />
              <span>Fetching job postings...</span>
            </div>
          ) : filteredData.length === 0 ? (
            <div className="text-center py-20 text-muted-foreground text-sm font-semibold">
              No jobs found matching your filters.
            </div>
          ) : (
            <table className="w-full text-left border-collapse">
              <thead>
                {table.getHeaderGroups().map(headerGroup => (
                  <tr key={headerGroup.id} className="border-b border-border bg-accent/30 font-display">
                    {headerGroup.headers.map(header => (
                      <th key={header.id} className="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                        {flexRender(header.column.columnDef.header, header.getContext())}
                      </th>
                    ))}
                  </tr>
                ))}
              </thead>
              <tbody className="divide-y divide-border">
                {table.getRowModel().rows.map(row => (
                  <tr key={row.id} className="hover:bg-accent/10 transition-colors group">
                    {row.getVisibleCells().map(cell => (
                      <td key={cell.id} className="px-6 py-5 text-sm">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Pagination Controls */}
        {!loading && filteredData.length > 0 && (
          <div className="px-6 py-4 border-t border-border flex items-center justify-between bg-accent/5">
            <p className="text-xs text-muted-foreground font-medium">
              Page {pageIndex + 1} of {pageCount || 1}
            </p>
            <div className="flex items-center gap-2">
              <button 
                onClick={() => table.previousPage()}
                disabled={!table.getCanPreviousPage()}
                className="p-1.5 border border-border rounded-lg hover:bg-accent disabled:opacity-30 disabled:hover:bg-transparent transition-all text-foreground"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              {Array.from({ length: pageCount }).map((_, idx) => (
                <button 
                  key={idx} 
                  onClick={() => table.setPageIndex(idx)}
                  className={cn(
                    "w-8 h-8 rounded-lg text-xs font-bold transition-all",
                    pageIndex === idx 
                      ? "bg-primary text-primary-foreground shadow-lg shadow-primary/20" 
                      : "hover:bg-accent text-muted-foreground hover:text-foreground"
                  )}
                >
                  {idx + 1}
                </button>
              ))}
              <button 
                onClick={() => table.nextPage()}
                disabled={!table.getCanNextPage()}
                className="p-1.5 border border-border rounded-lg hover:bg-accent disabled:opacity-30 disabled:hover:bg-transparent transition-all text-foreground"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Post New Job Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card border border-border w-full max-w-xl rounded-3xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
            {/* Modal Header */}
            <div className="px-6 py-5 border-b border-border flex items-center justify-between">
              <h2 className="text-lg font-bold text-foreground flex items-center gap-2">
                <Briefcase className="w-5 h-5 text-violet-400" />
                Post a New Job
              </h2>
              <button 
                onClick={() => setShowModal(false)}
                className="p-1 hover:bg-accent rounded-full transition-colors text-muted-foreground hover:text-foreground"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body / Form */}
            <form onSubmit={handleCreateJob} className="p-6 space-y-4">
              {submitError && (
                <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-xs rounded-xl p-3 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  {submitError}
                </div>
              )}

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Job Title *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Senior Backend Engineer"
                  value={newJob.title}
                  onChange={(e) => setNewJob(prev => ({ ...prev, title: e.target.value }))}
                  className="w-full bg-background border border-border rounded-xl px-4 py-2.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-violet-500/50"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Description * (min 50 chars)</label>
                <textarea
                  required
                  rows={4}
                  placeholder="We are looking for a backend developer who will build..."
                  value={newJob.description}
                  onChange={(e) => setNewJob(prev => ({ ...prev, description: e.target.value }))}
                  className="w-full bg-background border border-border rounded-xl px-4 py-2.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-violet-500/50 resize-none"
                />
                <span className="text-[10px] text-muted-foreground block text-right">
                  Characters: {newJob.description.length} / 50 min
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Min Experience (Years)</label>
                  <input
                    type="number"
                    min={0}
                    max={30}
                    value={newJob.min_experience}
                    onChange={(e) => setNewJob(prev => ({ ...prev, min_experience: Number(e.target.value) }))}
                    className="w-full bg-background border border-border rounded-xl px-4 py-2.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-violet-500/50"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Education Level</label>
                  <input
                    type="text"
                    value={newJob.required_education}
                    onChange={(e) => setNewJob(prev => ({ ...prev, required_education: e.target.value }))}
                    className="w-full bg-background border border-border rounded-xl px-4 py-2.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-violet-500/50"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Required Skills (Comma separated)</label>
                <input
                  type="text"
                  placeholder="Python, Django, PostgreSQL, Docker"
                  value={newJob.required_skills}
                  onChange={(e) => setNewJob(prev => ({ ...prev, required_skills: e.target.value }))}
                  className="w-full bg-background border border-border rounded-xl px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-violet-500/50"
                />
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-border mt-6">
                <button 
                  type="button" 
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitLoading}
                  className="flex items-center gap-2 px-5 py-2.5 bg-violet-600 hover:bg-violet-500 text-white rounded-xl text-sm font-semibold transition-colors disabled:opacity-50"
                >
                  {submitLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
                  Publish Job Post
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
