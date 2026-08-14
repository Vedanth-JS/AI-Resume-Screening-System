"""
Embedding Pipeline — Gemini text-embedding-004 via pgvector.
Batch processing for indexing missing candidates.
"""
from typing import List, Optional
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.models import Candidate, ResumeEmbedding
from ..services.llm_service import get_embedding
from ..core.logger import log


class EmbeddingPipeline:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def embed_candidate(self, candidate_id: int, text: str) -> bool:
        """Generate 768-dim embedding and upsert in pgvector."""
        try:
            vector = await get_embedding(text[:8000])
            if not vector:
                log.warning("embed_candidate.no_vector", candidate_id=candidate_id)
                return False

            # Upsert via raw SQL to avoid SQLAlchemy ORM overhead
            await self.db.execute(
                text("""
                    INSERT INTO resume_embeddings (candidate_id, embedding, model_version, created_at, updated_at)
                    VALUES (:cid, :vec, 'gemini-embedding-2', NOW(), NOW())
                    ON CONFLICT (candidate_id) DO UPDATE SET
                        embedding = EXCLUDED.embedding,
                        model_version = EXCLUDED.model_version,
                        updated_at = NOW()
                """),
                {"cid": candidate_id, "vec": vector},
            )
            await self.db.commit()
            return True
        except Exception as e:
            await self.db.rollback()
            log.error("embed_candidate.error", candidate_id=candidate_id, error=str(e))
            return False

    async def batch_embed_missing(self, limit: int = 100):
        """
        Find candidates without embeddings and process them in bulk.
        Uses chunked indexing for memory efficiency.
        """
        rows = await self.db.execute(
            text("""
                SELECT c.id, c.raw_text
                FROM candidates c
                WHERE c.deleted_at IS NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM resume_embeddings re WHERE re.candidate_id = c.id
                  )
                LIMIT :limit
            """),
            {"limit": limit},
        )
        candidates = [(row[0], row[1]) for row in rows.fetchall()]
        if not candidates:
            return 0

        processed = 0
        for cid, text in candidates:
            if await self.embed_candidate(cid, text or ""):
                processed += 1

        log.info("batch_embed_missing.done", total=len(candidates), processed=processed)
        return processed
