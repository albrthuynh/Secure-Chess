#!/usr/bin/env python3
"""
Week 4 deliverable test: gRPC ticket verification + game persistence end-to-end.

What this tests:
  1. Two real users sign up and log in via FastAPI
  2. Matchmaking creates a match and issues tickets for both players
  3. The game server rejects a connection with an invalid ticket (gRPC verify fail path)
  4. Both players join with valid tickets — gRPC VerifyMatchTicket succeeds
  5. A Scholar's Mate plays out to checkmate
  6. gRPC ReportGameEnd is called; game is persisted in Postgres
  7. We query Postgres directly to confirm the game row exists with the correct result

Requires both servers running:
  FastAPI:  cd services/api && uvicorn main:app --port 8000
  C++ WS:   ./services/gameserver/build/gameserver

Run with:
  python3 scripts/test_week4_deliverable.py
"""

import asyncio
import json
import os
import sys
import uuid

import psycopg
import requests
import websockets
from websockets.exceptions import ConnectionClosedError

API = "http://localhost:8000"
WS  = "ws://localhost:9001/ws"

# Load Postgres credentials from infra/.env
def _load_env(path: str) -> dict:
    env = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    env[k.strip()] = v.strip().strip('"')
    except FileNotFoundError:
        pass
    return env

_env = _load_env(os.path.join(os.path.dirname(__file__), "../infra/.env"))
DATABASE_URL = os.getenv("DATABASE_URL") or (
    f"postgresql://{_env['POSTGRES_USER']}:{_env['POSTGRES_PASSWORD']}"
    f"@localhost:{_env.get('POSTGRES_PORT', '5432')}/{_env['POSTGRES_DB']}"
)

GREEN = "\033[0;32m"
RED   = "\033[0;31m"
BLUE  = "\033[0;34m"
NC    = "\033[0m"

def ok(msg):   print(f"{GREEN}  PASS{NC}  {msg}")
def fail(msg): print(f"{RED}  FAIL{NC}  {msg}"); sys.exit(1)
def step(msg): print(f"\n{BLUE}--- {msg} ---{NC}")


def signup_and_login(suffix: str) -> tuple[str, str]:
    """Creates a user and returns (user_id, access_token)."""
    uid = uuid.uuid4().hex[:8]
    username = f"test_{suffix}_{uid}"
    email    = f"{username}@example.com"
    password = "TestPass123!"

    r = requests.post(f"{API}/auth/sign-up", json={"username": username, "email": email, "password": password})
    if r.status_code != 201:
        fail(f"signup failed for {username}: {r.text}")

    r = requests.post(f"{API}/auth/sign-in", json={"username": username, "password": password})
    if r.status_code != 200:
        fail(f"login failed for {username}: {r.text}")

    data = r.json()
    return data["user_id"], data["access_token"]


async def recv_json(ws, timeout=5):
    raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
    return json.loads(raw)


async def run():
    # ------------------------------------------------------------------ #
    # Step 1: Create two real users
    # ------------------------------------------------------------------ #
    step("Step 1: Sign up and log in two users")

    white_user_id, white_token = signup_and_login("white")
    black_user_id, black_token = signup_and_login("black")
    ok(f"white user created: {white_user_id}")
    ok(f"black user created: {black_user_id}")

    headers_white = {"Authorization": f"Bearer {white_token}"}
    headers_black = {"Authorization": f"Bearer {black_token}"}

    # ------------------------------------------------------------------ #
    # Step 2: Matchmaking — white queues first, black triggers the match
    # ------------------------------------------------------------------ #
    step("Step 2: Matchmaking — create a match and get tickets")

    r = requests.post(f"{API}/matchmaking/request",
        json={"time_control": "10+0", "increment": 0},
        headers=headers_white)
    if r.status_code != 202:
        fail(f"white matchmaking request failed: {r.text}")
    ok("white queued")

    r = requests.post(f"{API}/matchmaking/request",
        json={"time_control": "10+0", "increment": 0},
        headers=headers_black)
    if r.status_code != 202:
        fail(f"black matchmaking request failed: {r.text}")

    match_data = r.json()
    if not match_data.get("match_found"):
        fail(f"expected match_found, got: {match_data}")

    match_id    = match_data["match_id"]
    black_ticket = match_data["ticket"]
    ok(f"match created: {match_id}")
    ok(f"black ticket received directly")

    # white's ticket was stored in Redis — fetch it via the poll endpoint
    r = requests.get(f"{API}/matchmaking/ticket", headers=headers_white)
    if r.status_code != 200:
        fail(f"white ticket poll failed: {r.text}")
    white_ticket = r.json()["ticket"]
    ok("white ticket retrieved from Redis")

    # ------------------------------------------------------------------ #
    # Step 3: Reject an invalid ticket
    # ------------------------------------------------------------------ #
    step("Step 3: Invalid ticket is rejected by game server")

    async with websockets.connect(WS) as ws:
        await ws.send(json.dumps({"type": "join_match", "ticket": "this.is.fake", "color": "white"}))
        try:
            msg = await recv_json(ws)
            assert msg["type"] == "error" and "invalid ticket" in msg["message"], msg
            ok(f"game server correctly rejected invalid ticket: '{msg['message']}'")
        except ConnectionClosedError:
            # server may close the connection before we can read the error frame — both are valid rejections
            ok("game server correctly rejected invalid ticket (connection closed)")

    # ------------------------------------------------------------------ #
    # Step 4: Both players join with valid tickets
    # ------------------------------------------------------------------ #
    step("Step 4: Both players join with valid tickets (gRPC VerifyMatchTicket)")

    async with (
        websockets.connect(WS) as white_ws,
        websockets.connect(WS) as black_ws,
    ):
        await white_ws.send(json.dumps({"type": "join_match", "ticket": white_ticket, "color": "white"}))
        w_joined = await recv_json(white_ws)
        assert w_joined["type"] == "joined", f"expected joined, got: {w_joined}"
        ok(f"white joined match {match_id}")

        await black_ws.send(json.dumps({"type": "join_match", "ticket": black_ticket, "color": "black"}))
        b_joined = await recv_json(black_ws)
        assert b_joined["type"] == "joined", f"expected joined, got: {b_joined}"
        ok(f"black joined match {match_id}")

        # ------------------------------------------------------------------ #
        # Step 5: Play Scholar's Mate to checkmate
        # ------------------------------------------------------------------ #
        step("Step 5: Play Scholar's Mate → checkmate (triggers gRPC ReportGameEnd)")

        moves = [
            (white_ws, "e2e4"),
            (black_ws, "e7e5"),
            (white_ws, "f1c4"),
            (black_ws, "b8c6"),
            (white_ws, "d1h5"),
            (black_ws, "g8f6"),
            (white_ws, "h5f7"),  # checkmate
        ]

        for sender, move in moves:
            await sender.send(json.dumps({"type": "move", "move": move}))
            msg_w = await recv_json(white_ws)
            msg_b = await recv_json(black_ws)
            assert msg_w["type"] == "move", f"expected move, got: {msg_w}"
            color = "white" if sender == white_ws else "black"
            ok(f"{color} played {move}")

            if move == "h5f7":
                over_w = await recv_json(white_ws)
                over_b = await recv_json(black_ws)
                assert over_w["type"] == "game_over", f"expected game_over, got: {over_w}"
                assert over_w["result"] == "white_wins", f"expected white_wins, got: {over_w}"
                ok(f"game_over received — result: {over_w['result']}, reason: {over_w['reason']}")

        # ------------------------------------------------------------------ #
        # Step 6: Confirm game was persisted in Postgres
        # ------------------------------------------------------------------ #
        step("Step 6: Verify game row exists in Postgres (gRPC ReportGameEnd worked)")

        # small pause to let the async gRPC call complete before querying
        await asyncio.sleep(1)

        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT result, pgn, moves FROM games WHERE match_id = %s",
                    (match_id,)
                )
                row = cur.fetchone()

        if not row:
            fail(f"no game row found in Postgres for match_id {match_id}")

        result, pgn, move_count = row
        assert result == "white_win", f"expected white_win, got: {result}"
        assert move_count == 7, f"expected 7 moves, got: {move_count}"
        assert pgn, "pgn should not be empty"
        ok(f"game persisted — result: {result}, moves: {move_count}, pgn: {pgn}")

    print(f"\n{GREEN}All tests passed — Week 4 deliverable complete!{NC}\n")


if __name__ == "__main__":
    asyncio.run(run())
