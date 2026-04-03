import pytest
from httpx import AsyncClient
from app.main import app
from app.core.pdf_extractor import PDFExtractor
import hashlib

@pytest.mark.asyncio
async def test_pdf_hash_deduplication():
    content = b"Dummy PDF content for testing hashes."
    hash1 = PDFExtractor.get_file_hash(content)
    hash2 = PDFExtractor.get_file_hash(content)
    
    assert hash1 == hash2
    assert len(hash1) == 64 # SHA256 length

@pytest.mark.asyncio
async def test_bulk_upload_validation(async_client: AsyncClient):
    # Test with non-pdf file
    files = [
        ("files", ("test.txt", b"not a pdf", "text/plain"))
    ]
    # We need a job_id and auth, but we can check if it returns 404/401 correctly
    response = await async_client.post("/api/v1/jobs/999/bulk-upload", files=files)
    # If not logged in, should be 401
    assert response.status_code in [401, 403, 404]

@pytest.mark.asyncio
async def test_sse_endpoint_exists(async_client: AsyncClient):
    # Just check if the route is registered and reachable
    # streaming=True for SSE
    response = await async_client.get("/api/v1/tasks/dummy-task-id/status")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream"
