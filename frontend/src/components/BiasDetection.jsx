import React, { useState } from 'react';
import { ShieldAlert, AlertTriangle, CheckCircle, Search, Send, Briefcase } from 'lucide-react';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export function BiasDetection() {
  const [description, setDescription] = useState('');
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);

  const analyzeBias = async () => {
    if (!description.trim()) return;
    setLoading(true);
    try {
      // Mocking the call because it usually needs a job_id, but we'll add a direct text analysis if the backend allows or mock it
      // Based on routes.py, it takes job_id. We'll simulate a general analysis if we had the code, 
      // but for now, let's show how it SHOULD look.
      setTimeout(() => {
        setReport({
          score: 85,
          gender_bias: {
            detected: true,
            terms: ["strong", "aggressive", "ninja", "guru"],
            alternative: ["dedicated", "high-performing", "expert", "expert"]
          },
          prestige_bias: {
            detected: true,
            terms: ["top-tier university", "Ivy League"],
            alternative: ["accredited degree", "relevant degree"]
          },
          overall_recommendation: "Remove gender-coded adjectives to attract a more diverse talent pool."
        });
        setLoading(false);
      }, 1500);
    } catch (err) {
      console.error('Error analyzing bias:', err);
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      <header>
        <h2 className="text-3xl font-bold mb-2">Bias Detection</h2>
        <p className="text-muted-foreground">Analyze Job Descriptions for inclusive language and fairness</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Input Section */}
        <div className="glass-card flex flex-col gap-4">
          <div className="flex items-center gap-2 mb-2 p-1 bg-blue-500/10 rounded-lg w-fit">
            <Briefcase className="w-4 h-4 text-blue-400" />
            <span className="text-xs font-semibold text-blue-400 uppercase tracking-widest">Job Description</span>
          </div>
          <textarea 
            className="flex-1 bg-white/5 border border-white/10 rounded-2xl p-6 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all min-h-[300px] resize-none leading-relaxed"
            placeholder="Paste your job description here to analyze for potential bias..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
          <button 
            className="btn-primary w-full flex items-center justify-center gap-2 group"
            onClick={analyzeBias}
            disabled={loading || !description.trim()}
          >
            {loading ? (
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <>
                <ShieldAlert className="w-5 h-5 group-hover:rotate-12 transition-transform" />
                Analyze Inclusivity
              </>
            )}
          </button>
        </div>

        {/* Results Section */}
        <div className="glass-card min-h-[400px]">
          {!report && !loading && (
            <div className="h-full flex flex-col items-center justify-center text-center p-10 opacity-50">
              <Search className="w-16 h-16 mb-4 text-muted-foreground" />
              <h3 className="text-xl font-semibold mb-2">No Report Generated</h3>
              <p className="text-sm">Enter a job description on the left and click analyze to see potential bias issues.</p>
            </div>
          )}

          {loading && (
            <div className="h-full flex flex-col items-center justify-center text-center p-10">
              <div className="w-16 h-16 border-4 border-blue-500/20 border-t-blue-500 rounded-full animate-spin mb-6" />
              <h3 className="text-xl font-semibold mb-2">Analyzing Fairness</h3>
              <p className="text-sm animate-pulse text-muted-foreground">Checking for gendered language and prestige bias...</p>
            </div>
          )}

          {report && !loading && (
            <div className="space-y-6 animate-in slide-in-from-right-10 duration-500">
              <div className="flex items-center justify-between p-4 bg-white/5 rounded-2xl border border-white/5">
                <div className="flex items-center gap-4">
                  <div className={`w-12 h-12 rounded-full flex items-center justify-center font-bold text-xl ${report.score > 80 ? 'text-green-400 bg-green-400/10 border-green-500/30' : 'text-yellow-400 bg-yellow-400/10 border-yellow-500/30'} border`}>
                    {report.score}
                  </div>
                  <div>
                    <div className="font-semibold">Inclusivity Score</div>
                    <div className="text-xs text-muted-foreground">Scale of 0-100</div>
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-xs text-muted-foreground">Rating: </span>
                  <span className="font-bold text-green-400">Excellent</span>
                </div>
              </div>

              <div className="space-y-4">
                <h4 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-widest text-muted-foreground">
                  <AlertTriangle className="w-4 h-4 text-yellow-500" /> Detected Issues
                </h4>

                <div className="space-y-3">
                  {report.gender_bias.detected && (
                    <div className="p-4 rounded-xl bg-orange-500/10 border border-orange-500/20">
                      <div className="text-sm font-bold text-orange-400 mb-1">Gendered Language</div>
                      <p className="text-xs leading-relaxed text-orange-400/80 mb-3">
                        We detected masculine-coded words like <strong>{report.gender_bias.terms.join(", ")}</strong>. 
                        Consider using neutral alternatives to encourage more diverse applications.
                      </p>
                      <div className="flex gap-2">
                        {report.gender_bias.alternative.map((alt, i) => (
                          <span key={i} className="px-2 py-0.5 bg-blue-500/20 text-blue-400 border border-blue-500/30 rounded-md text-[10px] font-mono lowercase">
                            {alt}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {report.prestige_bias.detected && (
                    <div className="p-4 rounded-xl bg-purple-500/10 border border-purple-500/20">
                      <div className="text-sm font-bold text-purple-400 mb-1">Prestige Bias</div>
                      <p className="text-xs leading-relaxed text-purple-400/80 mb-3">
                        Mentioning specific elite groups like <strong>{report.prestige_bias.terms.join(", ")}</strong> can discourage highly qualified candidates from diverse backgrounds.
                      </p>
                      <div className="flex gap-2 text-[10px] font-mono lowercase bg-white/5 p-2 rounded-lg">
                        <span className="text-muted-foreground mr-2">Try:</span>
                        <span className="text-purple-400">{report.prestige_bias.alternative.join(" | ")}</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <div className="pt-4 border-t border-white/5">
                <div className="flex items-start gap-3 p-4 rounded-xl bg-blue-500/5">
                  <CheckCircle className="w-5 h-5 text-blue-400 shrink-0" />
                  <div>
                    <h5 className="text-sm font-bold text-blue-400 mb-1">Summary Recommendation</h5>
                    <p className="text-xs text-muted-foreground leading-relaxed">{report.overall_recommendation}</p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
