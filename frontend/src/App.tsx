import React, { useState, useEffect, useCallback } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { Sidebar } from "./components/ui/Sidebar";
import { ErrorBoundary } from "./components/ui/ErrorBoundary";
import { authService } from "./services/api";

// Direct imports — no lazy() to avoid Vite ESM module namespace issues in dev
import Dashboard    from "./pages/Dashboard";
import Jobs         from "./pages/Jobs";
import Screening    from "./pages/Screening";
import Analytics    from "./pages/Analytics";
import Upload       from "./pages/Upload";
import Comparison   from "./pages/Comparison";
import Interview    from "./pages/Interview";
import JDComparison from "./pages/JDComparison";
import Login        from "./components/Login";
import Register     from "./components/Register";
import RAGChat      from "./components/RAGChat";
import JobDetail    from "./components/JobDetail";


export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(() => !!localStorage.getItem("token"));
  const [userEmail, setUserEmail] = useState(() => authService.getEmail() || "");
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem("theme") === "dark");

  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode);
    localStorage.setItem("theme", darkMode ? "dark" : "light");
  }, [darkMode]);

  const handleLogin = useCallback(() => {
    setIsAuthenticated(true);
    setUserEmail(authService.getEmail() || "");
  }, []);

  const handleLogout = useCallback(() => {
    authService.logout();
    setIsAuthenticated(false);
    setUserEmail("");
  }, []);

  if (!isAuthenticated) {
    return (
      <ErrorBoundary>
        <Routes>
          <Route path="/login"    element={<Login onLogin={handleLogin} />} />
          <Route path="/register" element={<Register />} />
          <Route path="*"         element={<Navigate to="/login" replace />} />
        </Routes>
      </ErrorBoundary>
    );
  }

  return (
    <div className="flex min-h-screen bg-background">
      <a href="#main-content" className="skip-link">Skip to main content</a>
      <Sidebar
        onLogout={handleLogout}
        userEmail={userEmail}
        darkMode={darkMode}
        onToggleDark={() => setDarkMode(!darkMode)}
      />
      <main id="main-content" className="flex-1 overflow-x-hidden min-h-screen">
        <div className="page-container">
          <ErrorBoundary>
            <Routes>
              <Route path="/"               element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard"      element={<Dashboard />} />
              <Route path="/jobs"           element={<Jobs />} />
              <Route path="/job/:id"        element={<JobDetail />} />
              <Route path="/candidates"     element={<Screening />} />
              <Route path="/analytics"      element={<Analytics />} />
              <Route path="/upload"         element={<Upload />} />
              <Route path="/chat"           element={<RAGChat />} />
              <Route path="/compare/:id"    element={<Comparison />} />
              <Route path="/interview/:id"  element={<Interview />} />
              <Route path="/jd-compare"     element={<JDComparison />} />
              <Route path="*"              element={<Navigate to="/dashboard" replace />} />

            </Routes>
          </ErrorBoundary>
        </div>
      </main>
    </div>
  );
}
