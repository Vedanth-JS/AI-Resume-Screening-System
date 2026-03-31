from app.db.database import SessionLocal, Base, engine
from app.db import crud
from app.api.auth import get_password_hash
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_database():
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # 1. Create a default Recruiter User
        logger.info("Creating default recruiter...")
        # admin123hashed = get_password_hash("admin123")
        user = crud.create_user(db, email="admin@ai-ats.com", password_hash=get_password_hash("admin123"), role="admin")
        
        # 2. Create Sample Job Postings
    # Add external jobs from Remotive API
    from app.services.job_fetcher import fetch_jobs
    external_jobs = fetch_jobs()
    for ext_job in external_jobs:
        crud.create_job_posting(
            db,
            title=ext_job["title"],
            description=ext_job["description"],
            skills=ext_job["skills"],
            min_exp=ext_job["min_exp"],
            edu=ext_job["edu"],
            user_id=user.id,
        )
    # Existing static jobs remain as fallback
        logger.info("Seeding job postings...")
        
        jobs = [
            {
                "title": "Senior Full Stack Engineer",
                "description": "We are looking for a high-performing guru to lead our scale-up team. Must be an aggressive problem solver with strong Ninja-level React skills. Ivy League background preferred.",
                "skills": ["React", "FastAPI", "PostgreSQL", "Docker", "AWS"],
                "min_exp": 5,
                "edu": "Bachelor's in Computer Science"
            },
            {
                "title": "AI/ML Product Manager",
                "description": "Lead the strategy for our next-gen AI resume screening tools. Bridge the gap between engineering and business to deliver state-of-the-art candidate matching.",
                "skills": ["Product Strategy", "Machine Learning", "Agile", "User Research"],
                "min_exp": 4,
                "edu": "MBA or equivalent experience"
            },
            {
                "title": "Frontend Developer (Junior)",
                "description": "Kickstart your career by building beautiful, glassmorphic UIs for our hiring platform. Learn from the best and grow your career with us.",
                "skills": ["HTML", "CSS", "Tailwind CSS", "JavaScript"],
                "min_exp": 1,
                "edu": "Self-taught or Degree"
            }
        ]
        
        for job_data in jobs:
            crud.create_job_posting(
                db, 
                title=job_data["title"], 
                description=job_data["description"], 
                skills=job_data["skills"], 
                min_exp=job_data["min_exp"], 
                edu=job_data["edu"], 
                user_id=user.id
            )
            
        logger.info("Successfully seeded database with %d jobs.", len(jobs))
        
    except Exception as e:
        logger.error("Error seeding database: %s", e)
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
