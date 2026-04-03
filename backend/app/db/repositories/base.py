from typing import Generic, TypeVar, Type, Optional, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from datetime import datetime, timezone
from ...db.database import Base

T = TypeVar("T", bound=Base)

class BaseRepository(Generic[T]):
    def __init__(self, model: Type[T], db: AsyncSession):
        self.model = model
        self.db = db

    async def get(self, id: Any, org_id: Optional[int] = None) -> Optional[T]:
        stmt = select(self.model).where(self.model.id == id)
        if org_id:
            stmt = stmt.where(self.model.org_id == org_id)
        if hasattr(self.model, "deleted_at"):
            stmt = stmt.where(self.model.deleted_at == None)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def list(self, org_id: Optional[int] = None, skip: int = 0, limit: int = 100) -> List[T]:
        stmt = select(self.model).offset(skip).limit(limit)
        if org_id:
            stmt = stmt.where(self.model.org_id == org_id)
        if hasattr(self.model, "deleted_at"):
            stmt = stmt.where(self.model.deleted_at == None)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def create(self, **kwargs) -> T:
        instance = self.model(**kwargs)
        self.db.add(instance)
        await self.db.flush()
        return instance

    async def update(self, id: Any, org_id: Optional[int] = None, **kwargs) -> Optional[T]:
        stmt = update(self.model).where(self.model.id == id)
        if org_id:
            stmt = stmt.where(self.model.org_id == org_id)
        stmt = stmt.values(**kwargs).returning(self.model)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def delete(self, id: Any, org_id: Optional[int] = None, soft: bool = True) -> bool:
        if soft and hasattr(self.model, "deleted_at"):
            stmt = update(self.model).where(self.model.id == id)
            if org_id:
                stmt = stmt.where(self.model.org_id == org_id)
            stmt = stmt.values(deleted_at=datetime.now(timezone.utc))
            result = await self.db.execute(stmt)
            return result.rowcount > 0
        else:
            stmt = delete(self.model).where(self.model.id == id)
            if org_id:
                stmt = stmt.where(self.model.org_id == org_id)
            result = await self.db.execute(stmt)
            return result.rowcount > 0
