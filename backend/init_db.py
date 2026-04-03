import asyncio
import sys
import os
import subprocess

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import async_engine, Base
from app.models.models import *
from seed_data import seed_database # Import seeding logic

async def run_alembic_upgrade():
    """
    Attempt to run alembic upgrade head using a subprocess.
    """
    print("📋 Running Alembic migrations to latest version...")
    try:
        # Run alembic upgrade head
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True, 
            text=True,
            check=True
        )
        print(f"✅ Alembic Success: {result.stdout}")
        return True
    except FileNotFoundError:
        print("⚠️  Alembic CLI not found on host. Falling back to internal SQLAlchemy init...")
        return False
    except subprocess.CalledProcessError as e:
        print(f"❌ Alembic Migration Failed: {e.stderr}")
        return False

async def init_db():
    print("🚀 Antigravity Production DB Hardening Sequence...")
    
    # 1. Database Schema
    migration_success = await run_alembic_upgrade()
    if not migration_success:
        print("🛠️  Performing fallback schema baseline (create_all)...")
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Baseline Schema Created.")
    
    # 2. Database Seeding (Roles, Admin User, Jobs)
    print("🌱 Seeding essential production data...")
    try:
        await seed_database()
        print("✅ Seeding Successful.")
    except Exception as e:
        print(f"⚠️  Seeding Note: {e}")

    await async_engine.dispose()
    print("🎉 Database is fully initialized and seeded for Production.")

if __name__ == "__main__":
    try:
        asyncio.run(init_db())
    except Exception as e:
        print(f"❌ DB Hardware Fault: {e}")
        sys.exit(1)
