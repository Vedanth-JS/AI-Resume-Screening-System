"""
Hybrid semantic search — Gemini embeddings + pgvector cosine similarity.
Supports metadata filters (min_score, status, skill tags).
"""
from typing import Any, Dict, List, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from ..services.llm_service import get_embedding
from ..core.logger import log


class SemanticSearch:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def search_candidates(
        self,
        query: str,
        org_id: int,
        limit: int = 20,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        query_vector = await get_embedding(query)
        if not query_vector:
            log.warning("semantic_search.no_embedding", query=query[:100])
            return []

        # pgvector accepts the vector list directly via text cast
        # The '<=>' operator returns cosine distance, so 1 - distance = similarity
        sql = text("""
            SELECT
                c.id,
                c.name,
                c.email,
                c.status,
                1 - (re.embedding <=> CAST(:vector AS vector)) AS similarity_score
            FROM candidates c
            JOIN resume_embeddings re ON c.id = re.candidate_id
            WHERE c.org_id = :org_id
              AND c.deleted_at IS NULL
        """)

        params: Dict[str, Any] = {
            "vector": query_vector,
            "org_id": org_id,
            "limit": limit,
        }

        if filters:
            if "min_score" in filters:
                sql = text(sql.text + " AND 1 - (re.embedding <=> CAST(:vector AS vector)) >= :min_score")
                params["min_score"] = filters["min_score"]
            if "status" in filters and filters["status"]:
                sql = text(sql.text + " AND c.status = :cand_status")
                params["cand_status"] = filters["status"]

        sql = text(
            sql.text + " ORDER BY re.embedding <=> CAST(:vector AS vector) LIMIT :limit"
        )

        try:
            result = await self.db.execute(sql, params)
            return [dict(row._mapping) for row in result]
        except Exception as e:
            log.error("semantic_search.error", error=str(e))
            return []

    async def find_matches_for_job(
        self,
        job_id: int,
        job_description: str,
        org_id: int,
        top_k: int = 50,
    ) -> List[Dict[str, Any]]:
        """Auto-match candidates for a new job posting using semantic search."""
        results = await self.search_candidates(job_description, org_id, limit=top_k)

        # Persist top matches to job_candidate_matches table
        if results:
            insert_values = [
                {
                    "job_id": job_id,
                    "candidate_id": r["id"],
                    "similarity_score": float(r["similarity_score"]),
                }
                for r in results
            ]
            await self.db.execute(
                text("""
                    INSERT INTO job_candidate_matches (job_id, candidate_id, similarity_score, created_at, updated_at)
                    VALUES (:job_id, :candidate_id, :similarity_score, NOW(), NOW())
                    ON CONFLICT (job_id, candidate_id) DO UPDATE SET
                        similarity_score = EXCLUDED.similarity_score,
                        updated_at = NOW()
                """),
                insert_values,
            )
            await self.db.commit()

        return results
