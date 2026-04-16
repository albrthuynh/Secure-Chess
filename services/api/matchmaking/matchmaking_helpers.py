import os
import psycopg

from fastapi import HTTPException
from pydantic import BaseModel, Field

DATABASE_URL = os.getenv("DATABASE_URL")


class GameDetails(BaseModel):
    user_id_white: str
    user_id_black: str
    time_control: str
    increment: int = Field(ge=0)


def create_match(game_details: GameDetails):
    user_id_white = game_details.user_id_white
    user_id_black = game_details.user_id_black

    if user_id_white == user_id_black:
        raise HTTPException(
            status_code=400, detail="Cannot make match with 2 of the same players"
        )

    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                        INSERT INTO matches 
                        (white_user_id, black_user_id, time_control, increment)
                        VALUES (%s, %s, %s, %s)
                        RETURNING match_id, white_user_id, black_user_id, time_control, increment
                    """,
                    (
                        user_id_white,
                        user_id_black,
                        game_details.time_control,
                        game_details.increment,
                    ),
                )
                row = cur.fetchone()
            conn.commit()
    except psycopg.Error:
        raise HTTPException(status_code=500, detail="Server unable to create match")

    return {
        "match_id": str(row[0]),
        "white_user_id": str(row[1]),
        "black_user_id": str(row[2]),
        "time_control": row[3],
        "increment": row[4],
    }
