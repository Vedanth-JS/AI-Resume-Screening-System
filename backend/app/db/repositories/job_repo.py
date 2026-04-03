from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .base import BaseRepository
from ...models.models import JobPosting

class JobRepository(BaseRepository[JobPosting]):
    def __init__(self, db: AsyncSession):
        super().__init__(JobPosting, db)

    async def list_by_org(self, org_id: int, skip: int = 0, limit: int = 100) -> List[JobPosting]:
        result = await self.db.execute(
            select(self.model).filter(self.model.org_id == org_id, self.model.deleted_at == None).offset(skip).limit(limit)
        )
        return result.scalars().all()
    
    async def get_by_id_org(self, id: int, org_id: int) -> Optional[JobPosting]:
        result = await self.db.execute(
            select(self.model).filter(self.model.id == id, self.model.org_id == org_id, self.model.deleted_at == None)
        )
        return result.scalars().first()
