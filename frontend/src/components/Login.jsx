import React, { useState, useEffect } from 'react';
import { Zap, Mail, Lock, Loader2, ArrowRight } from 'lucide-react';
import { authService } from '../services/api';
import { Link, useLocation } from 'react-router-dom';

export function Login({ onLogin }) {
  const [email, setEmail] = useState('admin@ai-ats.com');
  const [password, setPassword] = useState('admin123');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const location = useLocation();

  useEffect(() => {
    if (location.state?.message) {
      setSuccess(location.state.message);
    }
  }, [location]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');
    
    try {
      await authService.login(email, password);
      onLogin();
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Invalid credentials. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6 relative overflow-hidden bg-[#020204]">
      {/* Background Orbs */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-blue-600/10 blur-[120px] rounded-full animate-pulse" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-purple-600/10 blur-[120px] rounded-full animate-pulse" />

      <div className="w-full max-w-md space-y-8 relative z-10 animate-in fade-in slide-in-from-bottom-8 duration-1000">
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-600 rounded-2xl shadow-[0_0_30px_rgba(59,130,246,0.3)] mb-4">
            <Zap className="w-10 h-10 text-white" />
          </div>
          <h1 className="text-4xl font-bold font-display text-white tracking-tight">Welcome Back</h1>
          <p className="text-slate-400">Enter your credentials to access the Hiring Cloud</p>
        </div>

        <div className="glass-card !p-8">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <label className="text-xs font-bold uppercase tracking-widest text-slate-500 ml-1">Work Email</label>
              <div className="relative group">
                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500 group-focus-within:text-blue-500 transition-colors" />
                <input 
                  type="email" 
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@company.com"
                  className="w-full bg-white/[0.03] border border-white/10 rounded-xl pl-12 pr-4 py-3.5 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/40 transition-all placeholder:text-slate-600"
                />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between items-center px-1">
                <label className="text-xs font-bold uppercase tracking-widest text-slate-500">Password</label>
                <button type="button" className="text-[10px] font-bold text-blue-500 uppercase hover:text-blue-400 transition-colors">Forgot?</button>
              </div>
              <div className="relative group">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500 group-focus-within:text-blue-500 transition-colors" />
                <input 
                  type="password" 
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-white/[0.03] border border-white/10 rounded-xl pl-12 pr-4 py-3.5 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/40 transition-all placeholder:text-slate-600"
                />
              </div>
            </div>

            {success && (
              <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-emerald-400 text-sm font-medium animate-in fade-in duration-500">
                {success}
              </div>
            )}

            {error && (
              <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm font-medium animate-in shake duration-500">
                {error}
              </div>
            )}

            <button 
              type="submit" 
              disabled={loading}
              className="btn-primary w-full py-4 flex items-center justify-center gap-2 group relative overflow-hidden"
            >
              {loading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <>
                  <span>Sign In to Dashboard</span>
                  <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </>
              )}
            </button>
            
            <div className="text-center pt-2">
              <p className="text-sm text-slate-500">
                Don't have an account?{' '}
                <Link to="/register" className="text-blue-500 hover:text-blue-400 font-medium transition-colors font-display">Create Account</Link>
              </p>
            </div>
          </form>
        </div>

        <div className="text-center p-6 border border-white/5 bg-white/[0.02] rounded-2xl mt-8">
          <p className="text-xs text-slate-500 leading-relaxed italic">
            "The best way to predict the future is to create it." <br /> 
            <span className="not-italic opacity-60">— Peter Drucker</span>
          </p>
        </div>
      </div>
    </div>
  );
}
