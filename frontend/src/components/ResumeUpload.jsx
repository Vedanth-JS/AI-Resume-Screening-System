import React, { useState } from 'react'
import { Upload, X, CheckCircle, FileText, Loader2, AlertCircle } from 'lucide-react'
import { candidateService } from '../services/api'

export function ResumeUpload({ jobId, onComplete }) {
  const [file, setFile] = useState(null)
  const [status, setStatus] = useState('idle') // idle, uploading, success, error
  const [error, setError] = useState('')

  const handleFile = (e) => {
    const selected = e.target.files[0]
    if (selected) {
      setFile(selected)
      setStatus('idle')
      setError('')
    }
  }

  const handleUpload = async () => {
    if (!file) return
    setStatus('uploading')

    try {
      const isZip = file.name.endsWith('.zip')
      const response = isZip 
        ? await candidateService.bulkUpload(jobId, file)
        : await candidateService.uploadResume(jobId, file)
      
      setStatus('success')
      if (onComplete) onComplete(response.data)
    } catch (err) {
      console.error(err)
      setStatus('error')
      setError(err.response?.data?.detail || 'Upload failed')
    }
  }

  return (
    <div className="glass rounded-2xl p-8 border border-white/5 space-y-6">
      <div className="flex items-center gap-3">
        <div className="p-2.5 bg-blue-500/10 rounded-xl">
          <Upload className="w-5 h-5 text-blue-500" />
        </div>
        <h3 className="text-xl font-bold">Screen New Resume</h3>
      </div>

      {!file ? (
        <label className="flex flex-col items-center justify-center h-48 border-2 border-dashed border-white/10 rounded-2xl cursor-pointer hover:border-blue-500/50 hover:bg-blue-500/5 transition-all">
          <div className="flex flex-col items-center text-center">
            <Upload className="w-10 h-10 text-slate-500 mb-3" />
            <p className="text-sm font-semibold text-slate-300">Choose file or drag here</p>
            <p className="text-xs text-slate-500 mt-1">PDF, TXT, or ZIP for bulk processing</p>
          </div>
          <input type="file" className="hidden" onChange={handleFile} accept=".pdf,.txt,.zip" />
        </label>
      ) : (
        <div className="bg-white/5 border border-white/10 rounded-2xl p-5 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-slate-800 rounded-xl border border-white/5">
              <FileText className="w-6 h-6 text-slate-400" />
            </div>
            <div>
              <p className="font-bold text-slate-100 truncate max-w-[200px]">{file.name}</p>
              <p className="text-xs text-slate-500">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
            </div>
          </div>
          {status !== 'uploading' && (
            <button onClick={() => setFile(null)} className="p-2 hover:bg-red-500/10 text-slate-500 hover:text-red-400 rounded-lg transition-all">
              <X className="w-5 h-5" />
            </button>
          )}
        </div>
      )}

      {status === 'idle' && file && (
        <button onClick={handleUpload} className="btn-primary w-full py-3.5">
          Process Candidate
        </button>
      )}

      {status === 'uploading' && (
        <div className="w-full h-12 flex items-center justify-center gap-3 bg-blue-500/10 rounded-xl text-blue-500 border border-blue-500/20 font-bold">
          <Loader2 className="w-5 h-5 animate-spin" />
          Analyzing Signals...
        </div>
      )}

      {status === 'success' && (
        <div className="bg-emerald-500/10 border border-emerald-500/20 p-4 rounded-xl flex items-center gap-3 text-emerald-500">
          <CheckCircle className="w-5 h-5" />
          <p className="font-bold">Analysis Complete! Data indexable.</p>
        </div>
      )}

      {status === 'error' && (
        <div className="bg-red-500/10 border border-red-500/20 p-4 rounded-xl flex items-center gap-3 text-red-500">
          <AlertCircle className="w-5 h-5" />
          <p className="font-bold">{error}</p>
        </div>
      )}
    </div>
  )
}
