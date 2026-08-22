import React, { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { Zap, Mail, Lock, ArrowRight, Shield, Eye, EyeOff, Sparkles } from "lucide-react";
import api from "../services/api";

interface LoginProps {
  onLogin: () => void;
}

const PARTICLES = Array.from({ length: 28 }, (_, i) => ({
  id: i,
  x: Math.random() * 100,
  y: Math.random() * 100,
  size: Math.random() * 3 + 1,
  duration: Math.random() * 12 + 8,
  delay: Math.random() * 6,
}));

const STATS = [
  { label: "Resumes Screened", value: "2.4M+" },
  { label: "Time Saved", value: "87%" },
  { label: "Accuracy Rate", value: "99.1%" },
];

const FEATURES = [
  "AI-powered semantic candidate search",
  "Automated resume scoring & ranking",
  "Real-time pipeline tracking",
];

export default function Login({ onLogin }: LoginProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showMFA, setShowMFA] = useState(false);
  const [mfaCode, setMfaCode] = useState("");
  const [focused, setFocused] = useState<string | null>(null);
  const [mousePos, setMousePos] = useState({ x: 50, y: 50 });
  const leftRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleMove = (e: MouseEvent) => {
      if (!leftRef.current) return;
      const rect = leftRef.current.getBoundingClientRect();
      setMousePos({
        x: ((e.clientX - rect.left) / rect.width) * 100,
        y: ((e.clientY - rect.top) / rect.height) * 100,
      });
    };
    window.addEventListener("mousemove", handleMove);
    return () => window.removeEventListener("mousemove", handleMove);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const form = new FormData();
      form.append("username", email);
      form.append("password", password);
      if (showMFA && mfaCode) form.append("mfa_code", mfaCode);
      const res = await api.post("/auth/token", form);
      if (res.data?.access_token) {
        localStorage.setItem("token", res.data.access_token);
        localStorage.setItem("refreshToken", res.data.refresh_token);
        onLogin();
      }
    } catch (err: any) {
      const data = err.response?.data;
      if (data?.detail === "MFA required" || err.response?.status === 403 || data?.mfa_required) {
        setShowMFA(true);
        setError("");
        setLoading(false);
        return;
      }
      let errMsg = data?.detail || "Invalid credentials";
      if (Array.isArray(errMsg)) errMsg = errMsg.map((e: any) => e.msg || JSON.stringify(e)).join(", ");
      else if (typeof errMsg === "object") errMsg = JSON.stringify(errMsg);
      setError(errMsg);
    } finally {
      if (!showMFA) setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", fontFamily: "'Inter', system-ui, sans-serif", background: "#0a0a0f" }}>

      {/* ── LEFT PANEL ─────────────────────────────────────────────── */}
      <div
        ref={leftRef}
        style={{
          flex: 1,
          display: "none",
          position: "relative",
          overflow: "hidden",
          background: "linear-gradient(135deg, #0f0c29 0%, #111827 40%, #0f0c29 100%)",
        }}
        className="lg-show"
      >
        {/* Dynamic radial spotlight following mouse */}
        <div style={{
          position: "absolute", inset: 0, pointerEvents: "none",
          background: `radial-gradient(circle at ${mousePos.x}% ${mousePos.y}%, rgba(255,107,53,0.18) 0%, transparent 60%)`,
          transition: "background 0.1s ease",
        }} />

        {/* Animated grid */}
        <div style={{
          position: "absolute", inset: 0, opacity: 0.04,
          backgroundImage: "linear-gradient(rgba(255,255,255,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.5) 1px, transparent 1px)",
          backgroundSize: "48px 48px",
        }} />

        {/* Floating particles */}
        {PARTICLES.map(p => (
          <div
            key={p.id}
            style={{
              position: "absolute",
              left: `${p.x}%`,
              top: `${p.y}%`,
              width: p.size,
              height: p.size,
              borderRadius: "50%",
              background: `rgba(255,107,53,${Math.random() * 0.5 + 0.2})`,
              animation: `floatUp ${p.duration}s ${p.delay}s infinite ease-in-out`,
            }}
          />
        ))}

        {/* Glowing orbs */}
        <div style={{
          position: "absolute", top: "10%", left: "15%",
          width: 280, height: 280, borderRadius: "50%",
          background: "radial-gradient(circle, rgba(255,107,53,0.25) 0%, transparent 70%)",
          filter: "blur(40px)",
          animation: "pulse 4s infinite ease-in-out",
        }} />
        <div style={{
          position: "absolute", bottom: "15%", right: "10%",
          width: 220, height: 220, borderRadius: "50%",
          background: "radial-gradient(circle, rgba(99,102,241,0.2) 0%, transparent 70%)",
          filter: "blur(40px)",
          animation: "pulse 6s 2s infinite ease-in-out",
        }} />

        {/* Content — row layout */}
        <div style={{
          position: "relative", zIndex: 10,
          height: "100%", display: "flex", flexDirection: "row",
          alignItems: "center", padding: "48px 56px", gap: 48,
        }}>
          {/* ── Left text column ── */}
          <div style={{ flex: "0 0 360px", display: "flex", flexDirection: "column", justifyContent: "center" }}>
            {/* Logo */}
            <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 48 }}>
              <div style={{
                width: 52, height: 52,
                background: "linear-gradient(135deg, #FF6B35, #FF8C5A)",
                borderRadius: 14,
                display: "flex", alignItems: "center", justifyContent: "center",
                boxShadow: "0 0 30px rgba(255,107,53,0.5)",
              }}>
                <Zap size={26} color="white" />
              </div>
              <span style={{ fontSize: 26, fontWeight: 800, color: "white", letterSpacing: -0.5 }}>AI ATS</span>
            </div>

            <div style={{ marginBottom: 36 }}>
              <div style={{
                display: "inline-flex", alignItems: "center", gap: 8,
                background: "rgba(255,107,53,0.12)", border: "1px solid rgba(255,107,53,0.3)",
                borderRadius: 100, padding: "6px 16px", marginBottom: 20,
              }}>
                <Sparkles size={13} color="#FF6B35" />
                <span style={{ fontSize: 12, fontWeight: 600, color: "#FF6B35", letterSpacing: 1, textTransform: "uppercase" }}>Powered by Gemini AI</span>
              </div>
              <h2 style={{ fontSize: 42, fontWeight: 900, color: "white", lineHeight: 1.1, letterSpacing: -2, margin: 0 }}>
                Hire smarter,<br />
                <span style={{
                  background: "linear-gradient(90deg, #FF6B35, #FF8C5A, #FFB347)",
                  WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
                }}>not harder.</span>
              </h2>
              <p style={{ fontSize: 15, color: "rgba(255,255,255,0.5)", marginTop: 16, lineHeight: 1.65, maxWidth: 320 }}>
                The AI-powered ATS that turns hiring chaos into a streamlined, data-driven pipeline.
              </p>
            </div>

            {/* Feature list */}
            <div style={{ display: "flex", flexDirection: "column", gap: 12, marginBottom: 44 }}>
              {FEATURES.map((f, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <div style={{
                    width: 20, height: 20, borderRadius: "50%",
                    background: "linear-gradient(135deg, #FF6B35, #FF8C5A)",
                    display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
                  }}>
                    <svg width="9" height="9" viewBox="0 0 10 10" fill="none">
                      <path d="M2 5l2 2 4-4" stroke="white" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </div>
                  <span style={{ fontSize: 13, color: "rgba(255,255,255,0.65)", fontWeight: 500 }}>{f}</span>
                </div>
              ))}
            </div>

            {/* Stats */}
            <div style={{ display: "flex", gap: 28 }}>
              {STATS.map((s, i) => (
                <div key={i}>
                  <div style={{ fontSize: 24, fontWeight: 900, color: "white", letterSpacing: -1 }}>{s.value}</div>
                  <div style={{ fontSize: 11, color: "rgba(255,255,255,0.4)", marginTop: 2, fontWeight: 500 }}>{s.label}</div>
                </div>
              ))}
            </div>
          </div>

          {/* ── Right: Animated Dashboard Mockup ── */}
          <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", position: "relative", minHeight: 520 }}>

            {/* Main pipeline card */}
            <div style={{
              position: "absolute", top: "50%", left: "50%",
              transform: "translate(-50%, -50%)",
              width: 340, background: "rgba(255,255,255,0.05)",
              border: "1px solid rgba(255,255,255,0.1)", borderRadius: 20,
              backdropFilter: "blur(20px)", padding: 20,
              boxShadow: "0 24px 64px rgba(0,0,0,0.4)",
            }}>
              {/* Card header */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18 }}>
                <span style={{ fontSize: 13, fontWeight: 700, color: "white" }}>Candidate Pipeline</span>
                <span style={{
                  fontSize: 10, fontWeight: 600, color: "#22c55e",
                  background: "rgba(34,197,94,0.12)", border: "1px solid rgba(34,197,94,0.2)",
                  borderRadius: 100, padding: "3px 10px",
                }}>● LIVE</span>
              </div>

              {/* Pipeline stages bar */}
              <div style={{ display: "flex", gap: 4, marginBottom: 18 }}>
                {[
                  { label: "New", count: 27, color: "#6366f1", w: "32%" },
                  { label: "Screen", count: 12, color: "#FF6B35", w: "22%" },
                  { label: "Interview", count: 8, color: "#FFB347", w: "18%" },
                  { label: "Offer", count: 3, color: "#22c55e", w: "14%" },
                  { label: "Hired", count: 2, color: "#10b981", w: "14%" },
                ].map((stage, i) => (
                  <div key={i} style={{ flex: stage.w === "32%" ? 3.2 : stage.w === "22%" ? 2.2 : stage.w === "18%" ? 1.8 : 1.4 }}>
                    <div style={{
                      height: 6, borderRadius: 6,
                      background: stage.color,
                      opacity: 0.85,
                      animation: `barGrow 1.2s ${i * 0.15}s both ease-out`,
                    }} />
                    <div style={{ fontSize: 9, color: "rgba(255,255,255,0.4)", marginTop: 5, fontWeight: 600 }}>{stage.label}</div>
                    <div style={{ fontSize: 11, fontWeight: 700, color: "white" }}>{stage.count}</div>
                  </div>
                ))}
              </div>

              {/* Candidate rows */}
              {[
                { name: "Arjun Mehta", role: "Python Engineer", score: 94, avatar: "AM", color: "#FF6B35", status: "Shortlisted" },
                { name: "Priya Sharma", role: "React Developer", score: 88, avatar: "PS", color: "#6366f1", status: "Interview" },
                { name: "Rahul Nair", role: "ML Engineer", score: 76, avatar: "RN", color: "#22c55e", status: "Screening" },
              ].map((c, i) => (
                <div key={i} style={{
                  display: "flex", alignItems: "center", gap: 12,
                  padding: "10px 12px", borderRadius: 12, marginBottom: 6,
                  background: "rgba(255,255,255,0.04)",
                  border: "1px solid rgba(255,255,255,0.06)",
                  animation: `slideInRow 0.5s ${0.4 + i * 0.15}s both ease-out`,
                }}>
                  {/* Avatar */}
                  <div style={{
                    width: 34, height: 34, borderRadius: "50%",
                    background: `linear-gradient(135deg, ${c.color}CC, ${c.color}66)`,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontSize: 11, fontWeight: 800, color: "white", flexShrink: 0,
                  }}>{c.avatar}</div>
                  {/* Info */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 12, fontWeight: 700, color: "white" }}>{c.name}</div>
                    <div style={{ fontSize: 10, color: "rgba(255,255,255,0.4)" }}>{c.role}</div>
                  </div>
                  {/* Score ring */}
                  <div style={{ position: "relative", width: 36, height: 36, flexShrink: 0 }}>
                    <svg width="36" height="36" viewBox="0 0 36 36" style={{ transform: "rotate(-90deg)" }}>
                      <circle cx="18" cy="18" r="14" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="3" />
                      <circle
                        cx="18" cy="18" r="14" fill="none"
                        stroke={c.color} strokeWidth="3"
                        strokeLinecap="round"
                        strokeDasharray={`${2 * Math.PI * 14}`}
                        strokeDashoffset={`${2 * Math.PI * 14 * (1 - c.score / 100)}`}
                        style={{ animation: `scoreRing 1s ${0.5 + i * 0.15}s both ease-out` }}
                      />
                    </svg>
                    <div style={{
                      position: "absolute", inset: 0,
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontSize: 9, fontWeight: 800, color: "white",
                    }}>{c.score}</div>
                  </div>
                </div>
              ))}
            </div>

            {/* Floating top-left: AI Match badge */}
            <div style={{
              position: "absolute", top: "4%", left: "-4%",
              background: "rgba(99,102,241,0.15)", border: "1px solid rgba(99,102,241,0.3)",
              borderRadius: 14, padding: "12px 16px", backdropFilter: "blur(12px)",
              animation: "floatBadge 4s ease-in-out infinite",
            }}>
              <div style={{ fontSize: 10, color: "rgba(255,255,255,0.5)", fontWeight: 600, marginBottom: 4 }}>AI MATCH SCORE</div>
              <div style={{ fontSize: 22, fontWeight: 900, color: "white" }}>94<span style={{ fontSize: 12, color: "rgba(255,255,255,0.4)" }}>%</span></div>
              <div style={{ fontSize: 10, color: "#22c55e", fontWeight: 600, marginTop: 2 }}>▲ Top candidate</div>
            </div>

            {/* Floating top-right: New applicant */}
            <div style={{
              position: "absolute", top: "8%", right: "-6%",
              background: "rgba(34,197,94,0.1)", border: "1px solid rgba(34,197,94,0.25)",
              borderRadius: 14, padding: "10px 14px", backdropFilter: "blur(12px)",
              animation: "floatBadge 5s 1s ease-in-out infinite",
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <div style={{
                  width: 8, height: 8, borderRadius: "50%", background: "#22c55e",
                  animation: "livePulse 1.5s infinite",
                }} />
                <span style={{ fontSize: 11, fontWeight: 700, color: "white" }}>New applicant</span>
              </div>
              <div style={{ fontSize: 12, fontWeight: 700, color: "rgba(255,255,255,0.7)", marginTop: 4 }}>Mohit Agarwal</div>
              <div style={{ fontSize: 10, color: "rgba(255,255,255,0.4)" }}>Senior Dev • 7 yrs exp</div>
            </div>

            {/* Floating bottom-left: Time saved */}
            <div style={{
              position: "absolute", bottom: "6%", left: "-2%",
              background: "rgba(255,107,53,0.12)", border: "1px solid rgba(255,107,53,0.25)",
              borderRadius: 14, padding: "12px 16px", backdropFilter: "blur(12px)",
              animation: "floatBadge 4.5s 0.5s ease-in-out infinite",
            }}>
              <div style={{ fontSize: 10, color: "rgba(255,255,255,0.45)", fontWeight: 600, marginBottom: 2 }}>TIME SAVED TODAY</div>
              <div style={{ fontSize: 20, fontWeight: 900, color: "#FF6B35" }}>4.2 hrs</div>
              <div style={{
                height: 3, borderRadius: 3, marginTop: 6,
                background: "linear-gradient(90deg, #FF6B35, #FFB347)",
                width: "70%",
              }} />
            </div>

            {/* Floating bottom-right: Activity */}
            <div style={{
              position: "absolute", bottom: "9%", right: "-4%",
              background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: 14, padding: "10px 14px", backdropFilter: "blur(12px)",
              animation: "floatBadge 6s 2s ease-in-out infinite",
              minWidth: 150,
            }}>
              <div style={{ fontSize: 10, color: "rgba(255,255,255,0.4)", fontWeight: 600, marginBottom: 8 }}>RECENT ACTIVITY</div>
              {[
                { text: "Resume screened", time: "2s ago", dot: "#FF6B35" },
                { text: "Interview scheduled", time: "1m ago", dot: "#6366f1" },
                { text: "Offer sent", time: "5m ago", dot: "#22c55e" },
              ].map((a, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 6 }}>
                  <div style={{ width: 6, height: 6, borderRadius: "50%", background: a.dot, flexShrink: 0 }} />
                  <span style={{ fontSize: 10, color: "rgba(255,255,255,0.6)", flex: 1 }}>{a.text}</span>
                  <span style={{ fontSize: 9, color: "rgba(255,255,255,0.25)" }}>{a.time}</span>
                </div>
              ))}
            </div>

          </div>
        </div>

      </div>

      {/* ── RIGHT PANEL ────────────────────────────────────────────── */}
      <div style={{
        width: "100%",
        maxWidth: 480,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        padding: "48px 40px",
        background: "#0d0d14",
        position: "relative",
        overflow: "hidden",
      }}>
        {/* subtle background glow */}
        <div style={{
          position: "absolute", top: -80, right: -80,
          width: 300, height: 300, borderRadius: "50%",
          background: "radial-gradient(circle, rgba(255,107,53,0.08) 0%, transparent 70%)",
          pointerEvents: "none",
        }} />
        <div style={{
          position: "absolute", bottom: -60, left: -60,
          width: 240, height: 240, borderRadius: "50%",
          background: "radial-gradient(circle, rgba(99,102,241,0.07) 0%, transparent 70%)",
          pointerEvents: "none",
        }} />

        <div style={{ position: "relative", zIndex: 10 }}>
          {/* Mobile logo */}
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 40 }} className="mobile-logo">
            <div style={{
              width: 44, height: 44,
              background: "linear-gradient(135deg, #FF6B35, #FF8C5A)",
              borderRadius: 12,
              display: "flex", alignItems: "center", justifyContent: "center",
              boxShadow: "0 0 24px rgba(255,107,53,0.4)",
            }}>
              <Zap size={22} color="white" />
            </div>
            <span style={{ fontSize: 22, fontWeight: 800, color: "white" }}>AI ATS</span>
          </div>

          {/* Heading */}
          <div style={{ marginBottom: 36 }}>
            <h1 style={{ fontSize: 30, fontWeight: 800, color: "white", margin: 0, letterSpacing: -0.8 }}>
              {showMFA ? "Two-factor auth" : "Welcome back"}
            </h1>
            <p style={{ fontSize: 15, color: "rgba(255,255,255,0.45)", marginTop: 8 }}>
              {showMFA
                ? `Enter the 6-digit code for ${email}`
                : "Sign in to your hiring dashboard"}
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} noValidate style={{ display: "flex", flexDirection: "column", gap: 18 }}>
            {!showMFA ? (
              <>
                {/* Email */}
                <div>
                  <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "rgba(255,255,255,0.7)", marginBottom: 8 }}>
                    Email address
                  </label>
                  <div style={{
                    position: "relative",
                    background: focused === "email" ? "rgba(255,107,53,0.06)" : "rgba(255,255,255,0.04)",
                    border: `1.5px solid ${focused === "email" ? "rgba(255,107,53,0.5)" : "rgba(255,255,255,0.1)"}`,
                    borderRadius: 12,
                    transition: "all 0.2s ease",
                  }}>
                    <Mail size={16} color="rgba(255,255,255,0.3)" style={{ position: "absolute", left: 14, top: "50%", transform: "translateY(-50%)" }} />
                    <input
                      type="email"
                      value={email}
                      onChange={e => setEmail(e.target.value)}
                      onFocus={() => setFocused("email")}
                      onBlur={() => setFocused(null)}
                      placeholder="you@company.com"
                      required
                      style={{
                        width: "100%", height: 50, paddingLeft: 42, paddingRight: 16,
                        background: "transparent", border: "none", outline: "none",
                        color: "white", fontSize: 15, fontFamily: "inherit",
                        boxSizing: "border-box",
                      }}
                    />
                  </div>
                </div>

                {/* Password */}
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                    <label style={{ fontSize: 13, fontWeight: 600, color: "rgba(255,255,255,0.7)" }}>
                      Password
                    </label>
                  </div>
                  <div style={{
                    position: "relative",
                    background: focused === "password" ? "rgba(255,107,53,0.06)" : "rgba(255,255,255,0.04)",
                    border: `1.5px solid ${focused === "password" ? "rgba(255,107,53,0.5)" : "rgba(255,255,255,0.1)"}`,
                    borderRadius: 12,
                    transition: "all 0.2s ease",
                  }}>
                    <Lock size={16} color="rgba(255,255,255,0.3)" style={{ position: "absolute", left: 14, top: "50%", transform: "translateY(-50%)" }} />
                    <input
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={e => setPassword(e.target.value)}
                      onFocus={() => setFocused("password")}
                      onBlur={() => setFocused(null)}
                      placeholder="••••••••••"
                      required
                      style={{
                        width: "100%", height: 50, paddingLeft: 42, paddingRight: 46,
                        background: "transparent", border: "none", outline: "none",
                        color: "white", fontSize: 15, fontFamily: "inherit",
                        boxSizing: "border-box",
                      }}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      style={{
                        position: "absolute", right: 14, top: "50%", transform: "translateY(-50%)",
                        background: "none", border: "none", cursor: "pointer", padding: 0,
                        color: "rgba(255,255,255,0.3)", display: "flex", alignItems: "center",
                      }}
                    >
                      {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>
              </>
            ) : (
              <div>
                <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "rgba(255,255,255,0.7)", marginBottom: 8 }}>
                  Authenticator Code
                </label>
                <div style={{
                  background: focused === "mfa" ? "rgba(255,107,53,0.06)" : "rgba(255,255,255,0.04)",
                  border: `1.5px solid ${focused === "mfa" ? "rgba(255,107,53,0.5)" : "rgba(255,255,255,0.1)"}`,
                  borderRadius: 12, transition: "all 0.2s ease",
                }}>
                  <div style={{ position: "relative" }}>
                    <Shield size={16} color="rgba(255,255,255,0.3)" style={{ position: "absolute", left: 14, top: "50%", transform: "translateY(-50%)" }} />
                    <input
                      type="text"
                      value={mfaCode}
                      onChange={e => setMfaCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                      onFocus={() => setFocused("mfa")}
                      onBlur={() => setFocused(null)}
                      placeholder="000000"
                      maxLength={6}
                      autoFocus
                      required
                      style={{
                        width: "100%", height: 50, paddingLeft: 42, paddingRight: 16,
                        background: "transparent", border: "none", outline: "none",
                        color: "white", fontSize: 22, fontFamily: "monospace", letterSpacing: 8,
                        boxSizing: "border-box",
                      }}
                    />
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setShowMFA(false)}
                  style={{ background: "none", border: "none", cursor: "pointer", color: "#FF6B35", fontSize: 13, fontWeight: 600, marginTop: 12, padding: 0 }}
                >
                  ← Back to login
                </button>
              </div>
            )}

            {/* Error */}
            {error && (
              <div style={{
                padding: "12px 16px",
                background: "rgba(255,51,102,0.08)",
                border: "1px solid rgba(255,51,102,0.25)",
                borderRadius: 10,
                color: "#FF6B8A",
                fontSize: 13,
                fontWeight: 500,
              }}>
                {error}
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              style={{
                height: 52,
                background: loading
                  ? "rgba(255,107,53,0.5)"
                  : "linear-gradient(135deg, #FF6B35, #FF8C5A)",
                border: "none",
                borderRadius: 12,
                color: "white",
                fontSize: 16,
                fontWeight: 700,
                cursor: loading ? "not-allowed" : "pointer",
                display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
                boxShadow: loading ? "none" : "0 4px 24px rgba(255,107,53,0.35)",
                transition: "all 0.2s ease",
                letterSpacing: 0.2,
              }}
              onMouseEnter={e => { if (!loading) (e.currentTarget as HTMLButtonElement).style.transform = "translateY(-1px)"; }}
              onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.transform = "translateY(0)"; }}
            >
              {loading ? (
                <div style={{
                  width: 20, height: 20, border: "2.5px solid rgba(255,255,255,0.3)",
                  borderTopColor: "white", borderRadius: "50%",
                  animation: "spin 0.7s linear infinite",
                }} />
              ) : (
                <>
                  {showMFA ? "Verify & Sign In" : "Sign In"}
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </form>

          {/* Footer */}
          <p style={{ textAlign: "center", marginTop: 28, fontSize: 14, color: "rgba(255,255,255,0.35)", fontWeight: 500 }}>
            Don't have an account?{" "}
            <Link to="/register" style={{ color: "#FF6B35", textDecoration: "none", fontWeight: 700 }}>
              Create one
            </Link>
          </p>
        </div>
      </div>

      {/* ── Global styles ────────────────────────────────────────── */}
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
        @keyframes floatUp {
          0%, 100% { transform: translateY(0) scale(1); opacity: 0.6; }
          50% { transform: translateY(-20px) scale(1.2); opacity: 1; }
        }
        @keyframes pulse {
          0%, 100% { opacity: 0.6; transform: scale(1); }
          50% { opacity: 1; transform: scale(1.08); }
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        @keyframes floatBadge {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-10px); }
        }
        @keyframes livePulse {
          0%, 100% { opacity: 1; transform: scale(1); box-shadow: 0 0 0 0 rgba(34,197,94,0.4); }
          50% { opacity: 0.8; transform: scale(1.3); box-shadow: 0 0 0 6px rgba(34,197,94,0); }
        }
        @keyframes barGrow {
          from { transform: scaleX(0); transform-origin: left; opacity: 0; }
          to { transform: scaleX(1); transform-origin: left; opacity: 0.85; }
        }
        @keyframes slideInRow {
          from { opacity: 0; transform: translateX(-12px); }
          to { opacity: 1; transform: translateX(0); }
        }
        @keyframes scoreRing {
          from { stroke-dashoffset: ${2 * Math.PI * 14}; }
        }
        @media (min-width: 1024px) {
          .lg-show { display: flex !important; }
        }
        input::placeholder { color: rgba(255,255,255,0.2); }
        input:-webkit-autofill,
        input:-webkit-autofill:hover,
        input:-webkit-autofill:focus {
          -webkit-text-fill-color: white;
          -webkit-box-shadow: 0 0 0px 1000px transparent inset;
          transition: background-color 5000s ease-in-out 0s;
        }
      `}</style>
    </div>
  );
}

