How everything connects (end-to-end)
1) Login / session

Next.js → FastAPI (HTTP): user logs in

FastAPI returns:

access JWT (short-lived)

refresh token (rotating)

2) Matchmaking

Next.js → FastAPI (HTTP): “find match” request

FastAPI:

validates user

enqueues matchmaking in Redis

creates match_id in Postgres

generates a short-lived match ticket (signed)

FastAPI returns to client:

ws_url (C++ server)

ticket (expires quickly)

match_id

3) Real-time gameplay (hot path)

Next.js → C++ Game Server (WebSocket): connects and sends ticket

C++ → FastAPI (gRPC): VerifyMatchTicket(ticket)

FastAPI verifies signature/expiry/permissions and responds

C++ admits user into the match room

During the game:

Next.js ↔ C++ (WebSocket): moves, clock updates, resign, draw offers

C++ validates moves locally (bitboards), updates authoritative state

4) Game end + persistence

C++ → FastAPI (gRPC): ReportGameEnd(match_id, result, pgn, stats, flags)

FastAPI:

writes game record + PGN to Postgres

updates ratings

appends to audit log

optionally marks abuse signals

5) Admin / tournament control (impressive streaming piece)

FastAPI ↔ C++ (gRPC bidirectional stream): ControlStream

C++ sends heartbeats + load

FastAPI can push commands:

kick/ban user

pause/terminate match

tournament control actions

6) Observability

Prometheus scrapes metrics from:

FastAPI service (HTTP + gRPC metrics)

C++ server (WS metrics + internal metrics)

Grafana shows:

p50/p95/p99 move latency

connected sockets

match creation rate

error rates

CPU/memory
