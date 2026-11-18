import React, { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { chatService, extractErrorMessage } from "../services/api";
import {
  Send,
  Search,
  MessageSquare,
  AlertCircle,
  User,
  Mail,
  Briefcase,
  Sparkles,
  UploadCloud,
  SearchX,
} from "lucide-react";

interface ChatCandidateResult {
  id: number;
  name: string;
  email?: string;
  status?: string;
  similarity?: number;
  distance?: number;
  skills?: string[];
  experience_years?: number;
  matched_terms?: string[];
  raw_text?: string;
  document?: string;
}

const QUICK_QUERIES = [
  "python",
  "react typescript",
  "full stack",
  "docker kubernetes",
  "machine learning",
  "java spring",
];

export default function RAGChat() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [lastQuery, setLastQuery] = useState("");
  const [results, setResults] = useState<ChatCandidateResult[]>([]);
  const [totalPoolSize, setTotalPoolSize] = useState<number | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runSearch = useCallback(async (searchText: string) => {
    const trimmed = searchText.trim();
    if (!trimmed) return;

    setLoading(true);
    setError(null);
    setHasSearched(true);
    setLastQuery(trimmed);

    try {
      const res = await chatService.query(trimmed);

      if (res.data && res.data.success === false) {
        throw new Error(res.data.message || "Search request failed");
      }

      const searchResults: ChatCandidateResult[] = Array.isArray(res.data?.results)
        ? res.data.results
        : [];
      setResults(searchResults);
      setTotalPoolSize(
        typeof res.data?.total_pool_size === "number" ? res.data.total_pool_size : null
      );
    } catch (err: any) {
      console.error("Chat search error:", err);
      setResults([]);
      setError(extractErrorMessage(err, "Unable to complete search. Please try again."));
    } finally {
      setLoading(false);
    }
  }, []);

  const handleSearch = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      runSearch(query);
    },
    [query, runSearch]
  );

  const handleQuickQuery = (q: string) => {
    setQuery(q);
    runSearch(q);
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6 pb-20">
      {/* Header */}
      <div className="space-y-1">
        <h2 className="text-3xl font-bold font-display tracking-tight text-foreground flex items-center gap-2.5">
          <Sparkles className="w-6 h-6 text-primary" />
          AI Chat
        </h2>
        <p className="text-sm text-muted-foreground">
          Search your uploaded candidate pool using natural language, skills, or keywords
        </p>
      </div>

      {/* Search Bar */}
      <form onSubmit={handleSearch} className="flex gap-3">
        <div className="relative flex-1">
          <Search className="w-5 h-5 text-muted-foreground absolute left-4 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            placeholder="Find Python developers with 5+ years experience, React, FastAPI..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={loading}
            className="w-full h-12 pl-12 pr-4 bg-card border border-border rounded-2xl text-sm text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-primary focus:border-primary outline-none transition-all"
          />
        </div>
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="h-12 px-6 bg-primary hover:bg-primary/90 text-primary-foreground rounded-2xl font-bold text-sm flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-primary/20 transition-all"
          aria-label="Search candidates"
        >
          {loading ? (
            <div className="w-5 h-5 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
          ) : (
            <Send className="w-5 h-5" />
          )}
        </button>
      </form>

      {/* Quick Search Chips */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-semibold text-muted-foreground mr-1">Try:</span>
        {QUICK_QUERIES.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => handleQuickQuery(q)}
            disabled={loading}
            className="px-3 py-1 bg-card hover:bg-accent border border-border rounded-full text-xs font-medium text-muted-foreground hover:text-foreground transition-all"
          >
            {q}
          </button>
        ))}
      </div>

      {/* Loading State */}
      {loading && (
        <div className="bg-card border border-border rounded-3xl text-center py-14 px-6">
          <div className="w-8 h-8 border-2 border-primary/30 border-t-primary rounded-full animate-spin mx-auto mb-4" />
          <p className="text-sm font-semibold text-muted-foreground">
            Searching candidates for &ldquo;{lastQuery}&rdquo;...
          </p>
        </div>
      )}

      {/* Actual Backend / Network Error State */}
      {error && !loading && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-3xl text-center py-12 px-6 space-y-3">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto" />
          <h3 className="text-lg font-bold text-red-400">Search Error</h3>
          <p className="text-sm text-red-300 max-w-md mx-auto">{error}</p>
          <button
            type="button"
            onClick={() => runSearch(lastQuery || query)}
            className="mt-2 px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-200 border border-red-500/40 rounded-xl text-xs font-bold transition-all"
          >
            Retry Search
          </button>
        </div>
      )}

      {/* Initial State (Before Any Search) */}
      {!loading && !error && !hasSearched && (
        <div className="bg-card border border-border rounded-3xl text-center py-14 px-6 space-y-2">
          <MessageSquare className="w-12 h-12 text-muted-foreground/40 mx-auto mb-3" />
          <h3 className="text-lg font-bold text-foreground">Ready to Search</h3>
          <p className="text-sm text-muted-foreground max-w-md mx-auto">
            Enter a skill, role, or natural language query above to search candidates in your workspace.
          </p>
        </div>
      )}

      {/* Clean Empty State (Query Succeeded with 0 Matches) */}
      {!loading && !error && hasSearched && results.length === 0 && (
        <div className="bg-card border border-border rounded-3xl text-center py-14 px-6 space-y-4">
          <SearchX className="w-12 h-12 text-muted-foreground/50 mx-auto" />
          <div className="space-y-1.5">
            <h3 className="text-lg font-bold text-foreground">No Matching Candidates Found</h3>
            {totalPoolSize === 0 ? (
              <p className="text-sm text-muted-foreground max-w-md mx-auto">
                Your candidate pool currently has <strong className="text-foreground">0 uploaded resumes</strong>.
                Upload resumes in the Bulk Screening Lab first, then search them here.
              </p>
            ) : (
              <p className="text-sm text-muted-foreground max-w-md mx-auto">
                No candidates matched <strong className="text-foreground">&ldquo;{lastQuery}&rdquo;</strong>
                {totalPoolSize !== null ? ` across ${totalPoolSize} candidate${totalPoolSize === 1 ? "" : "s"} in your pool` : ""}.
                Try broader skills, synonyms, or a candidate name.
              </p>
            )}
          </div>
          {totalPoolSize === 0 && (
            <button
              type="button"
              onClick={() => navigate("/upload")}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-primary hover:bg-primary/90 text-primary-foreground rounded-xl text-xs font-bold shadow-lg shadow-primary/20 transition-all"
            >
              <UploadCloud className="w-4 h-4" />
              Go to Bulk Screening Lab
            </button>
          )}
        </div>
      )}

      {/* Results List */}
      {!loading && !error && results.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Found <span className="text-primary">{results.length}</span> matching candidate
              {results.length !== 1 ? "s" : ""} for &ldquo;{lastQuery}&rdquo;
              {totalPoolSize !== null ? ` (out of ${totalPoolSize} in pool)` : ""}
            </p>
          </div>

          <div className="space-y-3">
            {results.map((r, i) => {
              const matchPct =
                typeof r.similarity === "number"
                  ? Math.round(r.similarity * 100)
                  : Math.round((1 - (r.distance || 0)) * 100);
              const snippet = r.raw_text || r.document || "";

              return (
                <div
                  key={r.id || i}
                  className="bg-card border border-border hover:border-primary/40 rounded-2xl p-5 transition-all space-y-3"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-primary/15 border border-primary/30 flex items-center justify-center text-primary font-bold text-sm">
                        {(r.name || "C").charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <User className="w-3.5 h-3.5 text-muted-foreground" />
                          <p className="text-sm font-bold text-foreground">
                            {r.name || "Unknown Candidate"}
                          </p>
                          <span className="text-[11px] text-muted-foreground font-mono">
                            #{r.id}
                          </span>
                        </div>
                        <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground mt-0.5">
                          {r.email && (
                            <span className="flex items-center gap-1">
                              <Mail className="w-3 h-3" />
                              {r.email}
                            </span>
                          )}
                          {typeof r.experience_years === "number" && r.experience_years > 0 && (
                            <span className="flex items-center gap-1">
                              <Briefcase className="w-3 h-3" />
                              {r.experience_years} yrs exp
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    <span className="px-3 py-1 rounded-full text-xs font-bold bg-primary/15 text-primary border border-primary/30">
                      {matchPct}% match
                    </span>
                  </div>

                  {/* Matched Terms & Skills */}
                  {((r.matched_terms && r.matched_terms.length > 0) ||
                    (r.skills && r.skills.length > 0)) && (
                    <div className="flex flex-wrap gap-1.5">
                      {r.matched_terms?.map((term, idx) => (
                        <span
                          key={`m-${idx}`}
                          className="px-2.5 py-0.5 rounded-lg text-[11px] font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                        >
                          ✓ {term}
                        </span>
                      ))}
                      {r.skills
                        ?.filter(
                          (sk) =>
                            !r.matched_terms?.some((m) =>
                              m.toLowerCase().includes(sk.toLowerCase())
                            )
                        )
                        .slice(0, 6)
                        .map((sk, idx) => (
                          <span
                            key={`s-${idx}`}
                            className="px-2.5 py-0.5 rounded-lg text-[11px] font-medium bg-accent text-muted-foreground border border-border"
                          >
                            {sk}
                          </span>
                        ))}
                    </div>
                  )}

                  {snippet && (
                    <p className="text-xs text-muted-foreground leading-relaxed line-clamp-3">
                      {snippet}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
