"""Fetch remote job listings asynchronously from public APIs."""
import httpx
from typing import List, Dict
from ..core.logger import log

REMOTIVE_URL = "https://remotive.com/api/remote_jobs?limit=20"


async def fetch_jobs() -> List[Dict]:
    """Fetch up to 20 remote jobs and map them to our JobPosting schema."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(REMOTIVE_URL)
            resp.raise_for_status()
            data = resp.json()
            jobs = data.get("jobs", [])[:20]
            return [
                {
                    "title": j.get("title", "Untitled"),
                    "description": j.get("description", ""),
                    "skills": j.get("tags", []),
                    "min_exp": 0,
                    "edu": j.get("category", "Not specified"),
                }
                for j in jobs
            ]
    except Exception as e:
        log.warning("job_fetcher.error", error=str(e))
        return []
