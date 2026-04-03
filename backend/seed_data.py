import asyncio
import logging
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.database import AsyncSessionLocal, async_engine, Base
from app.models.models import Organization, Role, User, RoleEnum, JobPosting
from app.api.auth import hash_password
from app.services.job_fetcher import fetch_jobs

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def seed_database():
    async with AsyncSessionLocal() as db:
        try:
            logger.info("Starting database seeding...")

            # 1. Create Roles if they don't exist
            logger.info("Seeding roles...")
            for role_enum in RoleEnum:
                stmt = select(Role).where(Role.name == role_enum)
                res = await db.execute(stmt)
                if not res.scalars().first():
                    new_role = Role(name=role_enum, permissions={})
                    db.add(new_role)
            await db.commit() # Commit roles first to ensure they have IDs
            
            # Re-open session or just continue
            await db.begin() # Start a new transaction if needed, but 'async with' handles it? 
            # Actually, with expire_on_commit=False, we can continue.
            
            # 2. Create Default Organization
            logger.info("Checking for default organization...")
            stmt = select(Organization).where(Organization.slug == "default-org")
            res = await db.execute(stmt)
            org = res.scalars().first()
            if not org:
                org = Organization(
                    name="AI Recruitment Corp",
                    slug="default-org",
                    plan_tier="enterprise"
                )
                db.add(org)
                await db.flush()
                logger.info("Created default organization: %s", org.name)
            else:
                logger.info("Default organization already exists.")

            # 3. Create Default Admin User
            logger.info("Checking for default admin user...")
            # Use selectinload to avoid lazy loading issues with roles
            stmt = select(User).where(User.email == "admin@ai-ats.com").options(selectinload(User.roles))
            res = await db.execute(stmt)
            admin = res.scalars().first()
            
            if not admin:
                # Fetch the admin role to assign it
                stmt = select(Role).where(Role.name == RoleEnum.ADMIN)
                res = await db.execute(stmt)
                admin_role = res.scalars().first()
                
                admin = User(
                    email="admin@ai-ats.com",
                    password_hash=hash_password("admin123"),
                    org_id=org.id
                )
                if admin_role:
                    admin.roles.append(admin_role)
                
                db.add(admin)
                await db.flush()
                logger.info("Created default admin user: %s", admin.email)
            else:
                logger.info("Default admin user already exists.")

            # 4. Seed Job Postings
            logger.info("Checking for existing job postings...")
            stmt = select(JobPosting).where(JobPosting.org_id == org.id)
            res = await db.execute(stmt)
            if not res.scalars().first():
                logger.info("Fetching jobs from Remotive API...")
                # Note: job_fetcher uses sync httpx, which is OK in this script but not ideal for high concurrency
                external_jobs = fetch_jobs()
                
                if not external_jobs:
                    logger.warning("Remotive API returned no jobs or failed, using static fallback...")
                    external_jobs = [
                        {
                            "title": "Senior Full Stack Engineer",
                            "description": "Lead our scale-up team. Ninja-level React skills required.",
                            "skills": ["React", "FastAPI", "PostgreSQL", "Docker"],
                            "min_exp": 5,
                            "edu": "Bachelor's in CS"
                        },
                        {
                            "title": "AI/ML Product Manager",
                            "description": "Lead strategy for next-gen AI tools.",
                            "skills": ["Product Strategy", "ML", "Agile"],
                            "min_exp": 4,
                            "edu": "MBA"
                        }
                    ]

                for job_data in external_jobs:
                    new_job = JobPosting(
                        org_id=org.id,
                        title=job_data["title"],
                        description=job_data["description"][:1000] if job_data["description"] else "No description",
                        required_skills=job_data["skills"] if isinstance(job_data["skills"], list) else [job_data["skills"]],
                        min_experience=job_data.get("min_exp", 0),
                        status="active"
                    )
                    db.add(new_job)
                
                logger.info("Successfully seeded %d job postings.", len(external_jobs))
            else:
                logger.info("Job postings already exist.")

            await db.commit()
            logger.info("Database seeding completed successfully!")

        except Exception as e:
            logger.error("Error during seeding: %s", e)
            await db.rollback()
            raise
        finally:
            await db.close()

if __name__ == "__main__":
    asyncio.run(seed_database())
