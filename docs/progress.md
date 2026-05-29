# Keeping track of all of my progress and what I have done so far, and what is left to do

### Week 0

- [x] Create monorepo structure
- [x] Docker Compose: Postgres + Redis + API + GameServer skeleton
- [x] Add a minimal proto/ + codegen script
- [x] Deliverable: “everything boots locally” screenshot + basic README.

### Week 1

- [x] FastAPI: signup/login, access JWT + refresh token rotation
    - [x] Set up Redis + Postgres services to docker-compose
    - [x] set up Postgres table
        - [x] users (id, username/email, password_hash, created_at)
        - [x] refresh_tokens (id, user_id, token_hash, expires_at, revoked_at, created_at)
refresh_time: int,
    - [x] Implement manual JWT flow
- [x] Postgres schema: users, matches, games, audit_logs (in progress)
- [x] Redis rate limiting for auth endpoints
- [x] Deliverable: working auth endpoints + migrations.


### Week 2: Matchmaking + join ticket flow

- [x] Matchmaking request endpoint → queue in Redis
- [x] Create match in Postgres
- [x] Issue short-lived match ticket
- [x] Deliverable: client can request match and receive {ws_url, ticket, match_id}.

### Week 3: C++ WebSocket server MVP (real-time core)

- [x] WS server accepts connections
- [x] Basic protocol: join match, send move message
- [x] Minimal move validation (start with library or simple checks; upgrade later)
- [x] Basic room state + broadcast
- [x] Deliverable: two clients can play a game end-to-end locally.

###  Week 4: gRPC integration (the “impressive systems” leap)
- [x] gRPC VerifyMatchTicket from C++ → FastAPI
- [x] gRPC ReportGameEnd from C++ → FastAPI
- [x] Persist PGN + game result
- [x] Deliverable: ticketed join + games saved automatically.

### Week 5: Reliability + security hardening

- [x] Reconnect/resume (session token or resume ticket)
- [x] Per-connection and per-user WS rate limits + message size limits
- [x] Append-only audit events (login, match start/end, bans)
- [x] Deliverable: feels production-ish, not fragile.

### Week 6: Observability + load test (resume gold)
**Prometheus metrics**
- [x] connected sockets, active games
- [x] move latency (histogram), error counts

**Grafana dashboard**
- [x] Dashboard set up, set up grafana dashboard
- [x] Load test: k6 (or a simple custom harness)

- [x] Deliverable: perf report: p50/p95/p99 move handling latency under load.

### Week 7: Polish + portfolio packaging

Threat model doc

- [x] Architecture diagram
- [x] “How to run locally” + “Design decisions” section
Deliverable: finished portfolio-grade repo.
