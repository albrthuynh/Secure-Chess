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
- [ ] Minimal move validation (start with library or simple checks; upgrade later)
- [x] Basic room state + broadcast
- [ ] Deliverable: two clients can play a game end-to-end locally.

###  Week 4: gRPC integration (the “impressive systems” leap)
- [ ] gRPC VerifyMatchTicket from C++ → FastAPI
- [ ] gRPC ReportGameEnd from C++ → FastAPI
- [ ] Persist PGN + game result
- [ ] Deliverable: ticketed join + games saved automatically.

### Week 5: Reliability + security hardening

- [ ] Reconnect/resume (session token or resume ticket)
- [ ] Per-connection and per-user WS rate limits + message size limits
- [ ] RBAC scaffolding (admin vs user)
- [ ] Append-only audit events (login, match start/end, bans)
- [ ] Deliverable: feels production-ish, not fragile.

### Week 6: Observability + load test (resume gold)
**Prometheus metrics**
- [ ] connected sockets, active games
- [ ] move latency (histogram), error counts

**Grafana dashboard**
- [ ] Load test: k6 (or a simple custom harness)
- [ ] Deliverable: perf report: p50/p95/p99 move handling latency under load.

### Week 7: Tournament/admin signature feature (probably don't care for the tournament for this tbh, if admin is related to tournament then scratch this)
- [ ] Tournament create/join + basic bracket/swiss
- [ ] Admin actions: kick/ban/pause

(Optional) gRPC ControlStream for pushing admin commands to C++
Deliverable: “security boundaries + ops controls” showcase.

### Week 8: Polish + portfolio packaging

Threat model doc

- [ ] Architecture diagram
- [ ] “How to run locally” + “Design decisions” section
- [ ] Record a 60–90s demo video
Deliverable: finished portfolio-grade repo.
