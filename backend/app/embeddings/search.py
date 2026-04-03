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
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search: Vector similarity + metadata filters.
        """
        query_vector = await get_embedding(query)
        if not query_vector:
            log.warning("search_query_embedding_failed", query=query)
            return []

        # Base SQL for pgvector cosine similarity
        sql = """
            SELECT 
                c.id, 
                c.name, 
                c.email, 
                c.status,
                (1 - (re.embedding <=> :vector)) as similarity_score
            FROM candidates c
            JOIN resume_embeddings re ON c.id = re.candidate_id
            WHERE c.org_id = :org_id 
              AND c.deleted_at IS NULL
        """
        
        params = {
            "vector": str(query_vector), # pgvector expects string representation or cast
            "org_id": org_id,
            "limit": limit
        }

        # Apply additional filters if provided
        if filters:
            if "min_score" in filters:
                sql += " AND (1 - (re.embedding <=> :vector)) >= :min_score"
                params["min_score"] = filters["min_score"]
            
            # Additional metadata filters can be added here
            # e.g., status, specific skill tags in parsed_json

        sql += " ORDER BY re.embedding <=> :vector LIMIT :limit"

        try:
            result = await self.db.execute(text(sql), params)
            return [dict(row._mapping) for row in result]
        except Exception as e:
            log.error("semantic_search_error", error=str(e))
            return []

    async def find_matches_for_job(self, job_id: int, job_description: str, org_id: int, top_k: int = 50):
        """
        Auto-match candidates for a new job posting.
        """
        results = await self.search_candidates(job_description, org_id, limit=top_k)
        
        # Store results in job_candidate_matches
        # Implementation details for batch insertion...
        return results
