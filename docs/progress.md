# Keeping track of all of my progress and what I have done so far, and what is left to do

### Week 0

- [x] Create monorepo structure
- [x] Docker Compose: Postgres + Redis + API + GameServer skeleton
- [x] Add a minimal proto/ + codegen script
- [x] Deliverable: “everything boots locally” screenshot + basic README.

### Week 1

- [ ] FastAPI: signup/login, access JWT + refresh token rotation
    - [x] Set up Redis + Postgres services to docker-compose
    - [ ] set up Postgres table
        - [ ] users (id, username/email, password_hash, created_at)
        - [ ] refresh_tokens (id, user_id, token_hash, expires_at, revoked_at, created_at)
    - [ ] Implement manual JWT flow
    - [ ] Figure out what the "backend" is, connect frontend to backend
- [ ] Postgres schema: users, matches, games, audit_logs
- [ ] Redis rate limiting for auth endpoints
- [ ] Deliverable: working auth endpoints + migrations.
