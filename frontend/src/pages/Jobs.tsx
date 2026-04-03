import React, { useMemo } from 'react';
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
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  Filter,
  Download,
  Trash2
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface Job {
  id: number;
  title: string;
  posted: string;
  applicants: number;
  avgScore: number;
  status: 'Active' | 'Draft' | 'Closed';
}

const mockJobs: Job[] = [
  { id: 1, title: 'Senior Software Engineer', posted: '2026-03-20', applicants: 45, avgScore: 78, status: 'Active' },
  { id: 2, title: 'Product Manager', posted: '2026-03-22', applicants: 12, avgScore: 65, status: 'Active' },
  { id: 3, title: 'UX Designer', posted: '2026-03-25', applicants: 8, avgScore: 82, status: 'Draft' },
  { id: 4, title: 'Backend Developer', posted: '2026-03-15', applicants: 92, avgScore: 71, status: 'Closed' },
];

const columnHelper = createColumnHelper<Job>();

export default function JobsPage() {
  const [sorting, setSorting] = React.useState<SortingState>([]);
  const data = useMemo(() => mockJobs, []);

  const columns = [
    columnHelper.accessor('title', {
      header: 'Job Title',
      cell: info => <span className="font-bold text-foreground">{info.getValue()}</span>,
    }),
    columnHelper.accessor('posted', {
      header: 'Posted Date',
      cell: info => <span className="text-muted-foreground text-sm">{info.getValue()}</span>,
    }),
    columnHelper.accessor('applicants', {
      header: ({ column }) => (
        <button className="flex items-center gap-1 hover:text-foreground transition-colors" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Applicants <ArrowUpDown className="w-3 h-3" />
        </button>
      ),
      cell: info => <span className="font-medium">{info.getValue()}</span>,
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
          "inline-flex items-center px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider",
          info.getValue() === 'Active' ? "bg-green-500/10 text-green-500" :
          info.getValue() === 'Draft' ? "bg-yellow-500/10 text-yellow-500" :
          "bg-muted text-muted-foreground"
        )}>
          {info.getValue()}
        </div>
      ),
    }),
    columnHelper.display({
      id: 'actions',
      cell: () => (
        <button className="p-2 hover:bg-accent rounded-full transition-colors">
          <MoreHorizontal className="w-4 h-4 text-muted-foreground" />
        </button>
      ),
    }),
  ];

  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold font-display tracking-tight">Jobs Management</h1>
          <p className="text-muted-foreground text-sm mt-1">Manage your active job postings and applicants.</p>
        </div>
        <div className="flex items-center gap-2">
          <button className="flex items-center gap-2 px-4 py-2 border rounded-lg text-sm font-medium hover:bg-accent transition-colors">
            <Download className="w-4 h-4" />
            Export CSV
          </button>
          <button className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:opacity-90 transition-opacity shadow-sm shadow-primary/20">
            <Plus className="w-4 h-4" />
            Post New Job
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {[
          { label: 'Active Jobs', value: '12', trend: '+2 this month', icon: Briefcase, color: 'text-blue-500' },
          { label: 'Total Applicants', value: '842', trend: '+156 this week', icon: Users, color: 'text-purple-500' },
          { label: 'Avg. Match Rate', value: '72%', trend: '+5% higher', icon: BarChart3, color: 'text-green-500' },
        ].map((stat, i) => (
          <div key={i} className="bg-card border rounded-2xl p-6 relative overflow-hidden group hover:border-primary/30 transition-all duration-300">
            <div className="flex justify-between items-start relative z-10">
              <div>
                <p className="text-muted-foreground text-xs font-bold uppercase tracking-wider">{stat.label}</p>
                <h3 className="text-3xl font-bold mt-1">{stat.value}</h3>
              </div>
              <div className={cn("p-2 rounded-xl bg-accent/50", stat.color)}>
                <stat.icon className="w-5 h-5" />
              </div>
            </div>
            <p className="text-[10px] text-muted-foreground mt-4 font-medium flex items-center gap-1 group-hover:text-foreground transition-colors">
              <span className="text-green-500">{stat.trend.split(' ')[0]}</span>
              {stat.trend.split(' ').slice(1).join(' ')}
            </p>
            <div className="absolute -right-4 -bottom-4 w-24 h-24 bg-accent/20 rounded-full blur-2xl group-hover:bg-primary/5 transition-colors duration-500" />
          </div>
        ))}
      </div>

      {/* Table Section */}
      <div className="bg-card border rounded-2xl overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b flex items-center justify-between bg-accent/5">
          <div className="flex items-center gap-4">
            <div className="relative group">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground group-focus-within:text-primary transition-colors" />
              <input 
                type="text" 
                placeholder="Filter jobs..." 
                className="bg-background/80 border rounded-full pl-9 pr-4 py-1.5 text-xs w-64 focus:ring-1 focus:ring-primary focus:border-primary outline-none transition-all"
              />
            </div>
            <button className="flex items-center gap-2 text-xs font-bold text-muted-foreground hover:text-foreground transition-all">
              <Filter className="w-3.5 h-3.5" />
              Advanced Filters
            </button>
          </div>
          <p className="text-[10px] uppercase font-bold tracking-widest text-muted-foreground">Showing 4 of 24 Jobs</p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              {table.getHeaderGroups().map(headerGroup => (
                <tr key={headerGroup.id} className="border-b bg-accent/30 font-display">
                  {headerGroup.headers.map(header => (
                    <th key={header.id} className="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                      {flexRender(header.column.columnDef.header, header.getContext())}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody className="divide-y">
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
        </div>

        {/* Pagination */}
        <div className="px-6 py-4 border-t flex items-center justify-between bg-accent/5">
          <p className="text-xs text-muted-foreground font-medium">Page 1 of 6</p>
          <div className="flex items-center gap-2">
            <button className="p-1.5 border rounded-lg hover:bg-accent disabled:opacity-30 disabled:hover:bg-transparent transition-all" disabled>
              <ChevronLeft className="w-4 h-4" />
            </button>
            {[1, 2, 3, '...', 6].map((p, i) => (
              <button 
                key={i} 
                className={cn(
                  "w-8 h-8 rounded-lg text-xs font-bold transition-all",
                  p === 1 ? "bg-primary text-primary-foreground shadow-lg shadow-primary/20" : "hover:bg-accent text-muted-foreground hover:text-foreground"
                )}
              >
                {p}
              </button>
            ))}
            <button className="p-1.5 border rounded-lg hover:bg-accent transition-all">
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function Plus({ className }: { className?: string }) {
  return <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>;
}
