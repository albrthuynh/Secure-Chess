import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from .matchmaking_helpers import GameDetails, create_match
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
    # this creates a protected route b/c we ensure only authenticated users can make a request
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

    # To be secure and efficient, let's immediately try and make the match after
    # the player enters the matchmaking queue. But if we have < 2 players, just keep queued.
    if position < 2:
        return {
            "queued": True,
            "request_id": payload["request_id"],
            "position": position,
            "queue_key": queue_key,
        }

    try:
        players = await redis_client.lpop(queue_key, 2)
    except Exception:
        raise HTTPException(status_code=503, detail="Matchmaking queue unavailable")

    if not players or len(players) < 2:
        # This is a defensive requeue
        # All that means is that if there is a race condition would could have made it partially pop (<2 players)
        # We need to make sure we push back the players just in case there was an partial pop
        if players:
            for player in players:
                await redis_client.lpush(queue_key, player)

        return {
            "queued": True,
            "request_id": payload["request_id"],
            "position": await redis_client.llen(queue_key),
            "queue_key": queue_key,
        }

    p1_raw = players[0].decode() if isinstance(players[0], bytes) else players[0]
    p2_raw = players[1].decode() if isinstance(players[1], bytes) else players[1]
    p1 = json.loads(p1_raw)
    p2 = json.loads(p2_raw)

    game_details = GameDetails(
        user_id_white=p1["user_id"],
        user_id_black=p2["user_id"],
        time_control=body.time_control,
        increment=body.increment,
    )

    match = create_match(game_details)

    return {
        "queued": False,
        "match_found": True,
        "match_id": match["match_id"],
        "white_user_id": match["white_user_id"],
        "black_user_id": match["black_user_id"],
        "time_control": match["time_control"],
        "increment": match["increment"],
    }
