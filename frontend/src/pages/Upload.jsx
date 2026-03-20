import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Upload, AlertCircle, CheckCircle, Brain, Sparkles, Files } from 'lucide-react';
import { jobsApi } from '../api/client';

const UploadPage = () => {
    const [jobData, setJobData] = useState({
        title: '',
        description: '',
        skills: '["Python", "React", "Docker"]',
        min_exp: 2,
        edu: 'Bachelor'
    });
    const [resumes, setResumes] = useState([]);
    const [loading, setLoading] = useState(false);
    const [biasInfo, setBiasInfo] = useState(null);
    const navigate = useNavigate();

    const handleUpload = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            const formData = new FormData();
            formData.append('title', jobData.title);
            formData.append('description', jobData.description);
            formData.append('skills', jobData.skills);
            formData.append('min_exp', jobData.min_exp);
            formData.append('edu', jobData.edu);

            const jobRes = await jobsApi.create(formData);
            setBiasInfo(jobRes.data);

            const screenData = new FormData();
            screenData.append('job_id', jobRes.data.job_id);
            resumes.forEach(file => {
                screenData.append('resumes', file);
            });

            await jobsApi.screen(screenData);
            
            setTimeout(() => {
                navigate(`/results/${jobRes.data.job_id}`);
            }, 2000);

        } catch (err) {
            console.error(err);
            alert("Upload failed. Check console.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-10">
            <header>
                <h2 className="text-5xl font-display font-bold text-slate-900 mb-4 tracking-tight">
                    Smart Candidate <span className="text-primary">Discovery</span>
                </h2>
                <p className="text-xl text-slate-500 max-w-2xl leading-relaxed">
                    Upload your job requirements and candidate resumes. Our system will rank them based on technical fit, experience, and potential.
                </p>
            </header>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
                <section className="lg:col-span-7 space-y-8">
                    <div className="card glass relative overflow-hidden group">
                        <div className="absolute top-0 right-0 p-8 opacity-5 group-hover:opacity-10 transition-opacity">
                            <Brain className="w-32 h-32" />
                        </div>
                        <h3 className="text-2xl font-display font-bold mb-6 flex items-center text-slate-800">
                            Requirement Definition
                        </h3>
                        <div className="space-y-6">
                            <div className="relative">
                                <label className="text-xs font-bold text-slate-400 uppercase mb-2 block ml-1">Job Title</label>
                                <input 
                                    type="text" placeholder="e.g. Senior Full Stack Engineer" 
                                    className="w-full px-4 py-4 bg-slate-50 border border-slate-200 rounded-2xl focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all outline-none text-slate-700 font-medium"
                                    value={jobData.title} onChange={e => setJobData({...jobData, title: e.target.value})}
                                />
                            </div>
                            <div className="relative">
                                <label className="text-xs font-bold text-slate-400 uppercase mb-2 block ml-1">Job Description</label>
                                <textarea 
                                    placeholder="Paste the full job description here..." 
                                    className="w-full h-56 px-4 py-4 bg-slate-50 border border-slate-200 rounded-2xl focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all outline-none text-slate-700 font-medium resize-none"
                                    value={jobData.description} onChange={e => setJobData({...jobData, description: e.target.value})}
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-6">
                                <div>
                                    <label className="text-xs font-bold text-slate-400 uppercase mb-2 block ml-1">Exp (Years)</label>
                                    <input 
                                        type="number" 
                                        className="w-full px-4 py-4 bg-slate-50 border border-slate-200 rounded-2xl focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all outline-none text-slate-700 font-medium"
                                        value={jobData.min_exp} onChange={e => setJobData({...jobData, min_exp: e.target.value})}
                                    />
                                </div>
                                <div>
                                    <label className="text-xs font-bold text-slate-400 uppercase mb-2 block ml-1">Education</label>
                                    <select 
                                        className="w-full px-4 py-4 bg-slate-50 border border-slate-200 rounded-2xl focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all outline-none text-slate-700 font-medium appearance-none"
                                        value={jobData.edu} onChange={e => setJobData({...jobData, edu: e.target.value})}
                                    >
                                        <option>Bachelor</option>
                                        <option>Master</option>
                                        <option>PhD</option>
                                    </select>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                <section className="lg:col-span-5 space-y-8">
                    <div className="card glass">
                        <h3 className="text-2xl font-display font-bold mb-6 flex items-center text-slate-800">
                            Candidates
                        </h3>
                        <div 
                            className="border-2 border-dashed border-slate-200 rounded-3xl p-10 text-center bg-slate-50/50 hover:bg-slate-50 hover:border-primary/50 transition-all cursor-pointer group"
                            onClick={() => document.getElementById('file-upload').click()}
                        >
                            <div className="w-20 h-20 bg-white rounded-2xl shadow-sm border border-slate-100 flex items-center justify-center mx-auto mb-6 group-hover:scale-110 transition-transform">
                                <Files className="w-10 h-10 text-primary" />
                            </div>
                            <p className="text-slate-800 font-bold mb-2">Drop resumes here</p>
                            <p className="text-slate-400 text-sm">Accepts PDF and DOCX files</p>
                            <input 
                                id="file-upload" type="file" multiple className="hidden" 
                                onChange={e => setResumes(Array.from(e.target.files))}
                            />
                        </div>

                        {resumes.length > 0 && (
                            <div className="mt-8 space-y-3 max-h-48 overflow-y-auto pr-2 custom-scrollbar">
                                {resumes.map((f, i) => (
                                    <motion.div 
                                        initial={{ opacity: 0, x: 20 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        key={i} 
                                        className="flex items-center p-3 bg-white border border-slate-100 rounded-xl shadow-sm"
                                    >
                                        <div className="w-8 h-8 bg-secondary/10 rounded-lg flex items-center justify-center mr-3">
                                            <CheckCircle className="w-4 h-4 text-secondary" />
                                        </div>
                                        <span className="text-sm font-medium text-slate-700 truncate">{f.name}</span>
                                    </motion.div>
                                ))}
                            </div>
                        )}

                        <button 
                            disabled={loading || !jobData.title || !jobData.description || resumes.length === 0}
                            onClick={handleUpload}
                            className="w-full mt-10 btn-primary flex items-center justify-center py-5 text-lg disabled:opacity-50 disabled:cursor-not-allowed group overflow-hidden relative"
                        >
                            <span className="relative z-10 flex items-center">
                                {loading ? (
                                    <>
                                        <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin mr-3" />
                                        Analyzing Profiles...
                                    </>
                                ) : (
                                    <>
                                        <Sparkles className="w-5 h-5 mr-3 group-hover:animate-pulse" />
                                        Start Intelligence Screening
                                    </>
                                )}
                            </span>
                            <div className="absolute inset-0 bg-gradient-to-r from-primary-dark to-primary opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                        </button>
                    </div>

                    {biasInfo && (biasInfo.biases.length > 0 || biasInfo.flags.length > 0) && (
                        <motion.div 
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            className="card border-amber-200 bg-amber-50/50 backdrop-blur-sm"
                        >
                            <h4 className="text-amber-800 font-bold mb-4 flex items-center">
                                <AlertCircle className="w-5 h-5 mr-2" /> Recruitment Integrity Flags
                            </h4>
                            <div className="space-y-3">
                                {biasInfo.biases.map((b, i) => (
                                    <div key={i} className="text-sm border-l-2 border-amber-300 pl-4 py-1">
                                        <p className="text-amber-900 font-semibold italic">"{b.word}"</p>
                                        <p className="text-amber-700 mt-1">{b.reason}</p>
                                        <p className="text-amber-800 font-bold mt-1 text-xs uppercase">Recommendation: {b.suggestion}</p>
                                    </div>
                                ))}
                                {biasInfo.flags.map((f, i) => (
                                    <div key={i} className="text-sm text-amber-700 flex items-start">
                                        <div className="w-1.5 h-1.5 bg-amber-400 rounded-full mt-1.5 mr-3 flex-shrink-0" />
                                        {f}
                                    </div>
                                ))}
                            </div>
                        </motion.div>
                    )}
                </section>
            </div>
        </div>
    );
};

export default UploadPage;
