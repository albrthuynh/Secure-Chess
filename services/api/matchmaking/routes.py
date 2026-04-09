import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from utils.user_helpers import get_user_id
from utils.redis_client import get_redis_client

router = APIRouter(prefix="/matchmaking", tags=["/matchmaking"])


class MatchmakingRequestBody(BaseModel):
    time_control: str
    increment: int = Field(ge=0)


@router.post("/request", status_code=202)
async def create_request(body: MatchmakingRequestBody, request: Request):
    """
    Creates the request in the Redis DB to establish a session
    """
    redis_client = await get_redis_client()
    user_id = get_user_id(request)

    # create the redis keys
    queue_key = f"mm:queue:{body.time_control}:{body.increment}"

    payload = {
        "request_id": str(uuid.uuid4()),
        "user_id": user_id,
        "time_control": body.time_control,
        "increment": body.increment,
        "created_at": datetime.now(
            timezone.utc
        ).isoformat(),  # the iso format looks like,'YYYY-MM-DD HH:MM:SS.mmmmmm'
    }

    try:
        await redis_client.rpush(queue_key, json.dumps(payload))
        position = await redis_client.llen(queue_key)
    except Exception:
        raise HTTPException(status_code=503, detail="Matchmaking queue unavailable")

    return {
        "queued": True,
        "request_id": payload["request_id"],
        "position": position,
        "queue_key": queue_key,
    }
