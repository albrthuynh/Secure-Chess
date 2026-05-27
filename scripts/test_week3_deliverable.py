#!/usr/bin/env python3
"""
Week 3 deliverable test: two clients play a game end-to-end over WebSocket.

Tests:
  1. Both players can join the same room and receive the starting FEN
  2. Turn enforcement: black is rejected if it tries to move first
  3. White makes a legal move; both players receive the updated FEN
  4. Black responds; both players receive the updated FEN
  5. Illegal move is rejected with an error
  6. A Scholar's Mate sequence ends with a game_over message (checkmate)

Run with:
  python3 scripts/test_week3_deliverable.py
"""

import asyncio
import json
import sys
import websockets

WS_URL = "ws://localhost:9001/ws"
GAME_ID = "test-game-week3"

GREEN = "\033[0;32m"
RED   = "\033[0;31m"
BLUE  = "\033[0;34m"
NC    = "\033[0m"

def ok(msg):   print(f"{GREEN}  PASS{NC}  {msg}")
def fail(msg): print(f"{RED}  FAIL{NC}  {msg}"); sys.exit(1)
def step(msg): print(f"\n{BLUE}--- {msg} ---{NC}")


async def recv_json(ws, timeout=3):
    raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
    return json.loads(raw)


async def run():
    async with (
        websockets.connect(WS_URL) as white,
        websockets.connect(WS_URL) as black,
    ):
        # ------------------------------------------------------------------ #
        # Step 1: Both players join the same room
        # ------------------------------------------------------------------ #
        step("Step 1: Both players join the room")

        await white.send(json.dumps({"type": "join_match", "game_id": GAME_ID, "color": "white"}))
        w_joined = await recv_json(white)
        assert w_joined["type"] == "joined" and w_joined["color"] == "white", w_joined
        assert "fen" in w_joined, "join response missing FEN"
        ok(f"white joined, starting FEN: {w_joined['fen']}")

        await black.send(json.dumps({"type": "join_match", "game_id": GAME_ID, "color": "black"}))
        b_joined = await recv_json(black)
        assert b_joined["type"] == "joined" and b_joined["color"] == "black", b_joined
        ok(f"black joined, starting FEN: {b_joined['fen']}")

        # ------------------------------------------------------------------ #
        # Step 2: Turn enforcement — black tries to move first (should fail)
        # ------------------------------------------------------------------ #
        step("Step 2: Turn enforcement (black moves out of turn)")

        await black.send(json.dumps({"type": "move", "game_id": GAME_ID, "move": "e7e5"}))
        err = await recv_json(black)
        assert err["type"] == "error" and "turn" in err["message"], err
        ok(f"server correctly rejected black's premature move: '{err['message']}'")

        # ------------------------------------------------------------------ #
        # Step 3: White makes a legal move; both players get the update
        # ------------------------------------------------------------------ #
        step("Step 3: White plays e2e4")

        await white.send(json.dumps({"type": "move", "game_id": GAME_ID, "move": "e2e4"}))
        w_recv = await recv_json(white)
        b_recv = await recv_json(black)

        assert w_recv["type"] == "move" and w_recv["move"] == "e2e4", w_recv
        assert b_recv["type"] == "move" and b_recv["move"] == "e2e4", b_recv
        assert w_recv["fen"] == b_recv["fen"], "FEN mismatch between players!"
        assert w_recv["turn"] == "black", f"expected turn=black, got {w_recv['turn']}"
        ok(f"both players received e2e4, new FEN: {w_recv['fen']}")

        # ------------------------------------------------------------------ #
        # Step 4: Illegal move is rejected
        # ------------------------------------------------------------------ #
        step("Step 4: Black sends an illegal move (e7e4 — occupied square)")

        await black.send(json.dumps({"type": "move", "game_id": GAME_ID, "move": "e7e4"}))
        err = await recv_json(black)
        assert err["type"] == "error" and "illegal" in err["message"], err
        ok(f"server correctly rejected illegal move: '{err['message']}'")

        # ------------------------------------------------------------------ #
        # Step 5: Scholar's Mate — plays out to checkmate
        #
        # The fastest checkmate in chess (4 moves):
        #   1. e4   e5
        #   2. Bc4  Nc6
        #   3. Qh5  Nf6??  (black's blunder)
        #   4. Qxf7#  (checkmate)
        # ------------------------------------------------------------------ #
        step("Step 5: Scholar's Mate sequence → game_over (checkmate)")

        moves = [
            (black, "e7e5"),   # 1... e5
            (white, "f1c4"),   # 2. Bc4
            (black, "b8c6"),   # 2... Nc6
            (white, "d1h5"),   # 3. Qh5
            (black, "g8f6"),   # 3... Nf6?? (the blunder)
            (white, "h5f7"),   # 4. Qxf7# (checkmate)
        ]

        for sender, move in moves:
            await sender.send(json.dumps({"type": "move", "game_id": GAME_ID, "move": move}))

            # Both players get the move broadcast
            msg_w = await recv_json(white)
            msg_b = await recv_json(black)
            assert msg_w["type"] == "move", f"expected move, got: {msg_w}"
            assert msg_b["type"] == "move", f"expected move, got: {msg_b}"

            color = "white" if sender == white else "black"
            ok(f"{color} played {move} → FEN: {msg_w['fen']}")

            # After the last move (checkmate), both players also get game_over
            if move == "h5f7":
                over_w = await recv_json(white)
                over_b = await recv_json(black)
                assert over_w["type"] == "game_over", f"expected game_over, got: {over_w}"
                assert over_b["type"] == "game_over", f"expected game_over, got: {over_b}"
                assert over_w["result"] == "white_wins", f"expected white_wins, got: {over_w['result']}"
                assert over_w["reason"] == "checkmate", f"expected checkmate, got: {over_w['reason']}"
                ok(f"game_over received by both — result: {over_w['result']}, reason: {over_w['reason']}")

        print(f"\n{GREEN}All tests passed — Week 3 deliverable complete!{NC}\n")


if __name__ == "__main__":
    asyncio.run(run())
