"""
RAG Service — semantic search over pgvector embeddings.
"""
import json as _json
from typing import List, Dict, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from ..services.llm_service import get_embedding
from ..models.models import Candidate, ResumeEmbedding
from ..core.logger import log


class RAGService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def index_candidate(self, candidate: Candidate):
        """Generate and store embedding for a candidate resume."""
        skills = candidate.parsed_json.get("skills", []) if isinstance(candidate.parsed_json, dict) else []
        content = (
            f"Name: {candidate.name}\n"
            f"Skills: {', '.join(skills)}\n"
            f"{candidate.raw_text[:2000]}"
        )
        vector = await get_embedding(content)
        if not vector:
            log.warning("rag_index.no_embedding", candidate_id=candidate.id)
            return

        existing = await self.db.execute(
            text("SELECT id FROM resume_embeddings WHERE candidate_id = :cid"),
            {"cid": candidate.id},
        )
        if existing.scalar():
            await self.db.execute(
                text(
                    "UPDATE resume_embeddings SET embedding = :vec, model_version = :mv "
                    "WHERE candidate_id = :cid"
                ),
                {
                    "vec": vector,
                    "mv": "text-embedding-004",
                    "cid": candidate.id,
                },
            )
        else:
            await self.db.execute(
                text(
                    "INSERT INTO resume_embeddings (candidate_id, embedding, model_version) "
                    "VALUES (:cid, :vec, :mv)"
                ),
                {
                    "cid": candidate.id,
                    "vec": vector,
                    "mv": "text-embedding-004",
                },
            )
        await self.db.commit()

    async def search_candidates(
        self, query: str, org_id: int, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Perform semantic search using pgvector cosine distance."""
        query_vector = await get_embedding(query)
        if not query_vector:
            return []

        sql = text("""
            SELECT c.id, c.name, c.email, c.status,
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
                {"vector": query_vector, "org_id": org_id, "limit": limit},
            )
            return [dict(row._mapping) for row in result]
        except Exception as e:
            log.error("rag_search.error", error=str(e))
            return []
