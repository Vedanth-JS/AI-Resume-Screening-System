import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useParams, useNavigate } from 'react-router-dom';
import { Search, ChevronRight, XCircle, CheckCircle, Info, Filter, Download, ArrowUpRight, User } from 'lucide-react';
import { jobsApi } from '../api/client';

const ResultsPage = () => {
    const { jobId } = useParams();
    const navigate = useNavigate();
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState("");

    useEffect(() => {
        const fetchResults = async () => {
            try {
                const res = await jobsApi.getResults(jobId === 'latest' ? 1 : jobId);
                setResults(res.data);
            } catch (err) {
                console.error(err);
            } finally {
                setLoading(false);
            }
        };
        fetchResults();
        const interval = setInterval(fetchResults, 5000);
        return () => clearInterval(interval);
    }, [jobId]);

    const getStatusTheme = (status) => {
        if (status === 'accept') return { icon: <CheckCircle className="w-4 h-4" />, color: 'text-secondary', bg: 'bg-secondary/10', label: 'Highly Recommended' };
        if (status === 'reject') return { icon: <XCircle className="w-4 h-4" />, color: 'text-red-500', bg: 'bg-red-50', label: 'Not a Fit' };
        return { icon: <Info className="w-4 h-4" />, color: 'text-amber-500', bg: 'bg-amber-50', label: 'Potential Match' };
    };

    const filteredResults = results.filter(r => 
        r.candidate_name.toLowerCase().includes(search.toLowerCase()) ||
        r.matched_skills.some(s => s.toLowerCase().includes(search.toLowerCase()))
    );

    return (
        <div className="space-y-10">
            <header className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                <div>
                    <h2 className="text-4xl font-display font-bold text-slate-900 tracking-tight">Candidate <span className="text-primary">Rankings</span></h2>
                    <p className="text-lg text-slate-500 mt-2">Precision scoring based on multi-dimensional talent vectors.</p>
                </div>
                
                <div className="flex items-center gap-3">
                    <div className="relative group">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 group-focus-within:text-primary transition-colors" />
                        <input 
                            type="text" 
                            placeholder="Filter candidates..." 
                            className="bg-white/50 border border-slate-200 pl-11 pr-4 py-3 rounded-2xl outline-none focus:ring-4 focus:ring-primary/10 focus:border-primary transition-all w-64 text-sm font-medium"
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                        />
                    </div>
                    <button className="p-3 bg-white border border-slate-200 rounded-2xl hover:bg-slate-50 transition-colors text-slate-600">
                        <Filter className="w-5 h-5" />
                    </button>
                    <button className="btn-primary flex items-center">
                        <Download className="w-4 h-4 mr-2" /> Export Report
                    </button>
                </div>
            </header>

            {loading && results.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-32 space-y-4">
                    <div className="relative w-20 h-20">
                        <div className="absolute inset-0 border-4 border-primary/10 rounded-full"></div>
                        <div className="absolute inset-0 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
                    </div>
                    <p className="text-slate-500 font-medium animate-pulse">Running Neural Ranking Algorithms...</p>
                </div>
            ) : (
                <div className="grid gap-6">
                    <AnimatePresence mode="popLayout">
                        {filteredResults.map((r, i) => {
                            const theme = getStatusTheme(r.status);
                            return (
                                <motion.div 
                                    layout
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, scale: 0.95 }}
                                    transition={{ delay: i * 0.05 }}
                                    key={i} 
                                    className="card glass group hover:border-primary/30 transition-all cursor-pointer flex flex-col md:flex-row md:items-center gap-8 relative overflow-hidden"
                                >
                                    <div className="absolute top-0 right-0 w-32 h-32 bg-primary/5 rounded-full -mr-16 -mt-16 group-hover:scale-150 transition-transform duration-500" />
                                    
                                    <div className="relative">
                                        <div className="w-20 h-20 bg-gradient-to-br from-slate-50 to-slate-100 rounded-3xl flex items-center justify-center text-2xl font-display font-black text-primary border border-slate-200 shadow-sm group-hover:shadow-md transition-all group-hover:-rotate-3">
                                            {r.candidate_name[0]}
                                        </div>
                                        <div className="absolute -bottom-2 -right-2 w-8 h-8 bg-white rounded-xl shadow-lg border border-slate-100 flex items-center justify-center">
                                            <span className="text-[10px] font-black text-slate-400">#{i+1}</span>
                                        </div>
                                    </div>

                                    <div className="flex-1 space-y-4">
                                        <div className="flex items-center gap-3">
                                            <h4 className="text-xl font-display font-bold text-slate-800">{r.candidate_name}</h4>
                                            <span className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${theme.bg} ${theme.color}`}>
                                                {theme.icon}
                                                {theme.label}
                                            </span>
                                        </div>
                                        
                                        <div className="grid grid-cols-3 gap-6">
                                            <div className="space-y-1">
                                                <div className="flex items-center justify-between text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                                                    <span>Skills Match</span>
                                                    <span className="text-slate-600">{Math.round(r.skills_score * 100)}%</span>
                                                </div>
                                                <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                                                    <motion.div 
                                                        initial={{ width: 0 }}
                                                        animate={{ width: `${r.skills_score * 100}%` }}
                                                        className="h-full bg-secondary rounded-full" 
                                                    />
                                                </div>
                                            </div>
                                            <div className="space-y-1">
                                                <div className="flex items-center justify-between text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                                                    <span>Experience</span>
                                                    <span className="text-slate-600">{Math.round(r.experience_score * 100)}%</span>
                                                </div>
                                                <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                                                    <motion.div 
                                                        initial={{ width: 0 }}
                                                        animate={{ width: `${r.experience_score * 100}%` }}
                                                        className="h-full bg-primary-light rounded-full" 
                                                    />
                                                </div>
                                            </div>
                                            <div className="space-y-1">
                                                <div className="flex items-center justify-between text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                                                    <span>Semantic Fit</span>
                                                    <span className="text-slate-600">{Math.round(r.semantic_score * 100)}%</span>
                                                </div>
                                                <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                                                    <motion.div 
                                                        initial={{ width: 0 }}
                                                        animate={{ width: `${r.semantic_score * 100}%` }}
                                                        className="h-full bg-indigo-400 rounded-full" 
                                                    />
                                                </div>
                                            </div>
                                        </div>

                                        <div className="flex flex-wrap gap-2 pt-1">
                                            {r.matched_skills.slice(0, 5).map((s, si) => (
                                                <span key={si} className="px-2.5 py-1 bg-slate-50 border border-slate-100 text-slate-500 rounded-lg text-[10px] font-bold uppercase tracking-tight">
                                                    {s}
                                                </span>
                                            ))}
                                            {r.matched_skills.length > 5 && (
                                                <span className="px-2.5 py-1 bg-slate-50 border border-slate-100 text-slate-400 rounded-lg text-[10px] font-bold">
                                                    +{r.matched_skills.length - 5} MORE
                                                </span>
                                            )}
                                        </div>
                                    </div>

                                    <div className="md:w-32 flex flex-col items-center md:items-end justify-center border-l border-slate-100 md:pl-8">
                                        <div className="text-5xl font-display font-black text-slate-900 leading-none tracking-tighter">
                                            {Math.round(r.total_score * 100)}
                                        </div>
                                        <div className="mt-2 text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">Overall</div>
                                        <button className="mt-4 p-2 bg-slate-50 rounded-xl text-slate-400 group-hover:text-primary group-hover:bg-primary/10 transition-all">
                                            <ArrowUpRight className="w-4 h-4" />
                                        </button>
                                    </div>
                                </motion.div>
                            );
                        })}
                    </AnimatePresence>
                    
                    {results.length === 0 && (
                        <motion.div 
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            className="flex flex-col items-center justify-center py-32 bg-white/50 border border-dashed border-slate-200 rounded-[2rem]"
                        >
                            <div className="w-20 h-20 bg-slate-50 rounded-3xl flex items-center justify-center mb-6">
                                <User className="w-10 h-10 text-slate-300" />
                            </div>
                            <p className="text-slate-500 font-bold">Queueing candidate profiles...</p>
                            <p className="text-slate-400 text-sm mt-1 text-center max-w-xs">Return to the upload page to start a new intelligence screening session.</p>
                            <button 
                                onClick={() => navigate("/")}
                                className="mt-8 text-primary font-bold text-sm hover:underline"
                            >
                                ← Back to Upload
                            </button>
                        </motion.div>
                    )}
                </div>
            )}
        </div>
    );
};

export default ResultsPage;
