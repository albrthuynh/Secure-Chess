#!/usr/bin/env python3
"""
Move handling latency load test for secure-chess.

Spins up N concurrent games and measures round-trip WebSocket latency for each
move (time from client sending the move to receiving the broadcast back).
Reports p50 / p95 / p99 at the end.

Requirements:
    pip install -r loadtests/requirements.txt

Both servers must be running:
    docker compose --env-file infra/.env -f infra/docker-compose.yml up -d

Run:
    python3 loadtests/latency_load_test.py
"""

import asyncio
import json
import random
import statistics
import string
import sys
import time
from dataclasses import dataclass, field

import aiohttp
import websockets

API = "http://localhost:8000"
WS = "ws://localhost:9001/ws"

N_GAMES = 10  # concurrent games — raise this to increase load
PASSWORD = "Loadtest123!"

# Ruy Lopez opening — 10 alternating half-moves (5 per side), all legal
MOVES = [
    "e2e4",
    "e7e5",
    "g1f3",
    "b8c6",
    "f1b5",
    "a7a6",
    "b5a4",
    "g8f6",
    "e1g1",
    "f8e7",
]

GREEN = "\033[0;32m"
RED = "\033[0;31m"
BLUE = "\033[0;34m"
YELLOW = "\033[0;33m"
NC = "\033[0m"


@dataclass
class GameResult:
    game_id: int
    latencies_ms: list[float] = field(default_factory=list)
    error: str | None = None


def rand_suffix(n: int = 8) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


async def sign_up(session: aiohttp.ClientSession, username: str) -> None:
    await session.post(
        f"{API}/auth/sign-up",
        json={
            "username": username,
            "email": f"{username}@loadtest.dev",
            "password": PASSWORD,
        },
    )


async def sign_in(session: aiohttp.ClientSession, username: str) -> str:
    resp = await session.post(
        f"{API}/auth/sign-in",
        json={
            "username": username,
            "password": PASSWORD,
        },
    )
    data = await resp.json()
    if "access_token" not in data:
        raise RuntimeError(f"sign-in failed for {username}: {data}")
    return data["access_token"]


async def request_match(
    session: aiohttp.ClientSession, token: str, time_control: str
) -> dict:
    resp = await session.post(
        f"{API}/matchmaking/request",
        json={"time_control": time_control, "increment": 0},
        headers={"Authorization": f"Bearer {token}"},
    )
    return await resp.json()


async def poll_ticket(session: aiohttp.ClientSession, token: str) -> str:
    """White player's ticket is stored in Redis — poll until it appears."""
    headers = {"Authorization": f"Bearer {token}"}
    for _ in range(20):
        resp = await session.get(f"{API}/matchmaking/ticket", headers=headers)
        if resp.status == 200:
            data = await resp.json()
            return data["ticket"]
        await asyncio.sleep(0.2)
    raise RuntimeError("timed out polling for ticket")


async def recv_json(ws, timeout: float = 5.0) -> dict:
    raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
    return json.loads(raw)


async def run_game(game_idx: int) -> GameResult:
    """
    Runs one complete game end-to-end and returns latency measurements.
    Each game gets its own unique time_control so it never cross-matches
    with other concurrent games.
    """
    result = GameResult(game_id=game_idx)
    suffix = rand_suffix()

    # unique queue key — ensures only this pair ever matches each other
    time_control = f"lt_{suffix}"
    user_white = f"lt_w_{suffix}"
    user_black = f"lt_b_{suffix}"

    try:
        async with aiohttp.ClientSession() as session:
            # --- setup: register + login both players concurrently ---
            await asyncio.gather(
                sign_up(session, user_white),
                sign_up(session, user_black),
            )
            token_white, token_black = await asyncio.gather(
                sign_in(session, user_white),
                sign_in(session, user_black),
            )

            # white queues first → becomes p1 (white) in matchmaking
            white_queue = await request_match(session, token_white, time_control)
            if not white_queue.get("queued"):
                result.error = f"white failed to queue: {white_queue}"
                return result

            # black queues second → triggers the match, gets ticket in response
            match_data = await request_match(session, token_black, time_control)

            if not match_data.get("match_found"):
                result.error = f"match not found: {match_data}"
                return result

            ticket_black = match_data["ticket"]
            ticket_white = await poll_ticket(session, token_white)

        # --- play the game, measuring each move's round-trip latency ---
        async with (
            websockets.connect(WS) as ws_white,
            websockets.connect(WS) as ws_black,
        ):
            await ws_white.send(
                json.dumps(
                    {"type": "join_match", "ticket": ticket_white, "color": "white"}
                )
            )
            await ws_black.send(
                json.dumps(
                    {"type": "join_match", "ticket": ticket_black, "color": "black"}
                )
            )

            join_white = await recv_json(ws_white)
            join_black = await recv_json(ws_black)

            if join_white.get("type") != "joined" or join_black.get("type") != "joined":
                result.error = f"join failed — white:{join_white}  black:{join_black}"
                return result

            for i, move in enumerate(MOVES):
                sender = ws_white if i % 2 == 0 else ws_black
                other = ws_black if i % 2 == 0 else ws_white

                # measure: send → both players receive broadcast
                t0 = time.perf_counter()
                await sender.send(json.dumps({"type": "move", "move": move}))
                msg_sender = await recv_json(sender)
                msg_other = await recv_json(other)
                elapsed_ms = (time.perf_counter() - t0) * 1000

                if msg_sender.get("type") == "error":
                    result.error = f"move rejected: {msg_sender['message']}"
                    return result

                result.latencies_ms.append(elapsed_ms)

    except Exception as exc:
        result.error = str(exc)

    return result


def percentile(sorted_data: list[float], p: float) -> float:
    idx = max(0, int(len(sorted_data) * p / 100) - 1)
    return sorted_data[idx]


async def main() -> None:
    print(f"\n{BLUE}secure-chess — move handling latency load test{NC}")
    print(f"  concurrent games : {N_GAMES}")
    print(f"  moves per game   : {len(MOVES)}")
    print(f"  total moves      : {N_GAMES * len(MOVES)}")
    print()

    start = time.perf_counter()
    results = await asyncio.gather(*[run_game(i) for i in range(N_GAMES)])
    total_s = time.perf_counter() - start

    all_latencies: list[float] = []
    errors = 0

    for r in results:
        if r.error:
            errors += 1
            print(
                f"  {RED}[game {r.game_id:02d} error]{NC}  {r.error}", file=sys.stderr
            )
        else:
            all_latencies.extend(r.latencies_ms)

    successful = N_GAMES - errors

    print(f"  games completed  : {GREEN}{successful}/{N_GAMES}{NC}")
    print(f"  moves measured   : {len(all_latencies)}")
    print(f"  total test time  : {total_s:.1f}s")

    if not all_latencies:
        print(f"\n{RED}no latency data collected — check errors above{NC}")
        sys.exit(1)

    all_latencies.sort()

    p50 = percentile(all_latencies, 50)
    p95 = percentile(all_latencies, 95)
    p99 = percentile(all_latencies, 99)

    # colour-code by how impressive the numbers are
    def fmt(ms: float) -> str:
        color = GREEN if ms < 10 else YELLOW if ms < 50 else RED
        return f"{color}{ms:.2f} ms{NC}"

    print(f"""
{BLUE}move handling latency  (WebSocket send → broadcast received){NC}
  p50  :  {fmt(p50)}
  p95  :  {fmt(p95)}
  p99  :  {fmt(p99)}
  min  :  {fmt(min(all_latencies))}
  max  :  {fmt(max(all_latencies))}
  mean :  {fmt(statistics.mean(all_latencies))}
""")


if __name__ == "__main__":
    asyncio.run(main())
