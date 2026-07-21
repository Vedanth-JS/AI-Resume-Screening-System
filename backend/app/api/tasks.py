import os
import json
import asyncio
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
import redis.asyncio as aioredis
from ..core.config import settings

router = APIRouter()
r = aioredis.from_url(settings.REDIS_URL)

@router.get("/{task_id}/status")
async def get_task_status_sse(task_id: str, request: Request):
    """
    Streaming SSE endpoint for real-time progress of a single task.
    """
    async def event_generator():
        if await request.is_disconnected():
            return

        try:
            data = await r.get(f"task_status:{task_id}")
        except Exception:
            data = None

        if data:
            yield f"event: message\ndata: {data.decode()}\n\n"
        else:
            yield "event: ping\ndata: waiting\n\n"

    response = StreamingResponse(event_generator())
    response.headers["content-type"] = "text/event-stream"
    return response
