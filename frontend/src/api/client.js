import axios from 'axios';

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || '/api',
});

export const jobsApi = {
    getAll: () => api.get('/jobs'),
    create: (data) => api.post('/job', data),
    screen: (data) => api.post('/screen', data),
    getResults: (jobId) => api.get(`/results/${jobId}`),
    getAnalytics: (jobId) => api.get(`/analytics/${jobId}`),
};

export default api;
