import { useState, useCallback, useEffect } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, X, FileText, CheckCircle2, Loader2, AlertCircle } from 'lucide-react'
import { getJobs, uploadResume, batchScreen } from '../api/client'
import { useNavigate } from 'react-router-dom'

export default function UploadPage() {
  const [jobs, setJobs] = useState([])
  const [selectedJobId, setSelectedJobId] = useState('')
  const [files, setFiles] = useState([])
  const [uploadStatus, setUploadStatus] = useState('idle') // idle, uploading, screening, complete
  const [progress, setProgress] = useState({ current: 0, total: 0 })
  const navigate = useNavigate()

  useEffect(() => {
    getJobs().then(setJobs).catch(console.error)
  }, [])

  const onDrop = useCallback(acceptedFiles => {
    setFiles(prev => [...prev, ...acceptedFiles.map(file => ({
      file,
      id: Math.random().toString(36).substr(2, 9),
      name: file.name,
      status: 'pending' // pending, uploading, done, error
    }))])
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] }
  })

  const removeFile = (id) => {
    setFiles(files.filter(f => f.id !== id))
  }

  const startProcessing = async () => {
    if (!selectedJobId) return alert('Please select a job first')
    if (files.length === 0) return alert('No files to upload')

    setUploadStatus('uploading')
    const uploadedCandidateIds = []
    setProgress({ current: 0, total: files.length })

    // 1. Upload Resumes
    for (let i = 0; i < files.length; i++) {
        const fileObj = files[i]
        setFiles(prev => prev.map(f => f.id === fileObj.id ? { ...f, status: 'uploading' } : f))
        
        try {
            const candidate = await uploadResume(fileObj.file)
            uploadedCandidateIds.push(candidate.id)
            setFiles(prev => prev.map(f => f.id === fileObj.id ? { ...f, status: 'done' } : f))
        } catch (err) {
            console.error(err)
            setFiles(prev => prev.map(f => f.id === fileObj.id ? { ...f, status: 'error' } : f))
        }
        setProgress(p => ({ ...p, current: i + 1 }))
    }

    // 2. Batch Screen
    if (uploadedCandidateIds.length > 0) {
        setUploadStatus('screening')
        try {
            await batchScreen(uploadedCandidateIds, selectedJobId)
            setUploadStatus('complete')
            // Delay redirect to show success
            setTimeout(() => {
                navigate(`/dashboard?job_id=${selectedJobId}`)
            }, 1000)
        } catch (err) {
            console.error(err)
            setUploadStatus('idle')
            alert('Screening failed. Please try again.')
        }
    } else {
        setUploadStatus('idle')
        alert('All uploads failed.')
    }
  }

  return (
    <div className="max-w-3xl mx-auto py-8">
      <div className="mb-8">
        <h1 className="page-header">Upload Resumes</h1>
        <p className="page-sub">Upload candidate portfolios in PDF format for AI-powered screening</p>
      </div>

      <div className="space-y-6">
        {/* Step 1: Select Job */}
        <div className="card border-2 border-navy-100">
          <label className="label">1. Target Job Posting</label>
          <select 
            className="select"
            value={selectedJobId}
            onChange={(e) => setSelectedJobId(e.target.value)}
            disabled={uploadStatus !== 'idle'}
          >
            <option value="">Choose an active job...</option>
            {jobs.map(job => (
              <option key={job.id} value={job.id}>{job.title} ({job.experience_level})</option>
            ))}
          </select>
        </div>

        {/* Step 2: Upload Zone */}
        <div 
          {...getRootProps()} 
          className={`card border-2 border-dashed flex flex-col items-center justify-center py-12 transition-all cursor-pointer
            ${isDragActive ? 'border-navy-400 bg-navy-50' : 'border-navy-100 hover:border-navy-300'}
            ${uploadStatus !== 'idle' ? 'pointer-events-none opacity-50' : ''}`}
        >
          <input {...getInputProps()} />
          <div className="w-12 h-12 bg-white rounded-full shadow-card flex items-center justify-center mb-4">
            <Upload className="text-navy-600" size={20} />
          </div>
          <p className="text-navy-800 font-semibold text-lg">
            {isDragActive ? 'Drop files here' : 'Select or drag resumes'}
          </p>
          <p className="text-navy-400 text-sm mt-1 italic font-serif">Supported format: PDF only</p>
        </div>

        {/* File List */}
        {files.length > 0 && (
          <div className="card space-y-3">
             <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-bold text-navy-700 uppercase tracking-wider">Queue ({files.length})</h3>
                {uploadStatus === 'idle' && (
                    <button onClick={() => setFiles([])} className="text-xs text-red-500 hover:underline">Clear all</button>
                )}
             </div>
            {files.map(file => (
              <div key={file.id} className="flex items-center gap-3 p-3 bg-cream rounded-lg group animate-fade-in border border-navy-50">
                <div className="w-8 h-8 flex-shrink-0 bg-white rounded flex items-center justify-center border border-navy-100 italic font-bold text-navy-300">
                  <FileText size={14} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-navy-800 truncate">{file.name}</p>
                </div>
                {file.status === 'pending' && uploadStatus === 'idle' && (
                  <button onClick={() => removeFile(file.id)} className="text-navy-300 hover:text-red-500 p-1">
                    <X size={15} />
                  </button>
                )}
                {file.status === 'uploading' && <Loader2 size={15} className="text-navy-400 animate-spin" />}
                {file.status === 'done' && <CheckCircle2 size={15} className="text-emerald-500" />}
                {file.status === 'error' && <AlertCircle size={15} className="text-red-500" />}
              </div>
            ))}

            {uploadStatus === 'idle' && (
                <div className="pt-4 flex justify-end">
                  <button 
                    onClick={startProcessing}
                    className="btn-primary w-full sm:w-auto"
                  >
                    Begin AI Screening
                  </button>
                </div>
            )}
          </div>
        )}

        {/* Processing Overlay */}
        {uploadStatus !== 'idle' && (
            <div className="fixed inset-0 z-50 bg-navy-900/80 backdrop-blur-sm flex items-center justify-center p-6 animate-fade-in">
                <div className="bg-white rounded-2xl shadow-modal p-10 max-w-sm w-full text-center">
                    <div className="mb-6">
                        {uploadStatus === 'complete' ? (
                            <div className="w-16 h-16 bg-emerald-50 text-emerald-500 rounded-full flex items-center justify-center mx-auto mb-4 animate-scale-in">
                                <CheckCircle2 size={32} />
                            </div>
                        ) : (
                            <Loader2 size={48} className="text-navy-600 animate-spin mx-auto" />
                        )}
                    </div>
                    <h2 className="font-serif text-2xl font-bold text-navy-800 mb-2">
                        {uploadStatus === 'uploading' ? 'Extracting Text...' : 
                         uploadStatus === 'screening' ? 'Analyzing with AI...' : 
                         'Success!'}
                    </h2>
                    <p className="text-navy-400 text-sm mb-6 font-medium">
                        {uploadStatus === 'uploading' && `Processing document ${progress.current} of ${progress.total}`}
                        {uploadStatus === 'screening' && `Our recruiter AI is evaluating the candidates...`}
                        {uploadStatus === 'complete' && `Analysis complete. Redirecting to dashboard.`}
                    </p>
                    {uploadStatus === 'uploading' && (
                        <div className="w-full h-1.5 bg-navy-50 rounded-full overflow-hidden">
                            <div 
                                className="h-full bg-navy-700 transition-all duration-300" 
                                style={{ width: `${(progress.current / progress.total) * 100}%` }}
                            />
                        </div>
                    )}
                </div>
            </div>
        )}
      </div>
    </div>
  )
}
