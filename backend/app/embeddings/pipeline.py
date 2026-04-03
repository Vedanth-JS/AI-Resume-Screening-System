from typing import Any, List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.models import Candidate, ResumeEmbedding
from ..services.llm_service import get_embedding
from ..core.logger import log

class EmbeddingPipeline:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def embed_candidate(self, candidate_id: int, text: str) -> bool:
        """
        Embeds a single candidate's resume and stores it in pgvector.
        """
        try:
            # text-embedding-004 returns 768 dimensions
            vector = await get_embedding(text[:8000])
            if not vector:
                return False
                
            # Check if embedding already exists
            existing = await self.db.execute(
                select(ResumeEmbedding).where(ResumeEmbedding.candidate_id == candidate_id)
            )
            embedding_obj = existing.scalar_one_or_none()
            
            if embedding_obj:
                embedding_obj.embedding = vector
                embedding_obj.model_version = "text-embedding-004"
            else:
                embedding_obj = ResumeEmbedding(
                    candidate_id=candidate_id,
                    embedding=vector,
                    model_version="text-embedding-004"
                )
                self.db.add(embedding_obj)
            
            await self.db.commit()
            return True
        except Exception as e:
            await self.db.rollback()
            log.error("embedding_pipeline_error", candidate_id=candidate_id, error=str(e))
            return False

    async def batch_embed_missing(self, limit: int = 100):
        """Find candidates missing embeddings and process them."""
        # Implementation for bulk processing
        pass
