"""
Load Testing — Locust-based performance validation.
Target: 100K concurrent users, <300ms P95 response time, 1M resumes.

Run: locust -f tests/locustfile.py --host=http://localhost:8000 --users=1000 --spawn-rate=100
"""
from locust import HttpUser, task, between, events
import random
import json
import time
from typing import Optional


# ─── Test Data ────────────────────────────────────────────────────────────────

SAMPLE_RESUME_TEXT = """
John Doe | john@example.com | +1-555-0123 | linkedin.com/in/johndoe
EDUCATION: B.S. Computer Science, Stanford University, 2018-2022
EXPERIENCE:
- Senior Backend Engineer, TechCorp, Jan 2021 - Present
  Built REST APIs handling 10k req/s using Python, FastAPI, PostgreSQL
- Junior Developer, StartupX, Jun 2018 - Dec 2020
  Developed e-commerce platform with Django and React
SKILLS: Python, FastAPI, PostgreSQL, Docker, Kubernetes, AWS, React
PROJECTS: Distributed task queue system, Real-time analytics dashboard
CERTIFICATIONS: AWS Solutions Architect, CKAD
"""

SAMPLE_JD = """
We are looking for a Senior Python Engineer with 5+ years of experience.
Required skills: Python, FastAPI, PostgreSQL, Docker, Kubernetes, AWS
Nice to have: React, TypeScript, CI/CD experience
"""

REGISTER_DATA = {
    "email": "loadtest@test.com",
    "password": "Str0ng!Passw0rd",
    "organization_name": "LoadTest Corp",
    "organization_slug": "loadtest-corp",
}

JOB_DATA = {
    "title": "Senior Python Engineer",
    "description": "Build scalable APIs with Python and FastAPI. Experience with PostgreSQL required.",
    "required_skills": ["python", "fastapi", "postgresql"],
    "min_experience": 3,
    "required_education": "Bachelor's",
}


class AIATSUser(HttpUser):
    """Simulates a recruiter using the AI ATS platform."""

    wait_time = between(1, 5)
    token: Optional[str] = None
    headers: dict = {}
    org_id: Optional[int] = None

    def on_start(self):
        """Authenticate before running tests."""
        # Register
        resp = self.client.post(
            "/api/auth/register",
            json={
                "email": f"loadtest_{random.randint(1, 99999)}@test.com",
                "password": "Str0ng!Passw0rd",
                "organization_name": "LoadTest Corp",
                "organization_slug": f"loadtest-{random.randint(1, 99999)}",
            },
        )

        # Login
        resp = self.client.post(
            "/api/auth/token",
            data={"username": "loadtest@test.com", "password": "Str0ng!Passw0rd"},
        )
        if resp.status_code == 200:
            data = resp.json()
            self.token = data.get("access_token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = None

    @task(10)  # Highest frequency — dashboard view
    def get_analytics_overview(self):
        if self.token:
            self.client.get("/api/analytics/overview", headers=self.headers)

    @task(8)
    def list_jobs(self):
        if self.token:
            self.client.get("/api/jobs", headers=self.headers)

    @task(5)
    def create_job(self):
        if self.token:
            self.client.post("/api/jobs", json=JOB_DATA, headers=self.headers)

    @task(3)
    def list_candidates(self):
        if self.token:
            self.client.get("/api/candidates", headers=self.headers)

    @task(2)
    def get_metrics(self):
        if self.token:
            self.client.get("/api/metrics", headers=self.headers)

    @task(1)  # Lowest frequency — most expensive operation
    def upload_resume(self):
        """Simulate resume upload with screening."""
        if self.token and self.org_id:
            # First create a job for screening
            job_resp = self.client.post("/api/jobs", json=JOB_DATA, headers=self.headers)
            if job_resp.status_code == 200:
                job_id = job_resp.json()["id"]
                # Upload a resume
                files = {"file": ("resume.pdf", SAMPLE_RESUME_TEXT.encode(), "application/pdf")}
                data = {"job_id": str(job_id)}
                self.client.post(
                    "/api/resume/upload",
                    files=files,
                    data=data,
                    headers={**self.headers, "Content-Type": None},
                )

    @task(3)
    def health_check(self):
        """Basic health check (no auth required)."""
        self.client.get("/api/health")

    @task(1)
    def chat_query(self):
        """Natural language candidate search."""
        if self.token:
            self.client.post("/api/chat?query=python+developers+with+aws", headers=self.headers)


# ─── Custom Events — Track Latency ────────────────────────────────────────────

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Track P95 and error rate."""
    if exception:
        events.request.fire(
            request_type=request_type,
            name=name,
            response_time=response_time,
            response_length=0,
            exception=exception,
        )


# ─── Seed Data for Load Tests ─────────────────────────────────────────────────

def create_seed_data():
    """Helper to pre-populate test data before load testing."""
    import requests

    base_url = "http://localhost:8000"
    print("Seeding load test data...")

    # Register and get token
    reg = requests.post(f"{base_url}/api/auth/register", json=REGISTER_DATA)
    login = requests.post(
        f"{base_url}/api/auth/token",
        data={"username": REGISTER_DATA["email"], "password": REGISTER_DATA["password"]},
    )
    if login.status_code != 200:
        print("Failed to authenticate for seeding")
        return

    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create 50 jobs
    for i in range(50):
        job = {**JOB_DATA, "title": f"Software Engineer {i}"}
        resp = requests.post(f"{base_url}/api/jobs", json=job, headers=headers)
        if resp.status_code != 200:
            print(f"Failed to create job {i}: {resp.status_code}")

    print("Seed data creation complete.")


if __name__ == "__main__":
    create_seed_data()
