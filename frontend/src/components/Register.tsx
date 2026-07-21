import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button, Card, Input } from "./ui";
import { authService } from "../services/api";
import { Zap } from "lucide-react";

export default function Register() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [orgName, setOrgName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await authService.register(email, password, orgName);
      navigate("/login", { state: { message: "Registration successful! Please sign in." } });
    } catch (err: any) {
      setError(err.response?.data?.detail || "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-[#FFF9F0]">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-[#4D9DE0] border-[4px] border-black rounded-2xl shadow-[6px_6px_0px_#000] mb-5">
            <Zap className="w-10 h-10 text-white" />
          </div>
          <h1 className="text-5xl font-black text-black leading-none mb-2">Join AI ATS</h1>
          <p className="text-lg font-bold text-black/60">Create your organization account</p>
        </div>

        <Card>
          <form onSubmit={handleSubmit} className="space-y-5" noValidate>
            <Input label="Work Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com" required />
            <Input label="Organization Name" value={orgName} onChange={(e) => setOrgName(e.target.value)} placeholder="Acme Corp" required />
            <Input label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" required />
            {error && (
              <div className="p-4 border-[3px] border-black bg-[#FF3366]/10 rounded-xl text-[#FF3366] font-bold text-sm" role="alert">
                {error}
              </div>
            )}
            <Button type="submit" loading={loading} className="w-full" size="lg">
              Create Account
            </Button>
          </form>
        </Card>

        <p className="text-center mt-6 font-bold text-black/60">
          Already registered?{" "}
          <Link to="/login" className="text-[#FF6B35] underline underline-offset-2">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
