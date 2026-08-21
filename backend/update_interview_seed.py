import asyncio
import logging
from sqlalchemy import select, update
from app.db.database import AsyncSessionLocal, async_engine
from app.models import models
from app.models.ats_models import PipelineStageEnum, InterviewType, Interview

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def seed_interview():
    async with AsyncSessionLocal() as db:
        try:
            logger.info("Updating seed data for interview page...")
            
            # 1. Update Candidate 1 name to 'Arjun Sharma'
            cand = await db.get(models.Candidate, 1)
            if cand:
                cand.name = "Arjun Sharma"
                db.add(cand)
                logger.info("Updated Candidate 1 name to Arjun Sharma.")
            
            # 2. Delete existing kit/interview with id=1 if exists
            kit = await db.get(models.InterviewKit, 1)
            if kit:
                await db.delete(kit)
                logger.info("Deleted existing interview kit 1.")
            
            # 3. Create InterviewKit 1
            questions = [
                {
                    "id": 1,
                    "type": "TECHNICAL",
                    "question": "How would you handle global state in a complex React application with high mutation frequency?",
                    "expected": ["Context API vs Redux", "Performance optimization", "State normalization"]
                },
                {
                    "id": 2,
                    "type": "BEHAVIORAL",
                    "question": "Tell me about a time you had a conflict with a designer over a specific UI implementation.",
                    "expected": ["Communication", "Compromise", "User-first logic"]
                },
                {
                    "id": 3,
                    "type": "SITUATIONAL",
                    "question": "A critical production bug is discovered on a Friday at 5 PM. How do you triage it?",
                    "expected": ["Isolation", "Communication", "Quick-fix vs robust fix"]
                }
            ]
            
            new_kit = models.InterviewKit(
                id=1,
                job_id=1,
                candidate_id=1,
                focus_areas=["React", "State Management", "Conflict Resolution", "Incident Management"],
                difficulty="SENIOR",
                questions=questions
            )
            db.add(new_kit)
            await db.flush()
            logger.info("Created InterviewKit with id=1.")

            # 4. Create Interview 1
            stmt = select(Interview).where(Interview.id == 1)
            existing_interview = (await db.execute(stmt)).scalars().first()
            if existing_interview:
                await db.delete(existing_interview)
                logger.info("Deleted existing interview 1.")
                
            new_interview = Interview(
                id=1,
                org_id=1,
                application_id=1,
                interview_type=InterviewType.TECHNICAL,
                scheduled_at=datetime_now_utc(),
                duration_minutes=60,
                location="Zoom Meeting",
                interviewers=["recruiter@example.com"],
                status="scheduled",
                feedback={},
                kit_id=1
            )
            db.add(new_interview)
            
            await db.commit()
            logger.info("Successfully updated interview seed data!")

        except Exception as e:
            logger.error("Error during seeding: %s", e)
            await db.rollback()
            raise
        finally:
            await db.close()

def datetime_now_utc():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)

if __name__ == "__main__":
    asyncio.run(seed_interview())
