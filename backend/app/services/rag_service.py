from typing import List, Dict, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from ..services.llm_service import get_embedding
from ..models.models import Candidate, ResumeEmbedding
import json

class RAGService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def index_candidate(self, candidate: Candidate):
        """Generate and store embedding for a candidate resume."""
        # Use a combination of parsed JSON and raw text for better indexing
        content_to_embed = f"Name: {candidate.name}\nSkills: {', '.join(candidate.parsed_json.get('skills', []))}\n{candidate.raw_text[:2000]}"
        vector = await get_embedding(content_to_embed)
        
        if not vector:
            return
            
        embedding = ResumeEmbedding(
            candidate_id=candidate.id,
            embedding=vector, # In Postgres with pgvector, this would be a list
            model_version="text-embedding-004"
        )
        self.db.add(embedding)
        await self.db.flush()

    async def search_candidates(self, query: str, org_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """Perform semantic search using pgvector similarity."""
        query_vector = await get_embedding(query)
        if not query_vector:
            return []

        # pgvector similarity search: <=> is cosine distance
        # We join with candidates to filter by org_id
        sql = text("""
            SELECT c.id, c.name, c.email, (1 - (re.embedding <=> :vector)) as similarity
            FROM candidates c
            JOIN resume_embeddings re ON c.id = re.candidate_id
            WHERE c.org_id = :org_id AND c.deleted_at IS NULL
            ORDER BY re.embedding <=> :vector
            LIMIT :limit
        """)
        
        # Note: If pgvector extension is NOT installed, this will fail.
        # Ensure 'CREATE EXTENSION vector' was run in migration.
        
        result = await self.db.execute(sql, {"vector": json.dumps(query_vector), "org_id": org_id, "limit": limit})
        return [dict(row._mapping) for row in result]
