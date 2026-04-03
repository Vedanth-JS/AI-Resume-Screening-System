import os
import json
import asyncio
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
import redis

router = APIRouter()
r = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))

@router.get("/{task_id}/status")
async def get_task_status_sse(task_id: str, request: Request):
    """
    Streaming SSE endpoint for real-time progress of a single task.
    """
    async def event_generator():
        while True:
            # Check for client disconnect
            if await request.is_disconnected():
                break
                
            data = r.get(f"task_status:{task_id}")
            if data:
                yield {
                    "event": "message",
                    "data": data.decode()
                }
                status_obj = json.loads(data)
                # Statuses like SUCCESS or FAILED terminate the stream
                if status_obj.get("status") in ["SUCCESS", "FAILED", "COMPLETED"]:
                    break
            else:
                # If no data yet, wait
                yield {
                    "event": "ping",
                    "data": "waiting"
                }
                
            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
