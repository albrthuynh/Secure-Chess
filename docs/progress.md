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
- [ ] Issue short-lived match ticket
- [ ] Deliverable: client can request match and receive {ws_url, ticket, match_id}.

### Week 3: C++ WebSocket server MVP (real-time core)

- [ ] WS server accepts connections
- [ ] Basic protocol: join match, send move message
- [ ] Minimal move validation (start with library or simple checks; upgrade later)
- [ ] Basic room state + broadcast
- [ ] Deliverable: two clients can play a game end-to-end locally.

