import React, { useState } from 'react'
import { MessageSquare, Send, Search, Users, Database } from 'lucide-react'
import { chatService } from '../services/api'

export function RAGChat() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!query.trim()) return
    setLoading(true)

    try {
      const response = await chatService.query(query)
      setResults(response.data.results || [])
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-right-4 duration-700">
      <header className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Candidate Intelligence</h2>
          <p className="text-slate-400 mt-1">Search your candidate pool using natural language.</p>
        </div>
        <div className="p-3 bg-blue-500/10 rounded-2xl border border-blue-500/20">
           <Database className="w-6 h-6 text-blue-500" />
        </div>
      </header>

      {/* Search Input Box */}
      <form onSubmit={handleSearch} className="relative group">
        <input 
          type="text" 
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g., Find Python developers with 5+ years experience in Fintech..."
          className="w-full bg-white/5 border border-white/10 rounded-2xl px-6 py-5 pr-16 text-lg focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all group-hover:border-white/20"
        />
        <button 
          disabled={loading}
          className="absolute right-4 top-1/2 -translate-y-1/2 p-3 bg-blue-600 hover:bg-blue-500 text-white rounded-xl transition-all shadow-lg hover:shadow-blue-500/30 disabled:opacity-50"
        >
          {loading ? <div className="w-5 h-5 border-2 border-white/20 border-t-white rounded-full animate-spin" /> : <Send className="w-5 h-5" />}
        </button>
      </form>

      {/* Results Section */}
      <div className="space-y-6">
        <h3 className="text-lg font-bold flex items-center gap-3">
          <Search className="w-5 h-5 text-slate-500" />
          Detected Matches ({results.length})
        </h3>

        {results.length === 0 && !loading && (
          <div className="glass rounded-3xl p-12 flex flex-col items-center text-center">
            <div className="p-5 bg-white/5 rounded-full mb-4">
               <MessageSquare className="w-10 h-10 text-slate-600" />
            </div>
            <h4 className="text-slate-400 font-bold uppercase tracking-widest text-xs mb-2">Systems Ready</h4>
            <p className="text-slate-500 max-w-sm">Type a search query above to query the Vector Database for matched candidates.</p>
          </div>
        )}

        {results.map((result, idx) => (
          <div key={idx} className="glass-card flex flex-col md:flex-row gap-8 border border-white/5 hover:border-blue-500/20">
             <div className="flex-1 space-y-4">
               <div className="flex items-center gap-4">
                  <div className="p-3 bg-blue-500/10 rounded-xl">
                     <Users className="w-6 h-6 text-blue-500" />
                  </div>
                  <div>
                    <h4 className="font-bold text-lg text-slate-100 italic">"Relevant Candidate Fragment"</h4>
                    <p className="text-xs text-slate-500 uppercase font-bold tracking-tighter">Match Confidence: {Math.round((1 - result.distance) * 100)}%</p>
                  </div>
               </div>
               <p className="text-sm text-slate-400 italic leading-relaxed bg-white/5 p-4 rounded-xl border border-white/5">
                 ...{result.document}...
               </p>
             </div>
             <div className="w-full md:w-48 flex flex-col justify-center border-l border-white/5 pl-8">
                <button className="btn-secondary text-sm w-full py-2.5">
                  View Profile
                </button>
                <p className="text-[10px] text-slate-600 mt-4 text-center leading-tight">
                  Source Resume ID: {result.id}
                </p>
             </div>
          </div>
        ))}
      </div>
    </div>
  )
}
