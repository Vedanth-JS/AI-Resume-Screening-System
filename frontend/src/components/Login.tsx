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

        {/* Content — expanded row layout */}
        <div style={{
          position: "relative", zIndex: 10,
          height: "100%", width: "100%", display: "flex", flexDirection: "row",
          alignItems: "center", justifyContent: "space-between",
          padding: "48px 64px", gap: 64, boxSizing: "border-box",
        }}>
          {/* ── Left text column (Expanded) ── */}
          <div style={{ flex: "0 0 440px", display: "flex", flexDirection: "column", justifyContent: "center" }}>
            {/* Logo */}
            <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 52 }}>
              <div style={{
                width: 58, height: 58,
                background: "linear-gradient(135deg, #FF6B35, #FF8C5A)",
                borderRadius: 16,
                display: "flex", alignItems: "center", justifyContent: "center",
                boxShadow: "0 0 36px rgba(255,107,53,0.55)",
              }}>
                <Zap size={30} color="white" />
              </div>
              <span style={{ fontSize: 30, fontWeight: 900, color: "white", letterSpacing: -0.5 }}>AI ATS</span>
            </div>

            <div style={{ marginBottom: 40 }}>
              <div style={{
                display: "inline-flex", alignItems: "center", gap: 8,
                background: "rgba(255,107,53,0.12)", border: "1px solid rgba(255,107,53,0.35)",
                borderRadius: 100, padding: "7px 18px", marginBottom: 22,
              }}>
                <Sparkles size={14} color="#FF6B35" />
                <span style={{ fontSize: 13, fontWeight: 700, color: "#FF6B35", letterSpacing: 1, textTransform: "uppercase" }}>Powered by Gemini AI</span>
              </div>
              <h2 style={{ fontSize: 50, fontWeight: 900, color: "white", lineHeight: 1.08, letterSpacing: -2, margin: 0 }}>
                Hire smarter,<br />
                <span style={{
                  background: "linear-gradient(90deg, #FF6B35, #FF8C5A, #FFB347)",
                  WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
                }}>not harder.</span>
              </h2>
              <p style={{ fontSize: 16, color: "rgba(255,255,255,0.55)", marginTop: 18, lineHeight: 1.65, maxWidth: 390 }}>
                The AI-powered ATS that turns hiring chaos into a streamlined, data-driven pipeline.
              </p>
            </div>

            {/* Feature list */}
            <div style={{ display: "flex", flexDirection: "column", gap: 14, marginBottom: 48 }}>
              {FEATURES.map((f, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 14 }}>
                  <div style={{
                    width: 22, height: 22, borderRadius: "50%",
                    background: "linear-gradient(135deg, #FF6B35, #FF8C5A)",
                    display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
                    boxShadow: "0 2px 8px rgba(255,107,53,0.4)",
                  }}>
                    <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                      <path d="M2 5l2 2 4-4" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </div>
                  <span style={{ fontSize: 15, color: "rgba(255,255,255,0.75)", fontWeight: 600 }}>{f}</span>
                </div>
              ))}
            </div>

            {/* Stats */}
            <div style={{ display: "flex", gap: 36 }}>
              {STATS.map((s, i) => (
                <div key={i}>
                  <div style={{ fontSize: 28, fontWeight: 900, color: "white", letterSpacing: -1 }}>{s.value}</div>
                  <div style={{ fontSize: 12, color: "rgba(255,255,255,0.45)", marginTop: 2, fontWeight: 600 }}>{s.label}</div>
                </div>
              ))}
            </div>
          </div>

          {/* ── Right: Animated Floating Dashboard Mockup (Expanded & Centered in Space) ── */}
          <div style={{
            flex: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            position: "relative",
            minHeight: 600,
            width: "100%",
          }}>

            {/* Floating Container holding the main card & badges */}
            <div style={{
              position: "relative",
              width: "100%",
              maxWidth: 540,
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              animation: "floatMain 7s ease-in-out infinite",
            }}>

              {/* Main pipeline card */}
              <div style={{
                width: "100%",
                background: "rgba(255, 255, 255, 0.05)",
                border: "1.5px solid rgba(255, 255, 255, 0.14)",
                borderRadius: 28,
                backdropFilter: "blur(28px)",
                padding: 28,
                boxShadow: "0 36px 90px rgba(0,0,0,0.65), 0 0 60px rgba(255,107,53,0.15)",
                transform: "perspective(1000px) rotateY(-3deg) rotateX(2deg)",
                transition: "all 0.4s ease",
              }}>
                {/* Card header */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 22 }}>
                  <div>
                    <div style={{ fontSize: 17, fontWeight: 800, color: "white", letterSpacing: -0.3 }}>Candidate Pipeline</div>
                    <div style={{ fontSize: 12, color: "rgba(255,255,255,0.45)", marginTop: 3 }}>Real-time Gemini AI Screening</div>
                  </div>
                  <div style={{
                    display: "flex", alignItems: "center", gap: 7,
                    fontSize: 12, fontWeight: 800, color: "#22c55e",
                    background: "rgba(34,197,94,0.12)", border: "1px solid rgba(34,197,94,0.3)",
                    borderRadius: 100, padding: "5px 14px",
                  }}>
                    <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#22c55e", animation: "livePulse 1.5s infinite" }} />
                    LIVE
                  </div>
                </div>

                {/* Pipeline stages bar */}
                <div style={{ display: "flex", gap: 8, marginBottom: 24 }}>
                  {[
                    { label: "New", count: 27, color: "#6366f1", flex: 3.2 },
                    { label: "Screened", count: 12, color: "#FF6B35", flex: 2.2 },
                    { label: "Interview", count: 8, color: "#FFB347", flex: 1.8 },
                    { label: "Offer", count: 3, color: "#22c55e", flex: 1.4 },
                    { label: "Hired", count: 2, color: "#10b981", flex: 1.2 },
                  ].map((stage, i) => (
                    <div key={i} style={{ flex: stage.flex }}>
                      <div style={{
                        height: 8, borderRadius: 8,
                        background: stage.color,
                        opacity: 0.9,
                        boxShadow: `0 0 12px ${stage.color}77`,
                        animation: `barGrow 1.2s ${i * 0.15}s both ease-out`,
                      }} />
                      <div style={{ fontSize: 11, color: "rgba(255,255,255,0.45)", marginTop: 7, fontWeight: 600 }}>{stage.label}</div>
                      <div style={{ fontSize: 13, fontWeight: 800, color: "white" }}>{stage.count}</div>
                    </div>
                  ))}
                </div>

                {/* Candidate rows */}
                {[
                  { name: "Arjun Mehta", role: "Python Backend Dev", score: 96, avatar: "AM", color: "#FF6B35", status: "Top Match" },
                  { name: "Priya Sharma", role: "React Frontend Engineer", score: 91, avatar: "PS", color: "#6366f1", status: "Interview" },
                  { name: "Rahul Nair", role: "ML / AI Specialist", score: 84, avatar: "RN", color: "#22c55e", status: "Screened" },
                  { name: "Sneha Patel", role: "Cloud DevOps Architect", score: 79, avatar: "SP", color: "#FFB347", status: "Review" },
                ].map((c, i) => (
                  <div key={i} style={{
                    display: "flex", alignItems: "center", gap: 16,
                    padding: "14px 16px", borderRadius: 16, marginBottom: 10,
                    background: i === 0 ? "rgba(255,107,53,0.09)" : "rgba(255,255,255,0.04)",
                    border: i === 0 ? "1px solid rgba(255,107,53,0.3)" : "1px solid rgba(255,255,255,0.06)",
                    animation: `slideInRow 0.5s ${0.3 + i * 0.12}s both ease-out`,
                    transition: "transform 0.2s ease",
                  }}>
                    {/* Avatar */}
                    <div style={{
                      width: 44, height: 44, borderRadius: "50%",
                      background: `linear-gradient(135deg, ${c.color}, ${c.color}77)`,
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontSize: 13, fontWeight: 800, color: "white", flexShrink: 0,
                      boxShadow: `0 4px 14px ${c.color}44`,
                    }}>{c.avatar}</div>

                    {/* Info */}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <span style={{ fontSize: 14, fontWeight: 700, color: "white" }}>{c.name}</span>
                        {i === 0 && (
                          <span style={{ fontSize: 10, fontWeight: 800, color: "#FF6B35", background: "rgba(255,107,53,0.18)", padding: "2px 8px", borderRadius: 4 }}>
                            MATCH
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: 12, color: "rgba(255,255,255,0.45)", marginTop: 3 }}>{c.role}</div>
                    </div>

                    {/* Score ring */}
                    <div style={{ position: "relative", width: 44, height: 44, flexShrink: 0 }}>
                      <svg width="44" height="44" viewBox="0 0 44 44" style={{ transform: "rotate(-90deg)" }}>
                        <circle cx="22" cy="22" r="18" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="4" />
                        <circle
                          cx="22" cy="22" r="18" fill="none"
                          stroke={c.color} strokeWidth="4"
                          strokeLinecap="round"
                          strokeDasharray={`${2 * Math.PI * 18}`}
                          strokeDashoffset={`${2 * Math.PI * 18 * (1 - c.score / 100)}`}
                          style={{ animation: `scoreRing 1.2s ${0.4 + i * 0.15}s both ease-out` }}
                        />
                      </svg>
                      <div style={{
                        position: "absolute", inset: 0,
                        display: "flex", alignItems: "center", justifyContent: "center",
                        fontSize: 12, fontWeight: 900, color: "white",
                      }}>{c.score}</div>
                    </div>
                  </div>
                ))}
              </div>

              {/* ── Floating Badge 1 (Top-Left): AI Match Score ── */}
              <div style={{
                position: "absolute", top: "-36px", left: "-70px",
                background: "rgba(15, 17, 32, 0.9)", border: "1px solid rgba(99,102,241,0.45)",
                borderRadius: 18, padding: "16px 22px", backdropFilter: "blur(20px)",
                boxShadow: "0 20px 45px rgba(0,0,0,0.6), 0 0 30px rgba(99,102,241,0.25)",
                animation: "floatBadge 5s ease-in-out infinite",
                zIndex: 20,
              }}>
                <div style={{ fontSize: 11, color: "rgba(255,255,255,0.55)", fontWeight: 700, letterSpacing: 0.6, marginBottom: 4 }}>AI SEMANTIC MATCH</div>
                <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
                  <span style={{ fontSize: 30, fontWeight: 900, color: "white" }}>96</span>
                  <span style={{ fontSize: 16, fontWeight: 700, color: "#6366f1" }}>%</span>
                </div>
                <div style={{ fontSize: 11, color: "#22c55e", fontWeight: 700, marginTop: 3, display: "flex", alignItems: "center", gap: 5 }}>
                  <span>▲</span> Gemini 2.5 Flash Match
                </div>
              </div>

              {/* ── Floating Badge 2 (Top-Right): Live Applicant ── */}
              <div style={{
                position: "absolute", top: "15px", right: "-80px",
                background: "rgba(15, 17, 32, 0.9)", border: "1px solid rgba(34,197,94,0.4)",
                borderRadius: 18, padding: "14px 20px", backdropFilter: "blur(20px)",
                boxShadow: "0 20px 45px rgba(0,0,0,0.6), 0 0 30px rgba(34,197,94,0.2)",
                animation: "floatBadgeSlow 6s 1s ease-in-out infinite",
                zIndex: 20,
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#22c55e", animation: "livePulse 1.5s infinite" }} />
                  <span style={{ fontSize: 12, fontWeight: 800, color: "white" }}>New Resume Upload</span>
                </div>
                <div style={{ fontSize: 14, fontWeight: 800, color: "#22c55e", marginTop: 5 }}>Mohit Agarwal</div>
                <div style={{ fontSize: 11, color: "rgba(255,255,255,0.5)", marginTop: 2 }}>Senior Fullstack • 7 yrs exp</div>
              </div>

              {/* ── Floating Badge 3 (Bottom-Left): Time Saved ── */}
              <div style={{
                position: "absolute", bottom: "15px", left: "-75px",
                background: "rgba(15, 17, 32, 0.9)", border: "1px solid rgba(255,107,53,0.4)",
                borderRadius: 18, padding: "16px 22px", backdropFilter: "blur(20px)",
                boxShadow: "0 20px 45px rgba(0,0,0,0.6), 0 0 30px rgba(255,107,53,0.2)",
                animation: "floatBadgeFast 4.5s 0.5s ease-in-out infinite",
                zIndex: 20,
              }}>
                <div style={{ fontSize: 11, color: "rgba(255,255,255,0.55)", fontWeight: 700, letterSpacing: 0.6, marginBottom: 4 }}>TIME SAVED PER RESUME</div>
                <div style={{ fontSize: 26, fontWeight: 900, color: "#FF6B35" }}>87% Faster</div>
                <div style={{
                  height: 5, borderRadius: 5, marginTop: 10,
                  background: "linear-gradient(90deg, #FF6B35, #FFB347)",
                  width: "100%", boxShadow: "0 0 12px rgba(255,107,53,0.6)",
                }} />
              </div>

              {/* ── Floating Badge 4 (Bottom-Right): Activity ── */}
              <div style={{
                position: "absolute", bottom: "-35px", right: "-65px",
                background: "rgba(15, 17, 32, 0.9)", border: "1px solid rgba(255,255,255,0.15)",
                borderRadius: 18, padding: "14px 20px", backdropFilter: "blur(20px)",
                boxShadow: "0 20px 45px rgba(0,0,0,0.6)",
                animation: "floatBadgeSlow 7s 1.5s ease-in-out infinite",
                minWidth: 190, zIndex: 20,
              }}>
                <div style={{ fontSize: 11, color: "rgba(255,255,255,0.5)", fontWeight: 700, letterSpacing: 0.6, marginBottom: 10 }}>LIVE ACTIVITY</div>
                {[
                  { text: "Resume screened", time: "Just now", dot: "#FF6B35" },
                  { text: "Interview scheduled", time: "2m ago", dot: "#6366f1" },
                  { text: "Offer accepted", time: "8m ago", dot: "#22c55e" },
                ].map((a, i) => (
                  <div key={i} style={{ display: "flex", alignItems: "center", gap: 9, marginBottom: 7 }}>
                    <div style={{ width: 7, height: 7, borderRadius: "50%", background: a.dot, flexShrink: 0, boxShadow: `0 0 8px ${a.dot}` }} />
                    <span style={{ fontSize: 12, color: "rgba(255,255,255,0.8)", fontWeight: 600, flex: 1 }}>{a.text}</span>
                    <span style={{ fontSize: 10, color: "rgba(255,255,255,0.4)" }}>{a.time}</span>
                  </div>
                ))}
              </div>

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
        @keyframes floatMain {
          0%, 100% { transform: translateY(0px) rotate(0deg); }
          50% { transform: translateY(-14px) rotate(0.5deg); }
        }
        @keyframes floatBadge {
          0%, 100% { transform: translateY(0px) rotate(0deg); }
          50% { transform: translateY(-10px) rotate(-1deg); }
        }
        @keyframes floatBadgeSlow {
          0%, 100% { transform: translateY(0px) rotate(0deg); }
          50% { transform: translateY(-12px) rotate(1deg); }
        }
        @keyframes floatBadgeFast {
          0%, 100% { transform: translateY(0px) rotate(0deg); }
          50% { transform: translateY(-8px) rotate(-0.5deg); }
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

