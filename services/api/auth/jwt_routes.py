import hashlib
import os

import psycopg
from fastapi import APIRouter, HTTPException, Request
from passlib.context import CryptContext
from psycopg.errors import UniqueViolation
from pydantic import BaseModel, EmailStr
from .jwt_helpers import create_access_token, create_refresh_token, decode_token
from middleware.rate_limit import rate_limit

router = APIRouter(prefix="/auth", tags=["/auth"])

# I need this line explained
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DATABASE_URL = os.getenv("DATABASE_URL")


class SignupBody(BaseModel):
    username: str
    email: EmailStr
    password: str


class SignInBody(BaseModel):
    username: str
    password: str


class RefreshBody(BaseModel):
    refresh_token: str


class LogoutBody(BaseModel):
    refresh_token: str


@router.get("/health")
async def health():
    return {"ok": True}


@router.post("/sign-up", status_code=201)
@rate_limit(max_requests=3, window_seconds=3600, identifier_type="ip", key_prefix="sign-up")
async def signup(body: SignupBody, request: Request):
    # make sure there is a password policy here
    if len(body.password) < 6:
        raise HTTPException(
            status_code=400, detail="Password must be at least longer than 6 characters"
        )

    password_hash = pwd_context.hash(body.password)

    # connecting to the db, and inserting the user row
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # the reason we use %s is to protect from sql injection
                cur.execute(
                    """
                        INSERT INTO users (username, email, password_hash)
                        VALUES (%s, %s, %s)
                        RETURNING user_id, username, email, created_at
                    """,
                    (body.username, body.email, password_hash),
                )
                row = cur.fetchone()
            conn.commit()
    except UniqueViolation:
        raise HTTPException(
            status_code=409, detail="Username or email already exists")

    return {
        "user_id": str(row[0]),
        "username": row[1],
        "email": row[2],
        "created_at": row[3].isoformat(),
    }


@router.post("/sign-in", status_code=200)
@rate_limit(max_requests=5, window_seconds=900, identifier_type="ip", key_prefix="sign-in")
async def signin(body: SignInBody, request: Request):
    if not body.username or not body.password:
        raise HTTPException(status_code=400, detail="Missing information")

    # the reason we don't need to use a try/except statement here is bc we are doing a SELECT statement
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                    SELECT user_id, username, password_hash
                    FROM users
                    WHERE username = %s
                """,
                (body.username,),
            )
            row = cur.fetchone()

    if row is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_id, row_username, row_password_hash = row

    if not pwd_context.verify(body.password, row_password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(str(user_id))
    refresh_token, refresh_token_id, expiration_date = create_refresh_token(
        str(user_id)
    )
    refresh_token_hash = hashlib.sha256(
        refresh_token.encode("utf-8")).hexdigest()
    # insert refresh token into db to make sure that resources can be accessed securely once a user is logged in
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                        INSERT INTO refresh_tokens(token_id, user_id, token_hash, expiration_date)
                        VALUES (%s, %s, %s, %s)
                    """,
                    (refresh_token_id, user_id, refresh_token_hash, expiration_date),
                )
                conn.commit()
    except psycopg.Error:
        raise HTTPException(
            status_code=500, detail="Failed to persist refresh token")

    return {
        "Sign In Successful": True,
        "user_id": str(user_id),
        "username": row_username,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh")
@rate_limit(max_requests=20, window_seconds=60, identifier_type="user_id", key_prefix="refresh")
async def refresh(body: RefreshBody, request: Request):
    decoded_token = decode_token(body.refresh_token, token_type="refresh")

    sub = decoded_token["sub"]
    jti = decoded_token["jti"]

    # rehash the token in order to find the old one
    rehashed_token = hashlib.sha256(
        body.refresh_token.encode("utf-8")).hexdigest()

    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                        SELECT user_id
                        FROM refresh_tokens
                        WHERE token_hash = %s
                        AND revoked_date IS NULL
                        AND expiration_date > NOW()
                    """,
                    (rehashed_token,),
                )
                row = cur.fetchone()

                if row is None:
                    raise HTTPException(
                        status_code=401, detail="Invalid or expired refresh token"
                    )

                # revoking the token to establish the "refresh effect"
                cur.execute(
                    "UPDATE refresh_tokens SET revoked_date = NOW() WHERE token_hash = %s",
                    (rehashed_token,),
                )

                # issuing new token
                new_access_token = create_access_token(sub)
                new_refresh_token, new_jti, new_exp_date = create_refresh_token(
                    sub)
                new_refresh_token_hash = hashlib.sha256(
                    new_refresh_token.encode("utf-8")
                ).hexdigest()

                cur.execute(
                    """
                        INSERT INTO refresh_tokens(token_id, user_id, token_hash, expiration_date)
                        VALUES (%s, %s, %s, %s)
                    """,
                    (new_jti, sub, new_refresh_token_hash, new_exp_date),
                )
            conn.commit()
    except HTTPException:
        raise
    except psycopg.Error:
        raise HTTPException(status_code=500, detail="Failed to refresh token")

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


@router.post("/logout")
@rate_limit(max_requests=20, window_seconds=60, identifier_type="ip", key_prefix="logout")
async def logout(body: LogoutBody, request: Request):
    try:
        # we decode to see if the token has been tampered with, if it has then it would return a 401 error
        decoded_token = decode_token(
            token=body.refresh_token, token_type="refresh")
    except:
        pass  # make logout idempotent

    refresh_token_hash = hashlib.sha256(
        body.refresh_token.encode("utf-8")).hexdigest()

    # update the refresh tokens (revoke it)
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                        UPDATE refresh_tokens
                        SET revoked_date = NOW()
                        WHERE token_hash = %s
                    """,
                    (refresh_token_hash,),
                )
            conn.commit()
    except psycopg.Error:
        raise HTTPException(status_code=500, detail="Failed to revoke token")

    return {"message": "Logged out successfully"}
