import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || '/api';

const api = axios.create({ baseURL: API_BASE_URL });

// JWT and path resolution interceptor
api.interceptors.request.use(
  (config) => {
    // Resolve Axios leading slash issue with baseURL subpaths (e.g. /api)
    if (config.url && config.url.startsWith('/') && config.baseURL) {
      const base = config.baseURL.endsWith('/') ? config.baseURL.slice(0, -1) : config.baseURL;
      if (config.url.startsWith(base)) {
        config.url = config.url;
      } else {
        config.url = base + config.url;
      }
      config.baseURL = undefined;
    }
    const token = localStorage.getItem('token');
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
  },
  (error) => Promise.reject(error)
);

  // 401 → Refresh or Logout
api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const refreshToken = localStorage.getItem('refreshToken');
      if (refreshToken) {
        try {
          const res = await axios.post(`${API_BASE_URL}/auth/refresh`, { refresh_token: refreshToken });
          localStorage.setItem('token', res.data.access_token);
          localStorage.setItem('refreshToken', res.data.refresh_token);
          originalRequest.headers.Authorization = `Bearer ${res.data.access_token}`;
          return api(originalRequest);
        } catch (refreshError) {
          authService.logout();
          window.location.reload();
        }
      } else {
        authService.logout();
        window.location.reload();
      }
    }
    return Promise.reject(error);
  }
);

// ─── Auth ────────────────────────────────────────────────────────────────────
export const authService = {
  login: async (email, password) => {
    const form = new FormData();
    form.append('username', email);
    form.append('password', password);
    const res = await api.post('/auth/token', form);
    if (res.data.access_token) {
        localStorage.setItem('token', res.data.access_token);
        localStorage.setItem('refreshToken', res.data.refresh_token);
    }
    return res.data;
  },
  register: async (email, password, orgName) => {
    const res = await api.post('/auth/register', {
      email,
      password,
      organization_name: orgName,
      organization_slug: email.split('@')[0].replace('.', '-'),
      full_name: orgName || email.split('@')[0]
    });
    return res.data;
  },
  logout: async () => {
    try { await api.post('/auth/logout'); } catch (e) {}
    localStorage.removeItem('token');
    localStorage.removeItem('refreshToken');
  },
  getEmail: () => {
    const token = localStorage.getItem('token');
    if (!token) return null;
    try {
      return JSON.parse(atob(token.split('.')[1])).sub || null;
    } catch { return null; }
  },
};

// ─── Jobs ─────────────────────────────────────────────────────────────────────
export const jobService = {
  getJobs: () => api.get('/jobs'),
  createJob: (data) => api.post('/jobs', data),
  getJob: (id) => api.get(`/jobs/${id}`),
};

// ─── Candidates ───────────────────────────────────────────────────────────────
export const candidateService = {
  getCandidates: () => api.get('/candidates'),
  uploadResume: (jobId, file) => {
    const form = new FormData();
    form.append('file', file);
    form.append('job_id', jobId);
    return api.post('/resume/upload', form, { headers: { 'Content-Type': 'multipart/form-data' } });
  },
  bulkUpload: (jobId, zipFile) => {
    const form = new FormData();
    form.append('file', zipFile);
    form.append('job_id', jobId);
    return api.post('/bulk-upload', form, { headers: { 'Content-Type': 'multipart/form-data' } });
  },
  getScore: (id) => api.get(`/score/${id}`),
  recommendJobs: (id) => api.get(`/recommend-jobs/${id}`),
  evaluateLLM: (candidateId, jobId) =>
    api.post('/llm/evaluate', { candidate_id: candidateId, job_id: jobId }),
};

// ─── Task Polling ─────────────────────────────────────────────────────────────
export const taskService = {
  getStatus: (taskId) => api.get(`/tasks/${taskId}/status`),
};

// ─── Batch Uploads ────────────────────────────────────────────────────────────
export const batchService = {
  upload: (jobId, zipFile) => {
    const form = new FormData();
    form.append('file', zipFile);
    form.append('job_id', jobId);
    return api.post('/batch/upload', form, { headers: { 'Content-Type': 'multipart/form-data' } });
  },
  getResults: (batchId) => api.get(`/batch/${batchId}/results`),
  exportCsv: (batchId) => api.get(`/batch/${batchId}/export?format=csv`, { responseType: 'blob' }),
};

// ─── Analytics ────────────────────────────────────────────────────────────────
export const analyticsService = {
  getOverview: (days = 30) => api.get('/analytics/overview', { params: { days } }),
  getFunnel: (jobId) => api.get('/analytics/funnel', { params: jobId ? { job_id: jobId } : {} }),
  getScoreDistribution: (jobId) => api.get('/analytics/score-distribution', { params: jobId ? { job_id: jobId } : {} }),
  getTimeToHire: () => api.get('/analytics/time-to-hire'),
  getSkillTrends: () => api.get('/analytics/skill-trends'),
  getRecruiters: () => api.get('/analytics/recruiters'),
  getUniversities: () => api.get('/analytics/universities'),
  getGeography: () => api.get('/analytics/geography'),
  getDiversity: () => api.get('/analytics/diversity'),
  getVolumeTrends: (days = 30) => api.get('/analytics/volume-trends', { params: { days } }),
  exportCSV: () => api.get('/analytics/export/csv', { responseType: 'blob' }),
};

// ─── Chat ─────────────────────────────────────────────────────────────────────
export const chatService = {
  query: (query) => api.post('/chat', null, { params: { query } }),
};

// ─── Interview Assistant ────────────────────────────────────────────────────
export const interviewService = {
  generateKit: (candidateId, jobId, focusAreas, difficulty) => {
    const form = new FormData();
    form.append('job_id', jobId);
    focusAreas.forEach(a => form.append('focus_areas', a));
    form.append('difficulty', difficulty);
    return api.post(`/candidates/${candidateId}/interview-questions`, form);
  },
  submitScorecard: (kitId, scores) => api.post(`/interviews/${kitId}/scorecard`, { scores }),
  getKit: (id) => api.get(`/interviews/${id}`),
};

// ─── Comparison ──────────────────────────────────────────────────────────────
export const comparisonService = {
  compare: (jobId, candidateIds) => 
    api.get(`/jobs/${jobId}/compare`, { params: { candidate_ids: candidateIds.join(',') } }),
};

// ─── ATS Stage transitions ───────────────────────────────────────────────────
export const atsService = {
  advanceStage: (applicationId, newStage, notes = '') => 
    api.post('/v2/ats/pipeline/advance', { application_id: applicationId, new_stage: newStage, notes }),
  rejectCandidate: (applicationId, reasonId = null, notes = '') => 
    api.post('/v2/ats/pipeline/reject', { application_id: applicationId, reason_id: reasonId, notes }),
};

// ─── Advanced ATS Scoring & Bulk Screening Engine ───────────────────────────
export const atsScoringService = {
  getRoles: () => api.get('/ats/roles'),
  score: (payload) => api.post('/ats/score', payload),
  scoreFile: (file, jobDescription, jobRole) => {
    const form = new FormData();
    form.append('file', file);
    if (jobDescription) form.append('job_description', jobDescription);
    if (jobRole) form.append('job_role', jobRole);
    return api.post('/ats/score-file', form, { timeout: 90000 });
  },
  bulkScreen: async (files, jobRole, jobDescription, customJd, weights) => {
    const buildForm = () => {
      const form = new FormData();
      files.forEach((f) => form.append('files', f));
      if (jobRole) form.append('job_role', jobRole);
      if (jobDescription) form.append('job_description', jobDescription);
      if (customJd) form.append('custom_jd', typeof customJd === 'string' ? customJd : JSON.stringify(customJd));
      if (weights) form.append('weights', typeof weights === 'string' ? weights : JSON.stringify(weights));
      return form;
    };
    try {
      return await api.post('/ats/bulk-screen', buildForm(), { timeout: 90000 });
    } catch (err) {
      const status = err?.response?.status;
      // Auto-retry once on Render Free Tier cold-start (502/503/504) or transient network blip
      if (!status || status === 502 || status === 503 || status === 504) {
        await new Promise((r) => setTimeout(r, 3000));
        return await api.post('/ats/bulk-screen', buildForm(), { timeout: 90000 });
      }
      throw err;
    }
  },
  rescore: (candidates, jobRole, jobDescription, customJd, weights) => {
    return api.post('/ats/rescore', {
      candidates,
      job_role: jobRole,
      job_description: jobDescription,
      custom_jd: customJd,
      weights,
    });
  },
  exportCsv: (candidates) => api.post('/ats/export-csv', candidates, { responseType: 'blob' }),
  exportExcel: (candidates) => api.post('/ats/export-excel', candidates, { responseType: 'blob' }),
};

// ─── Pipeline Kanban ─────────────────────────────────────────────────────────
export const pipelineService = {
  getStages: (jobId) => api.get('/pipeline', { params: jobId ? { job_id: jobId } : {} }),
  updateStatus: (applicationId, status) =>
    api.put(`/applications/${applicationId}/status`, { status }),
};

// ─── Interview Scheduling ─────────────────────────────────────────────────────
export const scheduleService = {
  schedule: (kitId, payload) => api.patch(`/v1/interviews/${kitId}/schedule`, payload),
  getUpcoming: () => api.get('/v1/interviews/upcoming'),
};

// ─── Saved Searches ───────────────────────────────────────────────────────────
export const savedSearchService = {
  list: () => api.get('/saved-searches/'),
  create: (name, filters) => api.post('/saved-searches/', { name, filters }),
  delete: (id) => api.delete(`/saved-searches/${id}`),
};


export const extractErrorMessage = (err, defaultMessage = 'An unexpected error occurred') => {
  console.error('API Connection Error Details:', {
    message: err?.message,
    status: err?.response?.status,
    data: err?.response?.data,
    config: {
      url: err?.config?.url,
      method: err?.config?.method,
      baseURL: err?.config?.baseURL
    }
  });
  if (!err) return defaultMessage;
  
  if (err.response?.data?.detail) {
    const detail = err.response.data.detail;
    if (typeof detail === 'string') {
      return detail;
    }
    if (Array.isArray(detail)) {
      return detail.map(item => {
        if (typeof item === 'string') return item;
        return item.msg || JSON.stringify(item);
      }).join(', ');
    }
    if (typeof detail === 'object') {
      return detail.msg || JSON.stringify(detail);
    }
  }
  
  if (err.response?.data?.message) {
    return err.response.data.message;
  }
  
  if (typeof err.response?.data === 'string') {
    const raw = err.response.data.trim();
    if (raw.startsWith('<') || raw.toLowerCase().includes('<!doctype html')) {
      const code = err.response?.status;
      if (code === 502 || code === 503 || code === 504) {
        return `Backend server is waking up (HTTP ${code}). Please retry in a few seconds.`;
      }
      return `Server returned HTTP ${code || 'error'}. Please retry.`;
    }
    if (raw) return raw;
  }
  
  if (err.response?.status) {
    return `Server error: ${err.response.status}`;
  }
  
  if (err.message) {
    return err.message;
  }
  
  if (err.request) {
    return 'Network error — please check your connection';
  }
  
  return defaultMessage;
};

export default api;

