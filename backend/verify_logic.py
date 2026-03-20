import sys
import os
from unittest.mock import MagicMock

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# Mock dependencies that might fail
sys.modules['celery'] = MagicMock()
# sys.modules['fastapi'] = MagicMock() # Not needed for celery_tasks.py

try:
    from app.tasks.celery_tasks import run_screening_logic
    print("Successfully imported run_screening_logic")
    
    # Mock DB
    mock_db = MagicMock()
    
    # Mock Job
    mock_job = MagicMock()
    mock_job.id = 1
    mock_job.description = "We are looking for a Python developer with React experience."
    mock_job.required_skills = ["Python", "React"]
    mock_job.min_experience = 2
    mock_job.required_education = "Bachelor"
    
    # Mock crud.get_job_posting
    import app.db.crud as crud
    crud.get_job_posting = MagicMock(return_value=mock_job)
    crud.create_candidate = MagicMock(return_value=MagicMock(id=1))
    crud.create_screening_result = MagicMock()
    
    # Test Data
    sample_content = b"Candidate Name: John Doe. Skills: Python, React, SQL. Experience: 5 years. Education: Bachelor."
    
    # Run Logic
    result = run_screening_logic(job_id=1, filename="sample.txt", file_content=sample_content, candidate_email="john@example.com")
    
    print(f"Result: {result}")
    
    if result.get("status") == "success":
        print("Verification SUCCESS: Sync screening logic works!")
    else:
        print(f"Verification FAILED: {result.get('message')}")

except Exception as e:
    print(f"Import/Execution failed: {e}")
    import traceback
    traceback.print_exc()
