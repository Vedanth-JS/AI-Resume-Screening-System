import React, { useState, useCallback } from "react";
import { Card, Button, Input } from "./ui";
import { Badge } from "./ui/Badge";
import { chatService } from "../services/api";
import { Send, Search, MessageSquare } from "lucide-react";

export default function RAGChat() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const handleSearch = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    try {
      const res = await chatService.query(query);
      setResults(res.data.results || []);
    } catch {
      setResults([]);
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
          />
        </div>
        <Button type="submit" loading={loading} size="lg">
          <Send className="w-5 h-5" />
        </Button>
      </form>

      {results.length === 0 && !loading && (
        <Card className="text-center py-12">
          <MessageSquare className="w-16 h-16 text-black/20 mx-auto mb-4" />
          <h3 className="text-xl font-black mb-2">Ready to Search</h3>
          <p className="text-black/60 font-semibold">Type a query above to search the vector database</p>
        </Card>
      )}

      <div className="space-y-4">
        {results.map((r, i) => (
          <Card key={i} className="stagger-item" style={{ animationDelay: `${i * 80}ms` }}>
            <div className="flex items-center gap-4 mb-3">
              <Badge variant="info">{Math.round((1 - r.distance) * 100)}% match</Badge>
              <Badge variant="neutral">#{r.id}</Badge>
            </div>
            <p className="text-sm font-semibold text-black/80 leading-relaxed line-clamp-3">…{r.document}…</p>
          </Card>
        ))}
      </div>
    </div>
  );
}
