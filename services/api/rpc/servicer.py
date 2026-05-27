"""
The class that is implementing VerifyMatchTicket and ReportGameEnd
Essentially the class handling all of the functions defined in the protofile
"""

import os
import sys
import psycopg
from fastapi import HTTPException

# The generated files use flat imports (import gamecontrol_pb2),
# so we add grpc_generated/ to the path before importing them.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "grpc_generated"))

import gamecontrol_pb2
import gamecontrol_pb2_grpc

from auth.jwt_helpers import decode_token

DATABASE_URL = os.getenv("DATABASE_URL")


class GameControlServicer(gamecontrol_pb2_grpc.GameControlServicer):

    async def VerifyMatchTicket(self, request, context):
        try:
            payload = decode_token(request.ticket, "match_ticket")
        except HTTPException:
            return gamecontrol_pb2.VerifyTicketResponse(
                valid=False, match_id="", player_id=""
            )

        return gamecontrol_pb2.VerifyTicketResponse(
            valid=True,
            match_id=payload["match_id"],
            player_id=payload["sub"],
        )

    async def ReportGameEnd(self, request, context):
        try:
            with psycopg.connect(DATABASE_URL) as conn:
                with conn.cursor() as cur:
                    # fetch match details so we know who played and what time control
                    cur.execute(
                        "SELECT white_user_id, black_user_id, time_control FROM matches WHERE match_id = %s",
                        (request.match_id,),
                    )
                    row = cur.fetchone()
                    if not row:
                        return gamecontrol_pb2.GameEndResponse(acknowledged=False)

                    white_id, black_id, time_control = row

                    if not request.winner_id:
                        result = "draw"
                    elif request.winner_id == str(white_id):
                        result = "white_win"
                    elif request.winner_id == str(black_id):
                        result = "black_win"
                    else:
                        result = "abandoned"

                    pgn = " ".join(request.moves)
                    move_count = len(request.moves)

                    cur.execute(
                        """
                        INSERT INTO games
                            (match_id, white_user_id, black_user_id, result, pgn, moves, time_control, ended_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                        """,
                        (
                            request.match_id,
                            white_id,
                            black_id,
                            result,
                            pgn,
                            move_count,
                            time_control,
                        ),
                    )
                    cur.execute(
                        "UPDATE matches SET status = 'completed' WHERE match_id = %s",
                        (request.match_id,),
                    )
                conn.commit()
        except psycopg.Error:
            return gamecontrol_pb2.GameEndResponse(acknowledged=False)

        return gamecontrol_pb2.GameEndResponse(acknowledged=True)
