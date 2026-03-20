import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Bar, Pie } from 'react-chartjs-2';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    BarElement,
    Title,
    Tooltip,
    Legend,
    ArcElement,
    Filler
} from 'chart.js';
import { BarChart3, PieChart as PieChartIcon, TrendingUp, Users, Target, Award } from 'lucide-react';
import { jobsApi } from '../api/client';

ChartJS.register(
    CategoryScale,
    LinearScale,
    BarElement,
    Title,
    Tooltip,
    Legend,
    ArcElement,
    Filler
);

const AnalyticsPage = () => {
    const [analytics, setAnalytics] = useState(null);

    useEffect(() => {
        const fetchAnalytics = async () => {
            try {
                const res = await jobsApi.getAnalytics(1);
                setAnalytics(res.data);
            } catch (err) {
                console.error(err);
            }
        };
        fetchAnalytics();
    }, []);

    if (!analytics) return (
        <div className="flex items-center justify-center h-full">
            <div className="animate-pulse text-slate-400 font-display font-medium">Synthesizing Analytics...</div>
        </div>
    );

    const funnelData = {
        labels: Object.keys(analytics.funnel).map(s => s.toUpperCase()),
        datasets: [{
            label: 'Candidate Distribution',
            data: Object.values(analytics.funnel),
            backgroundColor: [
                '#10b981', // Accept
                '#f59e0b', // Manual
                '#ef4444', // Reject
            ],
            hoverOffset: 15,
            borderWidth: 8,
            borderColor: '#ffffff',
        }]
    };

    const skillGapData = {
        labels: ['Python', 'SQL', 'React', 'FastAPI', 'Docker', 'NLP'],
        datasets: [{
            label: 'Talent Density',
            data: [92, 78, 85, 64, 42, 71],
            backgroundColor: 'rgba(99, 102, 241, 0.8)',
            borderRadius: 12,
            hoverBackgroundColor: '#6366f1',
        }]
    };

    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: false
            },
            tooltip: {
                backgroundColor: '#1e293b',
                padding: 12,
                titleFont: { size: 14, weight: 'bold' },
                bodyFont: { size: 13 },
                cornerRadius: 12,
                displayColors: false
            }
        },
        scales: {
            y: {
                grid: { display: false },
                ticks: { display: false },
                border: { display: false }
            },
            x: {
                grid: { display: false },
                ticks: { font: { size: 11, weight: '600' }, color: '#94a3b8' },
                border: { display: false }
            }
        }
    };

    return (
        <div className="space-y-12 pb-12">
            <header>
                <h2 className="text-4xl font-display font-bold text-slate-900 tracking-tight">Intelligence <span className="text-primary">Insights</span></h2>
                <p className="text-lg text-slate-500 mt-2 leading-relaxed">Leverage data-driven metrics to optimize your talent acquisition funnel.</p>
            </header>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="card glass border-l-4 border-l-primary p-8">
                    <div className="flex items-center justify-between mb-4">
                        <Users className="w-5 h-5 text-slate-400" />
                        <span className="text-[10px] font-bold text-emerald-500 bg-emerald-50 px-2 py-0.5 rounded-full">+12%</span>
                    </div>
                    <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">Total Screened</p>
                    <h3 className="text-4xl font-display font-black text-slate-900">{analytics.count}</h3>
                </motion.div>
                
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="card glass border-l-4 border-l-secondary p-8">
                    <div className="flex items-center justify-between mb-4">
                        <Award className="w-5 h-5 text-slate-400" />
                        <span className="text-[10px] font-bold text-emerald-500 bg-emerald-50 px-2 py-0.5 rounded-full">Top 5%</span>
                    </div>
                    <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">Average QA</p>
                    <h3 className="text-4xl font-display font-black text-slate-900">{analytics.average_score}%</h3>
                </motion.div>

                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="card glass border-l-4 border-l-accent p-8">
                    <div className="flex items-center justify-between mb-4">
                        <Target className="w-5 h-5 text-slate-400" />
                        <span className="text-[10px] font-bold text-amber-500 bg-amber-50 px-2 py-0.5 rounded-full">Optimal</span>
                    </div>
                    <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">Conversion</p>
                    <h3 className="text-4xl font-display font-black text-slate-900">
                        {Math.round((analytics.funnel.accept / analytics.count) * 100)}%
                    </h3>
                </motion.div>

                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }} className="card glass border-l-4 border-l-slate-400 p-8">
                    <div className="flex items-center justify-between mb-4">
                        <BarChart3 className="w-5 h-5 text-slate-400" />
                    </div>
                    <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">Active Roles</p>
                    <h3 className="text-4xl font-display font-black text-slate-900">08</h3>
                </motion.div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                <div className="lg:col-span-4 card glass p-8">
                    <div className="flex items-center justify-between mb-8">
                        <h4 className="text-xl font-display font-bold text-slate-800">Pipeline Status</h4>
                        <PieChartIcon className="w-5 h-5 text-slate-300" />
                    </div>
                    <div className="h-64 relative flex items-center justify-center">
                        <Pie data={funnelData} options={{ maintainAspectRatio: false, plugins: { legend: { display: false } } }} />
                        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                            <span className="text-2xl font-black text-slate-800">{analytics.count}</span>
                            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Total</span>
                        </div>
                    </div>
                    <div className="mt-8 space-y-3">
                        {Object.entries(analytics.funnel).map(([key, val], idx) => (
                            <div key={idx} className="flex items-center justify-between">
                                <div className="flex items-center">
                                    <div className={`w-2.5 h-2.5 rounded-full mr-3 ${key === 'accept' ? 'bg-secondary' : key === 'reject' ? 'bg-red-500' : 'bg-accent'}`} />
                                    <span className="text-sm font-bold text-slate-600 capitalize">{key}</span>
                                </div>
                                <span className="text-sm font-black text-slate-800">{val}</span>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="lg:col-span-8 card glass p-8">
                    <div className="flex items-center justify-between mb-8">
                        <div>
                            <h4 className="text-xl font-display font-bold text-slate-800">Skill Proficiency Density</h4>
                            <p className="text-sm text-slate-400 mt-1">Aggregate competency across all evaluated candidates.</p>
                        </div>
                        <BarChart3 className="w-5 h-5 text-slate-300" />
                    </div>
                    <div className="h-80">
                        <Bar data={skillGapData} options={chartOptions} />
                    </div>
                    <div className="mt-8 p-6 bg-primary/5 rounded-2xl border border-primary/10">
                        <div className="flex items-start">
                            <div className="p-2 bg-white rounded-xl shadow-sm border border-primary/10 mr-4">
                                <Sparkles className="w-4 h-4 text-primary" />
                            </div>
                            <div>
                                <h5 className="text-sm font-bold text-slate-800">System Recommendation</h5>
                                <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                                    Current candidate pool shows high proficiency in **Python** but a significant gap in **Docker** infrastructure skills. Consider adjusting job descriptions to prioritize containerization experience.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default AnalyticsPage;
