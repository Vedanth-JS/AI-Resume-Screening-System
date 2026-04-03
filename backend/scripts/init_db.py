import asyncio
from app.db.database import AsyncSessionLocal
from app.models import models
from app.core.auth import get_password_hash
from sqlalchemy import select

async def init_db():
    async with AsyncSessionLocal() as db:
        # 1. Create Organization
        stmt = select(models.Organization).where(models.Organization.slug == "default")
        res = await db.execute(stmt)
        org = res.scalars().first()
        
        if not org:
            org = models.Organization(name="Default Org", slug="default", plan_tier="enterprise")
            db.add(org)
            await db.flush()
            print(f"Created Organization: {org.name}")
        
        # 2. Create Roles
        for role_name in models.RoleEnum:
            stmt = select(models.Role).where(models.Role.name == role_name)
            res = await db.execute(stmt)
            if not res.scalars().first():
                role = models.Role(name=role_name, permissions={"all": True})
                db.add(role)
                print(f"Created Role: {role_name}")
        
        # 3. Create Admin User
        stmt = select(models.User).where(models.User.email == "admin@ats.com")
        res = await db.execute(stmt)
        if not res.scalars().first():
            user = models.User(
                org_id=org.id,
                email="admin@ats.com",
                password_hash=get_password_hash("admin123")
            )
            db.add(user)
            print(f"Created Admin User: admin@ats.com / admin123")
            
        await db.commit()
        print("Database initialized successfully!")

if __name__ == "__main__":
    asyncio.run(init_db())
