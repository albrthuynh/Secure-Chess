# create_access_token, create_refresh_token, decode_token
import os
import uuid
from datetime import datetime, timezone, timedelta
import jwt
from jwt.exceptions import InvalidTokenError
from fastapi import HTTPException

JWT_ALGO = os.getenv("JWT_ALGORITHM", "HS256")
JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_MINS = int(os.getenv("ACCESS_TOKEN_MINS", "15"))
JWT_DAYS = int(os.getenv("REFRESH_TOKEN_DAYS", "7"))


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
        "iat": int(curr_datetime.timestamp()),  # issued_at
        "exp": int((curr_datetime + timedelta(minutes=JWT_MINS)).timestamp()),  # expired on
    }

    return jwt.encode(PAYLOAD, JWT_SECRET, algorithm=JWT_ALGO)


def create_refresh_token(user_id: str) -> tuple[str, str, datetime]:
    """
    1. create id for refresh token
    2. set expiration date for token
    """
    if not JWT_SECRET:
        raise RuntimeError("JWT Secret is missing")
    if not JWT_ALGO:
        raise RuntimeError("JWT ALGO is missing")

    token_id = str(uuid.uuid4())
    curr_datetime = _utc_now()
    expiration_date = curr_datetime + timedelta(days=JWT_DAYS)

    PAYLOAD = {
        "jti": token_id,  # JWT id
        "sub": user_id,
        "iat": int(curr_datetime.timestamp()),
        "exp": int(expiration_date.timestamp()),
        "type": "refresh",
    }

    encoded_token = jwt.encode(PAYLOAD, JWT_SECRET, algorithm=JWT_ALGO)
    return (encoded_token, token_id, expiration_date)


def decode_token(token: str, token_type: str) -> dict:
    """
    1. know the secret
    2. use that secret to decode the token
    """

    if not JWT_SECRET:
        raise RuntimeError("JWT Secret is missing")
    if not JWT_ALGO:
        raise RuntimeError("JWT ALGO is missing")

    try:
        decoded_token = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token Expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid Token")

    if token_type != decoded_token.get("type"):
        raise HTTPException(401, "Unexpected token type")

    return decoded_token
