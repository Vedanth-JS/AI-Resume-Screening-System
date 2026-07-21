import React, { useState, useCallback } from "react";
import { Card, Button, Input } from "./ui";
import { Badge } from "./ui/Badge";
import { chatService } from "../services/api";
import { Send, Search, MessageSquare, AlertCircle, User, Mail } from "lucide-react";

export default function RAGChat() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    
    setLoading(true);
    setError(null);
    setResults([]);
    
    try {
      const res = await chatService.query(query);
      
      // Check for success flag in response
      if (res.data && res.data.success === false) {
        throw new Error(res.data.message || 'Search failed');
      }
      
      const searchResults = res.data?.results || [];
      setResults(searchResults);
      
      if (searchResults.length === 0) {
        setError('No candidates found matching your query');
      }
    } catch (err: any) {
      console.error('Chat search error:', err);
      
      let errorMessage = 'Search failed';
      
      if (err.response) {
        if (err.response.data?.detail) {
          errorMessage = err.response.data.detail;
        } else if (err.response.data?.message) {
          errorMessage = err.response.data.message;
        } else if (typeof err.response.data === 'string') {
          errorMessage = err.response.data;
        } else {
          errorMessage = `Server error: ${err.response.status}`;
        }
      } else if (err.message) {
        errorMessage = err.message;
      } else if (err.request) {
        errorMessage = 'Network error - please check your connection';
      }
      
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [query]);

  return (
    <div className="space-y-8">
      <div className="page-header">
        <div>
          <h2 className="page-title">AI Chat</h2>
          <p className="text-lg font-bold text-black/60 mt-1">Search your candidate pool with natural language</p>
        </div>
      </div>

      <form onSubmit={handleSearch} className="flex gap-3">
        <div className="flex-1">
          <Input
            placeholder="Find Python developers with 5+ years fintech experience..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            icon={<Search className="w-5 h-5" />}
            disabled={loading}
          />
        </div>
        <Button type="submit" loading={loading} size="lg" disabled={!query.trim()}>
          <Send className="w-5 h-5" />
        </Button>
      </form>

      {loading && (
        <Card className="text-center py-12">
          <div className="w-8 h-8 border-2 border-black/20 border-t-black rounded-full animate-spin mx-auto mb-4" />
          <p className="text-black/60 font-semibold">Searching candidates...</p>
        </Card>
      )}

      {error && !loading && (
        <Card className="text-center py-12 border-red-200 bg-red-50">
          <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h3 className="text-xl font-black mb-2 text-red-700">Search Error</h3>
          <p className="text-red-600 font-semibold">{error}</p>
        </Card>
      )}

      {!loading && !error && results.length === 0 && (
        <Card className="text-center py-12">
          <MessageSquare className="w-16 h-16 text-black/20 mx-auto mb-4" />
          <h3 className="text-xl font-black mb-2">Ready to Search</h3>
          <p className="text-black/60 font-semibold">Type a query above to search the vector database</p>
        </Card>
      )}

      {!loading && results.length > 0 && (
        <>
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm font-semibold text-black/60">
              Found {results.length} candidate{results.length !== 1 ? 's' : ''}
            </p>
          </div>
          <div className="space-y-4">
            {results.map((r, i) => (
              <Card key={r.id || i} className="stagger-item" style={{ animationDelay: `${i * 80}ms` }}>
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-4">
                    <Badge variant="info">
                      {r.similarity ? Math.round(r.similarity * 100) : Math.round((1 - (r.distance || 0)) * 100)}% match
                    </Badge>
                    <Badge variant="neutral">#{r.id}</Badge>
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <User className="w-4 h-4 text-black/60" />
                    <p className="text-sm font-bold text-black">{r.name || 'Unknown'}</p>
                  </div>
                  {r.email && (
                    <div className="flex items-center gap-2">
                      <Mail className="w-4 h-4 text-black/60" />
                      <p className="text-sm text-black/70">{r.email}</p>
                    </div>
                  )}
                  {r.raw_text && (
                    <p className="text-sm font-semibold text-black/80 leading-relaxed line-clamp-3 mt-2">
                      {r.raw_text.substring(0, 200)}...
                    </p>
                  )}
                  {r.document && (
                    <p className="text-sm font-semibold text-black/80 leading-relaxed line-clamp-3 mt-2">
                      {r.document.substring(0, 200)}...
                    </p>
                  )}
                </div>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
