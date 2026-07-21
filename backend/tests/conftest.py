import pytest
from httpx import AsyncClient, ASGITransport

@pytest.fixture
async def async_client():
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
