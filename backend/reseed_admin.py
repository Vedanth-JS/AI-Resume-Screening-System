import asyncio
from sqlalchemy import select, delete
from app.db.database import AsyncSessionLocal, async_engine, Base
from app.models.models import Organization, Role, User, RoleEnum
from app.api.auth import hash_password

async def reseed_admin():
    async with AsyncSessionLocal() as db:
        try:
            print("👤 Resetting Admin User...")
            
            # 1. Get or Create Org
            stmt = select(Organization).where(Organization.slug == "default-org")
            res = await db.execute(stmt)
            org = res.scalars().first()
            if not org:
                org = Organization(name="AI Recruitment Corp", slug="default-org", plan_tier="enterprise")
                db.add(org)
                await db.flush()

            # 2. Get Admin Role
            stmt = select(Role).where(Role.name == RoleEnum.ADMIN)
            res = await db.execute(stmt)
            admin_role = res.scalars().first()
            if not admin_role:
                admin_role = Role(name=RoleEnum.ADMIN, permissions={})
                db.add(admin_role)
                await db.flush()

            # 3. Force Re-create Admin
            stmt = delete(User).where(User.email == "admin@ai-ats.com")
            await db.execute(stmt)
            
            admin_email = "admin@ai-ats.com"
            admin_pass = "admin123"
            
            admin = User(
                email=admin_email,
                password_hash=hash_password(admin_pass),
                org_id=org.id
            )
            admin.roles.append(admin_role)
            db.add(admin)
            
            await db.commit()
            print(f"✅ Admin user '{admin_email}' reset with password '{admin_pass}'")

        except Exception as e:
            print(f"❌ Error: {e}")
            await db.rollback()
        finally:
            await db.close()

if __name__ == "__main__":
    asyncio.run(reseed_admin())
