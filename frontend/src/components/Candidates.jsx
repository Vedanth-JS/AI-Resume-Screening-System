import React, { useEffect, useState, useMemo } from 'react';
import { Users, Search, Filter, Mail, ChevronRight, SlidersHorizontal, X, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { Link } from 'react-router-dom';
import { candidateService } from '../services/api';

const scoreColor = (score) => {
  if (score >= 70) return { text: 'text-emerald-400', bg: 'bg-emerald-500', badge: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' };
  if (score >= 40) return { text: 'text-amber-400', bg: 'bg-amber-500', badge: 'bg-amber-500/10 text-amber-400 border-amber-500/20' };
  return { text: 'text-red-400', bg: 'bg-red-500', badge: 'bg-red-500/10 text-red-400 border-red-500/20' };
};

const statusIcon = (score) => {
  if (score >= 70) return <TrendingUp className="w-3.5 h-3.5" />;
  if (score >= 40) return <Minus className="w-3.5 h-3.5" />;
  return <TrendingDown className="w-3.5 h-3.5" />;
};

export function Candidates() {
  const [candidates, setCandidates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [minScore, setMinScore] = useState(0);
  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    candidateService.getCandidates()
      .then(res => setCandidates(res.data || []))
      .catch(err => console.error('Candidates fetch error:', err))
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    return candidates.filter(c => {
      const matchSearch =
        c.name?.toLowerCase().includes(search.toLowerCase()) ||
        c.email?.toLowerCase().includes(search.toLowerCase()) ||
        c.job_title?.toLowerCase().includes(search.toLowerCase());
      const matchScore = (c.final_score ?? 0) >= minScore;
      return matchSearch && matchScore;
    });
  }, [candidates, search, minScore]);

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      {/* Header */}
      <header className="flex justify-between items-end">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <div className="w-1.5 h-1.5 rounded-full bg-purple-500 animate-pulse" />
            <p className="text-[10px] font-bold text-purple-500/80 uppercase tracking-widest">Talent Pool</p>
          </div>
          <h2 className="text-4xl font-bold text-gradient">Candidates</h2>
          {!loading && (
            <p className="text-slate-500 text-sm mt-1">{candidates.length} total screened applicants</p>
          )}
        </div>

        <div className="flex gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              placeholder="Search by name, email, or role..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="bg-white/[0.03] border border-white/10 rounded-xl pl-10 pr-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all w-72 placeholder:text-slate-600"
            />
            {search && (
              <button onClick={() => setSearch('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white transition-colors">
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
          <button
            onClick={() => setShowFilters(f => !f)}
            className={`p-2.5 border rounded-xl transition-all flex items-center gap-2 px-4 text-sm font-medium ${showFilters ? 'bg-blue-600/10 border-blue-500/30 text-blue-400' : 'bg-white/[0.03] border-white/10 text-slate-400 hover:bg-white/[0.05] hover:text-white'}`}
          >
            <SlidersHorizontal className="w-4 h-4" />
            Filters
          </button>
        </div>
      </header>

      {/* Filter Panel */}
      {showFilters && (
        <div className="glass rounded-2xl p-6 border border-white/5 animate-in fade-in slide-in-from-top-2 duration-300">
          <div className="flex items-center gap-8">
            <div className="flex-1">
              <label className="text-xs font-bold uppercase tracking-widest text-slate-500 mb-3 block">
                Minimum Match Score: <span className="text-blue-400">{minScore}%</span>
              </label>
              <input
                type="range"
                min={0}
                max={100}
                step={5}
                value={minScore}
                onChange={e => setMinScore(Number(e.target.value))}
                className="w-full accent-blue-500 cursor-pointer"
              />
              <div className="flex justify-between text-[10px] text-slate-600 mt-1 font-medium">
                <span>0%</span>
                <span>50%</span>
                <span>100%</span>
              </div>
            </div>
            <div className="flex gap-3">
              {[
                { label: 'All', value: 0 },
                { label: '40%+', value: 40 },
                { label: '70%+', value: 70 },
                { label: '90%+', value: 90 },
              ].map(preset => (
                <button
                  key={preset.label}
                  onClick={() => setMinScore(preset.value)}
                  className={`px-4 py-2 rounded-xl text-xs font-bold border transition-all ${minScore === preset.value ? 'bg-blue-600/20 border-blue-500/40 text-blue-400' : 'bg-white/5 border-white/10 text-slate-400 hover:border-white/20'}`}
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="glass-card !p-0 overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-white/5 bg-white/[0.02]">
              <th className="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-slate-500">Candidate</th>
              <th className="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-slate-500">Applied For</th>
              <th className="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-slate-500">Status</th>
              <th className="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-slate-500">Screened</th>
              <th className="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-slate-500 text-right">Match Score</th>
              <th className="px-6 py-4 w-10" />
            </tr>
          </thead>
          <tbody>
            {loading ? (
              [...Array(5)].map((_, i) => (
                <tr key={i} className="border-b border-white/5">
                  <td colSpan={6} className="px-6 py-4">
                    <div className="h-10 bg-white/[0.03] rounded-xl animate-pulse" />
                  </td>
                </tr>
              ))
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-24 text-center">
                  <Users className="w-12 h-12 text-slate-700 mx-auto mb-4" />
                  <p className="text-slate-500 font-medium">
                    {search || minScore > 0
                      ? 'No candidates match your filters.'
                      : 'No candidates screened yet. Upload a resume to get started.'}
                  </p>
                  {(search || minScore > 0) && (
                    <button
                      onClick={() => { setSearch(''); setMinScore(0); }}
                      className="mt-4 text-xs text-blue-400 hover:text-blue-300 transition-colors font-semibold"
                    >
                      Clear all filters
                    </button>
                  )}
                </td>
              </tr>
            ) : (
              filtered.map((cand, i) => {
                const colors = scoreColor(cand.final_score ?? 0);
                return (
                  <tr
                    key={cand.id}
                    className="border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors group animate-in fade-in"
                    style={{ animationDelay: `${i * 40}ms` }}
                  >
                    {/* Candidate */}
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-4">
                        <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-blue-500/20 to-purple-500/20 flex items-center justify-center border border-white/10 text-white font-bold text-sm flex-shrink-0">
                          {cand.name?.[0]?.toUpperCase() || '?'}
                        </div>
                        <div>
                          <div className="font-semibold text-slate-100 text-sm">{cand.name}</div>
                          <div className="text-xs text-slate-500 flex items-center gap-1.5 mt-0.5">
                            <Mail className="w-3 h-3" />
                            {cand.email}
                          </div>
                        </div>
                      </div>
                    </td>

                    {/* Applied For */}
                    <td className="px-6 py-4">
                      {cand.job_id ? (
                        <Link to={`/job/${cand.job_id}`} className="text-sm text-slate-300 hover:text-blue-400 transition-colors font-medium">
                          {cand.job_title || `Job #${cand.job_id}`}
                        </Link>
                      ) : (
                        <span className="text-slate-600 text-sm">—</span>
                      )}
                    </td>

                    {/* Status Badge */}
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wide border ${colors.badge}`}>
                        {statusIcon(cand.final_score ?? 0)}
                        {(cand.final_score ?? 0) >= 70 ? 'Shortlist' : (cand.final_score ?? 0) >= 40 ? 'Review' : 'Declined'}
                      </span>
                    </td>

                    {/* Date */}
                    <td className="px-6 py-4 text-xs text-slate-500 font-medium">
                      {new Date(cand.uploaded_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                    </td>

                    {/* Score */}
                    <td className="px-6 py-4 text-right">
                      {cand.final_score != null ? (
                        <div className="flex items-center justify-end gap-3">
                          <div className="w-24 h-1.5 bg-white/5 rounded-full overflow-hidden">
                            <div
                              className={`h-full ${colors.bg} transition-all duration-700`}
                              style={{ width: `${Math.min(cand.final_score, 100)}%` }}
                            />
                          </div>
                          <span className={`text-lg font-bold font-mono ${colors.text}`}>
                            {Math.round(cand.final_score)}%
                          </span>
                        </div>
                      ) : (
                        <span className="text-slate-600 text-sm">Pending</span>
                      )}
                    </td>

                    {/* Arrow */}
                    <td className="px-4 py-4">
                      {cand.job_id && (
                        <Link to={`/job/${cand.job_id}`} className="w-8 h-8 rounded-lg bg-white/5 border border-white/5 flex items-center justify-center group-hover:border-blue-500/20 group-hover:text-blue-400 text-slate-600 transition-all">
                          <ChevronRight className="w-4 h-4" />
                        </Link>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>

        {/* Table Footer */}
        {!loading && filtered.length > 0 && (
          <div className="px-6 py-4 border-t border-white/5 bg-white/[0.01] flex items-center justify-between">
            <p className="text-xs text-slate-600 font-medium">
              Showing <span className="text-slate-400 font-bold">{filtered.length}</span> of{' '}
              <span className="text-slate-400 font-bold">{candidates.length}</span> candidates
            </p>
            <div className="flex items-center gap-4 text-xs text-slate-600">
              <span>
                <span className="text-emerald-400 font-bold">{candidates.filter(c => (c.final_score ?? 0) >= 70).length}</span> shortlisted
              </span>
              <span>
                <span className="text-amber-400 font-bold">{candidates.filter(c => (c.final_score ?? 0) >= 40 && (c.final_score ?? 0) < 70).length}</span> in review
              </span>
              <span>
                <span className="text-red-400 font-bold">{candidates.filter(c => (c.final_score ?? 0) < 40).length}</span> declined
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
