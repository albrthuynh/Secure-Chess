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
import os
import random
import statistics
import string
import subprocess
import sys
import time
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from pathlib import Path

import aiohttp
import websockets

API = "http://localhost:8000"
WS = "ws://localhost:9001/ws"
ROOT = Path(__file__).resolve().parents[1]

N_GAMES = 100        # total games to run
CONCURRENCY = 50    # max games in flight at once (macOS fd limit: ~4 fds/game)
SETUP_CONCURRENCY = 5  # max games creating users/signing in/matchmaking at once
JOIN_CONCURRENCY = 1  # max games handshaking/joining the WebSocket server at once
MOVE_DELAY_SECONDS = 0.12  # keeps each socket under the 10 messages/sec rate limit
WS_OPEN_TIMEOUT_SECONDS = 30
JOIN_ACK_TIMEOUT_SECONDS = 30
MOVE_RECV_TIMEOUT_SECONDS = 10
CLEAR_RATE_LIMITS_ON_START = True
REDIS_CONTAINER = "secure_chess_redis"
PASSWORD = "Loadtest123!"

# Ruy Lopez opening line — 37 alternating half-moves, all legal
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
    "f1e1",
    "b7b5",
    "a4b3",
    "d7d6",
    "c2c3",
    "e8g8",
    "h2h3",
    "c6b8",
    "d2d4",
    "b8d7",
    "c3c4",
    "c7c6",
    "c4b5",
    "a6b5",
    "b1c3",
    "c8b7",
    "c1g5",
    "b5b4",
    "c3b1",
    "h7h6",
    "g5h4",
    "c6c5",
    "d4e5",
    "f6e4",
    "h4e7",
    "d8e7",
    "e5d6",
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


def env_value(name: str) -> str | None:
    if value := os.getenv(name):
        return value

    env_file = ROOT / "infra" / ".env"
    if not env_file.exists():
        return None

    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == name:
            return value.strip().strip("\"'")

    return None


def clear_rate_limit_keys() -> None:
    if not CLEAR_RATE_LIMITS_ON_START:
        return

    password = env_value("REDIS_PASSWORD")
    if not password:
        print(f"{YELLOW}warning: REDIS_PASSWORD not found; rate limits were not cleared{NC}")
        return

    scan = subprocess.run(
        [
            "docker",
            "exec",
            REDIS_CONTAINER,
            "redis-cli",
            "-a",
            password,
            "--scan",
            "--pattern",
            "rate_limit:*",
        ],
        capture_output=True,
        text=True,
    )
    if scan.returncode != 0:
        print(f"{YELLOW}warning: could not scan Redis rate-limit keys; continuing{NC}")
        return

    keys = [key for key in scan.stdout.splitlines() if key]
    if not keys:
        print(f"{GREEN}cleared rate limits: 0 keys{NC}")
        return

    deleted = 0
    for i in range(0, len(keys), 100):
        batch = keys[i : i + 100]
        result = subprocess.run(
            ["docker", "exec", REDIS_CONTAINER, "redis-cli", "-a", password, "DEL", *batch],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"{YELLOW}warning: failed to delete some rate-limit keys; continuing{NC}")
            continue
        deleted += int(result.stdout.strip() or "0")

    print(f"{GREEN}cleared rate limits: {deleted} keys{NC}")


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


async def recv_json(ws, timeout: float = MOVE_RECV_TIMEOUT_SECONDS) -> dict:
    raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
    return json.loads(raw)


async def run_game(
    game_idx: int,
    setup_sem: asyncio.Semaphore,
    join_sem: asyncio.Semaphore,
) -> GameResult:
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

    phase = "setup"
    try:
        async with setup_sem:
            async with aiohttp.ClientSession() as session:
                # --- setup: register + login both players concurrently ---
                phase = "signing up users"
                await asyncio.gather(
                    sign_up(session, user_white),
                    sign_up(session, user_black),
                )

                phase = "signing in users"
                token_white, token_black = await asyncio.gather(
                    sign_in(session, user_white),
                    sign_in(session, user_black),
                )

                # white queues first → becomes p1 (white) in matchmaking
                phase = "queueing white"
                white_queue = await request_match(session, token_white, time_control)
                if not white_queue.get("queued"):
                    result.error = f"white failed to queue: {white_queue}"
                    return result

                # black queues second → triggers the match, gets ticket in response
                phase = "queueing black"
                match_data = await request_match(session, token_black, time_control)

                if not match_data.get("match_found"):
                    result.error = f"match not found: {match_data}"
                    return result

                ticket_black = match_data["ticket"]
                phase = "polling white ticket"
                ticket_white = await poll_ticket(session, token_white)

        # --- play the game, measuring each move's round-trip latency ---
        async with AsyncExitStack() as stack:
            async with join_sem:
                phase = "opening white WebSocket"
                ws_white = await stack.enter_async_context(
                    websockets.connect(WS, open_timeout=WS_OPEN_TIMEOUT_SECONDS)
                )
                phase = "opening black WebSocket"
                ws_black = await stack.enter_async_context(
                    websockets.connect(WS, open_timeout=WS_OPEN_TIMEOUT_SECONDS)
                )

                phase = "joining white"
                await ws_white.send(
                    json.dumps(
                        {"type": "join_match", "ticket": ticket_white, "color": "white"}
                    )
                )
                phase = "joining black"
                await ws_black.send(
                    json.dumps(
                        {"type": "join_match", "ticket": ticket_black, "color": "black"}
                    )
                )

                phase = "waiting for white join ack"
                join_white = await recv_json(ws_white, JOIN_ACK_TIMEOUT_SECONDS)
                phase = "waiting for black join ack"
                join_black = await recv_json(ws_black, JOIN_ACK_TIMEOUT_SECONDS)

                if join_white.get("type") != "joined" or join_black.get("type") != "joined":
                    result.error = f"join failed — white:{join_white}  black:{join_black}"
                    return result

            for i, move in enumerate(MOVES):
                phase = f"playing move {i + 1}/{len(MOVES)} {move}"
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
                if msg_other.get("type") == "error":
                    result.error = f"move rejected for opponent: {msg_other['message']}"
                    return result
                if msg_sender.get("type") != "move" or msg_other.get("type") != "move":
                    result.error = f"unexpected response for move {move}: sender:{msg_sender} other:{msg_other}"
                    return result

                result.latencies_ms.append(elapsed_ms)
                if MOVE_DELAY_SECONDS and i < len(MOVES) - 1:
                    await asyncio.sleep(MOVE_DELAY_SECONDS)

    except TimeoutError:
        result.error = f"timed out while {phase}"
    except Exception as exc:
        result.error = f"{phase}: {exc}" if str(exc) else f"{phase}: {type(exc).__name__}"

    return result


def percentile(sorted_data: list[float], p: float) -> float:
    idx = max(0, int(len(sorted_data) * p / 100) - 1)
    return sorted_data[idx]


async def main() -> None:
    clear_rate_limit_keys()

    print(f"\n{BLUE}secure-chess — move handling latency load test{NC}")
    print(f"  total games      : {N_GAMES}")
    print(f"  concurrency      : {CONCURRENCY}")
    print(f"  setup concurrency: {SETUP_CONCURRENCY}")
    print(f"  join concurrency : {JOIN_CONCURRENCY}")
    print(f"  move delay       : {MOVE_DELAY_SECONDS:.2f}s")
    print(f"  join timeout     : {JOIN_ACK_TIMEOUT_SECONDS:.0f}s")
    print(f"  moves per game   : {len(MOVES)}")
    print(f"  total moves      : {N_GAMES * len(MOVES)}")
    print()

    sem = asyncio.Semaphore(CONCURRENCY)
    setup_sem = asyncio.Semaphore(SETUP_CONCURRENCY)
    join_sem = asyncio.Semaphore(JOIN_CONCURRENCY)

    async def run_game_limited(idx: int) -> GameResult:
        async with sem:
            return await run_game(idx, setup_sem, join_sem)

    start = time.perf_counter()
    results = await asyncio.gather(*[run_game_limited(i) for i in range(N_GAMES)])
    total_s = time.perf_counter() - start

    all_latencies: list[float] = []
    errors = 0

    for r in results:
        if r.error or len(r.latencies_ms) != len(MOVES):
            errors += 1
            detail = r.error or f"incomplete game: measured {len(r.latencies_ms)}/{len(MOVES)} moves"
            print(
                f"  {RED}[game {r.game_id:02d} error]{NC}  {detail}", file=sys.stderr
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
