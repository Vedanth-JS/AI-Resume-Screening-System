from typing import List, Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from .base import BaseRepository
from ...models.models import Application

class ApplicationRepository(BaseRepository[Application]):
    def __init__(self, db: AsyncSession):
        super().__init__(Application, db)

    async def list_by_job(self, job_id: int, org_id: int, skip: int = 0, limit: int = 100) -> List[Application]:
        result = await self.db.execute(
            select(self.model)
            .filter(self.model.job_id == job_id, self.model.org_id == org_id, self.model.deleted_at == None)
            .order_by(desc(self.model.score))
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    
    async def get_by_job_candidate(self, job_id: int, candidate_id: int, org_id: int) -> Optional[Application]:
        result = await self.db.execute(
            select(self.model)
            .filter(self.model.job_id == job_id, self.model.candidate_id == candidate_id, self.model.org_id == org_id, self.model.deleted_at == None)
        )
        return result.scalars().first()
