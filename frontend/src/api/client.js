import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
})

// Jobs
export const getJobs = () => api.get('/jobs').then(r => r.data)
export const createJob = (data) => api.post('/jobs', data).then(r => r.data)
export const getJob = (id) => api.get(`/jobs/${id}`).then(r => r.data)

// Resumes
export const uploadResume = (file) => {
  const form = new FormData()
  form.append('file', file)
  return api.post('/resumes/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data)
}

// Screening
export const screenResume = (candidateId, jobId) =>
  api.post('/screen', { candidate_id: candidateId, job_id: jobId }).then(r => r.data)

export const batchScreen = (candidateIds, jobId) =>
  api.post('/screen/batch', { candidate_ids: candidateIds, job_id: jobId }).then(r => r.data)

export const rescreenJob = (jobId) =>
  api.post(`/jobs/${jobId}/rescreen`).then(r => r.data)

// Candidates
export const getCandidates = (jobId) =>
  api.get('/candidates', { params: { job_id: jobId } }).then(r => r.data)

export default api
