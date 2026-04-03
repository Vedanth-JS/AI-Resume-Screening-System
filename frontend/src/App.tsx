import React, { Suspense, lazy } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import DashboardLayout from './layouts/DashboardLayout';

// Lazy load production pages
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Jobs = lazy(() => import('./pages/Jobs'));
const Screening = lazy(() => import('./pages/Screening'));
const Analytics = lazy(() => import('./pages/Analytics'));
const Interview = lazy(() => import('./pages/Interview'));
const Comparison = lazy(() => import('./pages/Comparison'));
const Upload = lazy(() => import('./pages/Upload'));

export default function App() {
  const isAuthenticated = true; // Placeholder for auth logic

  if (!isAuthenticated) return <Navigate to="/login" />;

  return (
    <Suspense fallback={
      <div className="h-screen w-screen flex items-center justify-center bg-background">
        <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    }>
      <Routes>
        <Route element={<DashboardLayout />}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/jobs" element={<Jobs />} />
          <Route path="/candidates" element={<Screening />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/interview/:id" element={<Interview />} />
          <Route path="/compare" element={<Comparison />} />
          <Route path="/upload" element={<Upload />} />
        </Route>
        <Route path="/login" element={<div>Login Page</div>} />
      </Routes>
    </Suspense>
  );
}
