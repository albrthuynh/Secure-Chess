# create_access_token, create_refresh_token, decode_token
import os
import uuid
from datetime import datetime, timezone, timedelta
import jwt
from fastapi import HTTPException

JWT_ALGO = os.getenv("ALGO_SECRET")
JWT_SECRET = os.getenv("SECRET_JWT")
JWT_MINS = int(os.getenv("ACCESS_TOKEN_MINS"))
JWT_DAYS = int(os.getenv("ACCESS_TOKEN_DAYS"))


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(user_id: str) -> str:
    """
    1. create timestamp for the payload
    2. construct payload
    3. sign the payload as jwt
    """
    if not JWT_SECRET:
        raise RuntimeError("JWT Secret is missing")

    curr_datetime = _utc_now()
    # payload is represented as UTC or in this case number of seconds since 1970-01-01 00:00:00 UTC
    # reason behind this is because most JWT libraries expect numeric time stamps and safer comparisons across systems
    PAYLOAD = {
        "sub": user_id,
        "type": "access",
        "iat": int(curr_datetime.timestamp()),
        "exp": int((curr_datetime + timedelta(JWT_MINS)).timestamp()),
    }

    return jwt.encode(PAYLOAD, JWT_SECRET, algorithm=JWT_ALGO)


def create_refresh_token():
    """ """


def decode_token():
    """ """
