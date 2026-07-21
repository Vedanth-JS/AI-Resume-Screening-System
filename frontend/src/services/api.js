import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({ baseURL: API_BASE_URL });

// JWT interceptor
api.interceptors.request.use(
  (config) => {
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
      organization_slug: email.split('@')[0].replace('.', '-')
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

export default api;
