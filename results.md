# Secure Chess Load Test Results

## Final Run

Configuration:

| Setting | Value |
|---|---:|
| Total games | 100 |
| Max games in flight | 50 |
| Setup concurrency | 5 |
| WebSocket join concurrency | 1 |
| Moves per game | 37 |
| Total moves | 3,700 |
| Move delay | 0.12s |
| Join timeout | 30s |

Results:

| Metric | Result |
|---|---:|
| Games completed | 100 / 100 |
| Moves measured | 3,700 / 3,700 |
| Total test time | 115.5s |
| p50 latency | 1.20 ms |
| p95 latency | 5.06 ms |
| p99 latency | 7.09 ms |
| min latency | 0.38 ms |
| max latency | 13.96 ms |
| mean latency | 1.79 ms |

## Problems Found

### Stale Socket Metrics

The dashboard showed mismatched values such as a low `chess_active_games` count with a high `chess_connected_sockets` count. The WebSocket close handler returned early when the room no longer existed, which skipped `connected_sockets_->Decrement()`.

Fix:

- Decrement `connected_sockets_` at the start of the close handler.
- Decrement `active_games_` when a game ends and the room is erased.

### Too Many Moves for Original Test

The latency test originally played 10 half-moves per game. The test was expanded to 37 legal alternating half-moves using a Ruy Lopez line.

Fix:

- Updated `MOVES` to 37 legal half-moves.
- Verified the sequence against the same C++ chess library used by the game server.

### WebSocket Rate Limit Interference

The expanded 37-move test could send moves fast enough to hit the per-socket WebSocket rate limit.

Fix:

- Added `MOVE_DELAY_SECONDS = 0.12`.
- Kept the move receive timeout strict so real move-path stalls still fail the test.

### Redis API Rate Limit Carryover

Repeated test runs could inherit stale API rate-limit keys from earlier manual or automated runs.

Fix:

- Added startup cleanup for Redis keys matching `rate_limit:*`.

### WebSocket Join Pressure

Early runs produced handshake timeouts and join acknowledgement timeouts. The game server was doing blocking gRPC calls while handling WebSocket messages.

Fix:

- Moved blocking gRPC work off the uWebSockets event loop.
- Added a small gRPC worker pool.
- Used `uWS::Loop::defer(...)` to apply room/socket updates back on the WebSocket event loop.

### API Setup Pressure

The test creates two fresh users per game, signs them in, and runs matchmaking. With too many setup tasks at once, HTTP setup occasionally disconnected before the move phase.

Fix:

- Added `SETUP_CONCURRENCY = 5`.
- Added phase-specific error messages for signup, signin, matchmaking, ticket polling, joining, and move playback.

## Current Interpretation

The final run completed every game and measured every move. With setup and join pressure controlled, the C++ move path stayed well under 10 ms at p99 for 3,700 measured move broadcasts.
