Week 0 (1–2 evenings): Setup + scope lock

Create monorepo structure

Docker Compose: Postgres + Redis + API + GameServer skeleton

Add a minimal proto/ + codegen script
Deliverable: “everything boots locally” screenshot + basic README.

Week 1: Auth + data model (control plane)

FastAPI: signup/login, access JWT + refresh token rotation

Postgres schema: users, matches, games, audit_logs

Redis rate limiting for auth endpoints
Deliverable: working auth endpoints + migrations.

Week 2: Matchmaking + join ticket flow

Matchmaking request endpoint → queue in Redis

Create match in Postgres

Issue short-lived match ticket
Deliverable: client can request match and receive {ws_url, ticket, match_id}.

Week 3: C++ WebSocket server MVP (real-time core)

WS server accepts connections

Basic protocol: join match, send move message

Minimal move validation (start with library or simple checks; upgrade later)

Basic room state + broadcast
Deliverable: two clients can play a game end-to-end locally.

Week 4: gRPC integration (the “impressive systems” leap)

gRPC VerifyMatchTicket from C++ → FastAPI

gRPC ReportGameEnd from C++ → FastAPI

Persist PGN + game result
Deliverable: ticketed join + games saved automatically.

Week 5: Reliability + security hardening

Reconnect/resume (session token or resume ticket)

Per-connection and per-user WS rate limits + message size limits

RBAC scaffolding (admin vs user)

Append-only audit events (login, match start/end, bans)
Deliverable: feels production-ish, not fragile.

Week 6: Observability + load test (resume gold)

Prometheus metrics:

connected sockets, active games

move latency (histogram), error counts

Grafana dashboard

Load test: k6 (or a simple custom harness)
Deliverable: perf report: p50/p95/p99 move handling latency under load.

Week 7: Tournament/admin signature feature

Tournament create/join + basic bracket/swiss

Admin actions: kick/ban/pause

(Optional) gRPC ControlStream for pushing admin commands to C++
Deliverable: “security boundaries + ops controls” showcase.

Week 8: Polish + portfolio packaging

Threat model doc

Architecture diagram

“How to run locally” + “Design decisions” section

Record a 60–90s demo video
Deliverable: finished portfolio-grade repo.
