import React, { useState } from "react";
import { Link } from "react-router-dom";
import { Button, Card, Input } from "./ui";
import { Zap } from "lucide-react";
import api from "../services/api";

interface LoginProps {
  onLogin: () => void;
}


export default function Login({ onLogin }: LoginProps) {
  const [email, setEmail] = useState("admin@ai-ats.com");
  const [password, setPassword] = useState("admin123");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showMFA, setShowMFA] = useState(false);
  const [mfaCode, setMfaCode] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const form = new FormData();
      form.append("username", email);
      form.append("password", password);
      if (showMFA && mfaCode) {
        form.append("mfa_code", mfaCode);
      }

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
      if (Array.isArray(errMsg)) {
        errMsg = errMsg.map((e: any) => e.msg || JSON.stringify(e)).join(", ");
      } else if (typeof errMsg === "object") {
        errMsg = JSON.stringify(errMsg);
      }
      
      setError(errMsg);
    } finally {
      if (!showMFA) setLoading(false);
    }
  };


  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-[#FFF9F0]">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-[#FF6B35] border-[4px] border-black rounded-2xl shadow-[6px_6px_0px_#000] mb-5">
            <Zap className="w-10 h-10 text-white" />
          </div>
          <h1 className="text-5xl font-black text-black leading-none mb-2">AI ATS</h1>
          <p className="text-lg font-bold text-black/60">
            {showMFA ? "Enter your authenticator code" : "Sign in to your dashboard"}
          </p>
        </div>

        <Card>
          <form onSubmit={handleSubmit} className="space-y-5" noValidate>
            {!showMFA ? (
              <>
                <Input
                  label="Email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@company.com"
                  required
                />
                <Input
                  label="Password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                />
              </>
            ) : (
              <>
                <div className="text-center mb-2">
                  <p className="font-bold text-black/70 text-sm">
                    Signed in as <span className="text-[#FF6B35]">{email}</span>
                  </p>
                </div>
                <Input
                  label="Authenticator Code (6 digits)"
                  type="text"
                  value={mfaCode}
                  onChange={(e) => setMfaCode(e.target.value)}
                  placeholder="000000"
                  maxLength={6}
                  required
                  autoFocus
                />
                <button
                  type="button"
                  onClick={() => setShowMFA(false)}
                  className="text-sm font-bold text-[#FF6B35] underline block mx-auto"
                >
                  ← Back to login
                </button>
              </>
            )}

            {error && (
              <div className="p-4 border-[3px] border-black bg-[#FF3366]/10 rounded-xl text-[#FF3366] font-bold text-sm" role="alert">
                {error}
              </div>
            )}

            <Button type="submit" loading={loading} className="w-full" size="lg">
              {showMFA ? "Verify & Sign In" : "Sign In"}
            </Button>
          </form>

        </Card>

        <p className="text-center mt-6 font-bold text-black/60">
          No account?{" "}
          <Link to="/register" className="text-[#FF6B35] underline underline-offset-2">
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
