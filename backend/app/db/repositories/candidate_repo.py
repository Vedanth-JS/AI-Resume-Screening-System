from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .base import BaseRepository
from ...models.models import Candidate

class CandidateRepository(BaseRepository[Candidate]):
    def __init__(self, db: AsyncSession):
        super().__init__(Candidate, db)

    async def get_by_email(self, email: str, org_id: int) -> Optional[Candidate]:
        stmt = select(self.model).where(self.model.email == email, self.model.org_id == org_id, self.model.deleted_at == None)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def list_by_org(self, org_id: int, skip: int = 0, limit: int = 100) -> List[Candidate]:
        result = await self.db.execute(
            select(self.model).filter(self.model.org_id == org_id, self.model.deleted_at == None).offset(skip).limit(limit)
        )
        return result.scalars().all()
