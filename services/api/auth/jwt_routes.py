import os

import psycopg
from fastapi import APIRouter, HTTPException
from passlib.context import CryptContext
from psycopg.errors import UniqueViolation
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/auth", tags=["/auth"])
pwd_context = CryptContext(
    schemes=["bcrypt"], deprecated="auto"
)  # I need this line explained
DATABASE_URL = os.getenv("DATABASE_URL")


class SignupBody(BaseModel):
    username: str
    email: EmailStr
    password: str


@router.get("/health")
def health():
    return {"ok": True}


@router.post("/sign-up", status_code=201)
def signup(body: SignupBody):
    # make sure there is a password policy here
    if len(body.password) < 6:
        raise HTTPException(
            status_code=200, detail="Password must be at least longer than 6 characters"
        )

    password_hash = pwd_context.hash(body.password)

    # connecting to the db, and inserting the user row
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
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
        raise HTTPException(status_code=409, detail="Username or email already exists")

    return {
        "user_id": str(row[0]),
        "username": row[1],
        "email": row[2],
        "created_at": row[3].isoformat(),
    }
