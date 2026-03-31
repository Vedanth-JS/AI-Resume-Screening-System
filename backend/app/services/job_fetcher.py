import httpx
from typing import List, Dict

REMOTIVE_URL = "https://remotive.com/api/remote_jobs?limit=20"

def fetch_jobs() -> List[Dict]:
    """Fetch up to 20 remote jobs and map them to our JobPosting schema.
    Returns a list of dicts with keys: title, description, skills, min_exp, edu.
    """
    try:
        resp = httpx.get(REMOTIVE_URL, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
        jobs = data.get("jobs", [])[:20]
        normalized = []
        for job in jobs:
            normalized.append({
                "title": job.get("title", "Untitled"),
                "description": job.get("description", ""),
                "skills": job.get("tags", []),
                "min_exp": 0,
                "edu": job.get("category", "Not specified"),
            })
        return normalized
    except Exception as e:
        print(f"Job fetch error: {e}")
        return []
