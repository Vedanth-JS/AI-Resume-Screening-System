"""
RAG Service — Hybrid semantic (pgvector) + deterministic keyword/synonym candidate search.
Works seamlessly on both PostgreSQL/pgvector and SQLite without requiring an external LLM key.
"""
import re
from typing import List, Dict, Any, Set
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession
from ..services.llm_service import get_embedding
from ..models.models import Candidate, ResumeEmbedding
from ..core.logger import log


_STOP_WORDS: Set[str] = {
    "a", "an", "and", "are", "as", "at", "be", "by", "candidate", "candidates",
    "dev", "developer", "developers", "do", "engineer", "engineers", "exp",
    "experience", "experienced", "find", "for", "from", "get", "good", "has",
    "have", "having", "i", "in", "is", "know", "knowing", "knowledge", "list",
    "looking", "me", "need", "of", "on", "or", "people", "person", "profiles",
    "resume", "resumes", "search", "show", "skilled", "skills", "some", "strong",
    "that", "the", "to", "want", "who", "with", "work", "working", "year", "years",
    "yr", "yrs", "plus", "senior", "junior", "mid",
}

_SYNONYM_GROUPS: List[Set[str]] = [
    {"python", "py", "fastapi", "django", "flask"},
    {"javascript", "js", "ecmascript"},
    {"typescript", "ts"},
    {"react", "reactjs", "react.js", "nextjs", "next.js"},
    {"node", "nodejs", "node.js", "express", "expressjs"},
    {"postgres", "postgresql", "psql"},
    {"sql", "mysql", "postgresql", "sqlite", "mssql", "rdbms"},
    {"nosql", "mongodb", "mongo", "dynamodb", "cassandra", "redis"},
    {"kubernetes", "k8s", "helm"},
    {"docker", "containers", "containerization"},
    {"aws", "amazon web services", "ec2", "s3", "lambda"},
    {"gcp", "google cloud", "bigquery"},
    {"azure", "microsoft azure"},
    {"ml", "machine learning", "scikit-learn", "sklearn", "pytorch", "tensorflow"},
    {"ai", "artificial intelligence", "llm", "genai", "nlp", "rag", "langchain"},
    {"java", "spring", "spring boot", "springboot", "j2ee"},
    {"csharp", "c#", ".net", "dotnet", "asp.net"},
    {"cpp", "c++"},
    {"golang", "go"},
    {"devops", "ci/cd", "cicd", "jenkins", "github actions", "terraform", "ansible"},
    {"frontend", "front-end", "ui", "html", "css", "tailwind", "react", "angular", "vue"},
    {"backend", "back-end", "api", "rest", "microservices", "graphql"},
    {"fullstack", "full-stack", "full stack"},
    {"data science", "data scientist", "pandas", "numpy", "statistics"},
    {"data analyst", "analytics", "power bi", "tableau", "excel"},
    {"cybersecurity", "security", "infosec", "pentest", "owasp"},
    {"qa", "testing", "selenium", "cypress", "playwright", "pytest"},
    {"ui/ux", "ux", "figma", "wireframing", "prototyping"},
]


def _extract_query_terms(query: str) -> List[str]:
    """Extract meaningful tokens and multi-word tech phrases from a natural language query."""
    q_lower = query.lower().strip()
    if not q_lower:
        return []

    terms: List[str] = []

    # Check multi-word phrases first
    multi_word_phrases = [
        "machine learning", "deep learning", "data science", "data scientist",
        "data analyst", "full stack", "full-stack", "spring boot", "power bi",
        "react.js", "node.js", "next.js", "asp.net", "github actions",
        "amazon web services", "google cloud", "microsoft azure",
        "system design", "artificial intelligence", "natural language",
    ]
    for phrase in multi_word_phrases:
        if phrase in q_lower:
            terms.append(phrase)

    # Tokenize keeping +, #, ., /, - inside tech identifiers (e.g. c++, c#, ci/cd, ui/ux)
    raw_tokens = re.findall(r"[a-z0-9][a-z0-9+#./-]*", q_lower)
    for tok in raw_tokens:
        clean_tok = tok.strip(".,;:-/")
        if not clean_tok:
            continue
        # Skip pure numbers like "5" (handled separately as experience filter)
        if clean_tok.isdigit():
            continue
        if clean_tok in _STOP_WORDS:
            continue
        if clean_tok not in terms:
            terms.append(clean_tok)

    # If everything was filtered as stop words (e.g. user searched "developer" or "senior"),
    # fall back to all raw tokens >= 2 chars so we still search meaningfully.
    if not terms:
        terms = [t.strip(".,;:-/") for t in raw_tokens if len(t.strip(".,;:-/")) >= 2]

    return terms


def _get_related_synonyms(term: str) -> Set[str]:
    """Return related/synonym terms for soft semantic expansion."""
    related: Set[str] = set()
    for group in _SYNONYM_GROUPS:
        if term in group:
            related.update(group)
    related.discard(term)
    return related


def _extract_min_years(query: str) -> float:
    """Extract optional minimum experience constraint like '5+ years' or '3 yrs'."""
    m = re.search(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)", query.lower())
    return float(m.group(1)) if m else 0.0


def _term_in_text(term: str, haystack: str) -> bool:
    """Match tech tokens with boundary awareness (avoiding 'go' matching 'good')."""
    if len(term) <= 2 or term in {"c", "go", "r", "ai", "ml", "qa", "ui", "ux", "js", "ts", "py"}:
        return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", haystack) is not None
    return term in haystack


class RAGService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def index_candidate(self, candidate: Candidate):
        """Generate and store embedding for a candidate resume."""
        parsed = candidate.parsed_json if isinstance(candidate.parsed_json, dict) else {}
        skills = parsed.get("skills") or parsed.get("technical_skills") or []
        content = (
            f"Name: {candidate.name}\n"
            f"Skills: {', '.join(str(s) for s in skills)}\n"
            f"{(candidate.raw_text or '')[:2000]}"
        )
        vector = await get_embedding(content)
        if not vector:
            log.warning("rag_index.no_embedding", candidate_id=candidate.id)
            return

        existing = await self.db.execute(
            text("SELECT id FROM resume_embeddings WHERE candidate_id = :cid"),
            {"cid": candidate.id},
        )
        vector_str = str(vector)
        if existing.scalar():
            await self.db.execute(
                text(
                    "UPDATE resume_embeddings SET embedding = :vec, model_version = :mv, updated_at = CURRENT_TIMESTAMP "
                    "WHERE candidate_id = :cid"
                ),
                {
                    "vec": vector_str,
                    "mv": "gemini-embedding-2",
                    "cid": candidate.id,
                },
            )
        else:
            await self.db.execute(
                text(
                    "INSERT INTO resume_embeddings (candidate_id, embedding, model_version, created_at, updated_at) "
                    "VALUES (:cid, :vec, :mv, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                ),
                {
                    "cid": candidate.id,
                    "vec": vector_str,
                    "mv": "gemini-embedding-2",
                },
            )
        await self.db.commit()

    async def _pgvector_search(
        self, query: str, org_id: int, limit: int
    ) -> Dict[int, Dict[str, Any]]:
        """Run pgvector semantic similarity search when running on PostgreSQL with embeddings."""
        try:
            bind = self.db.get_bind()
            dialect_name = bind.dialect.name if bind is not None else ""
        except Exception:
            dialect_name = ""

        if "postgres" not in dialect_name.lower():
            return {}

        query_vector = await get_embedding(query)
        if not query_vector:
            return {}

        sql = text("""
            SELECT c.id, c.name, c.email, c.status, c.raw_text, c.parsed_json,
                   (1 - (re.embedding <=> :vector)) as similarity
            FROM candidates c
            JOIN resume_embeddings re ON c.id = re.candidate_id
            WHERE c.org_id = :org_id
              AND c.deleted_at IS NULL
            ORDER BY re.embedding <=> :vector
            LIMIT :limit
        """)
        try:
            result = await self.db.execute(
                sql,
                {"vector": str(query_vector), "org_id": org_id, "limit": limit},
            )
            out: Dict[int, Dict[str, Any]] = {}
            for row in result:
                item = dict(row._mapping)
                sim = float(item.get("similarity") or 0.0)
                if sim >= 0.35:
                    out[item["id"]] = item
            return out
        except Exception as e:
            log.warning("rag_pgvector_fallback_to_keyword", error=str(e))
            return {}

    async def search_candidates(
        self, query: str, org_id: int, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Hybrid candidate search scoped to `org_id`:
        1. Runs pgvector semantic search if available on PostgreSQL.
        2. Runs deterministic + synonym-expanded keyword search across Candidate records
           (name, email, parsed skills/experience/projects, and raw resume text).
        3. Merges and ranks results by relevance score (0.0 - 1.0).
        """
        q_clean = (query or "").strip()
        if not q_clean:
            return []

        # 1. Optional pgvector semantic matches
        pg_matches = await self._pgvector_search(q_clean, org_id, limit)

        # 2. Fetch active candidates scoped to user's organization
        stmt = (
            select(Candidate)
            .where(Candidate.org_id == org_id, Candidate.deleted_at.is_(None))
            .order_by(Candidate.id.desc())
        )
        res = await self.db.execute(stmt)
        candidates = res.scalars().all()

        terms = _extract_query_terms(q_clean)
        min_years = _extract_min_years(q_clean)
        q_lower = q_clean.lower()

        scored_by_id: Dict[int, Dict[str, Any]] = {}

        for cand in candidates:
            parsed = cand.parsed_json if isinstance(cand.parsed_json, dict) else {}
            skills_raw = (
                parsed.get("technical_skills")
                or parsed.get("skills")
                or []
            )
            if isinstance(skills_raw, str):
                skills_list = [s.strip() for s in skills_raw.split(",") if s.strip()]
            elif isinstance(skills_raw, list):
                skills_list = [str(s).strip() for s in skills_raw if str(s).strip()]
            else:
                skills_list = []

            exp_years = (
                parsed.get("work_experience_years")
                or parsed.get("experience_years")
                or parsed.get("total_experience_years")
                or 0
            )
            try:
                exp_years_num = float(exp_years)
            except (TypeError, ValueError):
                exp_years_num = 0.0

            name_text = (cand.name or "").lower()
            email_text = (cand.email or "").lower()
            skills_text = " ".join(s.lower() for s in skills_list)
            raw_text = (cand.raw_text or "").lower()
            parsed_blob = f"{name_text} {email_text} {skills_text} {str(parsed).lower()} {raw_text}"

            matched_terms: List[str] = []
            exact_hits = 0
            skill_hits = 0
            synonym_hits = 0

            for term in terms:
                if _term_in_text(term, skills_text) or _term_in_text(term, name_text) or _term_in_text(term, email_text):
                    exact_hits += 1
                    skill_hits += 1
                    matched_terms.append(term)
                elif _term_in_text(term, parsed_blob):
                    exact_hits += 1
                    matched_terms.append(term)
                else:
                    # Check synonym expansion
                    syns = _get_related_synonyms(term)
                    syn_found = next((s for s in syns if _term_in_text(s, parsed_blob)), None)
                    if syn_found:
                        synonym_hits += 1
                        matched_terms.append(f"{term} (~{syn_found})")

            full_phrase_hit = q_lower in parsed_blob

            # Check if pgvector matched this candidate
            pg_item = pg_matches.get(cand.id)
            pg_sim = float(pg_item.get("similarity", 0.0)) if pg_item else 0.0

            if exact_hits == 0 and synonym_hits == 0 and not full_phrase_hit and pg_sim < 0.35:
                continue

            # Calculate normalized similarity score (0.0 - 0.99)
            denom = max(len(terms), 1)
            kw_coverage = (exact_hits + 0.65 * synonym_hits) / denom
            kw_score = 0.45 + 0.40 * min(kw_coverage, 1.0)
            if skill_hits > 0:
                kw_score += 0.07 * min(skill_hits / denom, 1.0)
            if full_phrase_hit:
                kw_score += 0.06
            if min_years > 0:
                if exp_years_num >= min_years:
                    kw_score += 0.05
                else:
                    kw_score -= 0.12

            kw_score = max(0.25, min(0.99, kw_score))
            final_sim = max(pg_sim, kw_score) if (exact_hits > 0 or synonym_hits > 0 or full_phrase_hit) else pg_sim

            # Build readable snippet around first matched term
            snippet = (cand.raw_text or "").strip()
            if snippet and matched_terms:
                first_term = matched_terms[0].split(" (~")[0]
                idx = snippet.lower().find(first_term.lower())
                if idx > 80:
                    snippet = "..." + snippet[max(0, idx - 60): idx + 240]
                else:
                    snippet = snippet[:300]
            else:
                snippet = snippet[:300]

            scored_by_id[cand.id] = {
                "id": cand.id,
                "name": cand.name or "Candidate",
                "email": cand.email or "",
                "status": cand.status or "SCREENED",
                "similarity": round(final_sim, 4),
                "skills": skills_list[:10],
                "experience_years": exp_years_num,
                "matched_terms": matched_terms,
                "raw_text": snippet,
            }

        ranked = sorted(
            scored_by_id.values(),
            key=lambda x: (x["similarity"], len(x.get("matched_terms", []))),
            reverse=True,
        )
        return ranked[:limit]
