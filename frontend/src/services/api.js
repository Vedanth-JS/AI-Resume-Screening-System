import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
});

export const jobService = {
  getJobs: () => api.get('/jobs'),
  createJob: (data) => api.post('/jobs', data),
  getJob: (id) => api.get(`/jobs/${id}`),
};

export const candidateService = {
  uploadResume: (jobId, file) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('job_id', jobId);
    return api.post('/resume/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  bulkUpload: (jobId, zipFile) => {
    const formData = new FormData();
    formData.append('file', zipFile);
    formData.append('job_id', jobId);
    return api.post('/bulk-upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  getScore: (candidateId) => api.get(`/score/${candidateId}`),
  recommendJobs: (candidateId) => api.get(`/recommend-jobs/${candidateId}`),
  evaluateLLM: (candidateId, jobId) => api.post('/llm/evaluate', { candidate_id: candidateId, job_id: jobId }),
};

export const chatService = {
  query: (query) => api.post('/chat', null, { params: { query } }),
};

export const biasService = {
  getReport: (jobId) => api.get('/bias-report', { params: { job_id: jobId } }),
};

export default api;
