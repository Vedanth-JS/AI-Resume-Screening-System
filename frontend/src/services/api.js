import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

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

// 401 → logout
api.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.reload();
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
    if (res.data.access_token) localStorage.setItem('token', res.data.access_token);
    return res.data;
  },
  logout: () => localStorage.removeItem('token'),
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
  getOverview: () => api.get('/analytics/overview'),
};

// ─── Chat ─────────────────────────────────────────────────────────────────────
export const chatService = {
  query: (query) => api.post('/chat', null, { params: { query } }),
};

// ─── Bias ─────────────────────────────────────────────────────────────────────
export const biasService = {
  getReport: (jobId) => api.get('/bias-report', { params: { job_id: jobId } }),
};

export default api;
