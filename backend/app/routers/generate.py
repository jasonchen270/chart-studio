"""Server-Sent Events endpoint for the prompt → code flow.

Why SSE not WebSockets: traffic is one-directional (server → client) and we
want to play nicely with HTTP/2 and Vercel's edge runtime. WebSockets would
add complexity without buying anything.
"""
import json

from fastapi import APIRouter
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.services.auth import User
from app.services.claude_loop import stream_generate

router = APIRouter()


class GenerateRequest(BaseModel):
    csv_hash: str
    prompt: str


@router.post("/generate")
async def generate(req: GenerateRequest, user: User) -> EventSourceResponse:
    async def event_source():
        async for evt in stream_generate(req.prompt, req.csv_hash):
            yield {"event": evt["type"], "data": json.dumps(evt)}

    return EventSourceResponse(event_source())
