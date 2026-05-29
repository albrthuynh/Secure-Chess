# Secure Chess

A production-style real-time chess platform built from scratch as a backend engineering learning project. A high-performance C++ WebSocket game server runs authoritative gameplay while a FastAPI control plane handles auth, matchmaking, and persistence. Services communicate via gRPC. The full stack is containerized and observable via Prometheus and Grafana.

---

## Tech Stack

![Next.js](https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=nextdotjs&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![C++](https://img.shields.io/badge/C%2B%2B-00599C?style=for-the-badge&logo=cplusplus&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-336791?style=for-the-badge&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![Prometheus](https://img.shields.io/badge/Prometheus-E6522C?style=for-the-badge&logo=prometheus&logoColor=white)
![Grafana](https://img.shields.io/badge/Grafana-F46800?style=for-the-badge&logo=grafana&logoColor=white)

| Layer | Technology |
|---|---|
| Frontend | Next.js (TypeScript) |
| Control Plane | FastAPI (Python) — REST + gRPC server |
| Game Server | C++ with uWebSockets — authoritative move validation |
| Service-to-service | gRPC (protobuf) |
| Primary DB | PostgreSQL |
| Cache / Ephemeral | Redis |
| Observability | Prometheus + Grafana |
| Infra | Docker Compose |

---

## What Was Built

### Authentication
Manual JWT flow — short-lived access tokens (never stored) and long-lived refresh tokens stored as bcrypt hashes in Postgres, enabling revocation. Token rotation on every refresh. Redis-based rate limiting on all auth endpoints using a fixed window algorithm, keyed by IP or user ID.

### Matchmaking
Redis queue per time control — players are paired in arrival order. Short-lived signed match tickets are issued on match found and verified by the game server before a player is seated. A polling endpoint lets the first queued player retrieve their ticket from Redis.

### Real-Time Game Server
Authoritative C++ WebSocket server — move validation runs entirely server-side using a chess library. Clients are never trusted. Turn enforcement, full legal move generation, and game-over detection (checkmate, stalemate, insufficient material, fifty-move rule, threefold repetition) are all handled server-side. Both players receive every move broadcast in real time.

### Service-to-Service Communication
The C++ game server communicates with the FastAPI control plane via gRPC. `VerifyMatchTicket` is called before seating any player. `ReportGameEnd` fires on game completion, persisting the result and PGN to Postgres automatically. `CreateResumeToken` and `ResolveResumeToken` handle the reconnect flow.

### Reconnect / Resume
When a player disconnects mid-game, their room stays alive. A resume token issued at join time is stored in Redis and consumed on reconnect (`GETDEL` — single use). The reconnecting player is re-seated into the existing room and immediately sent the current board position and full move history to re-sync.

### Rate Limiting + Security
Per-connection WebSocket rate limiting (10 messages/sec) tracked in-memory per socket. Message size limit (1KB) enforced before JSON parsing to prevent CPU-burn attacks. Append-only `audit_logs` table in Postgres with DB-level rules blocking UPDATE and DELETE — events captured include signup, login, failed login, logout, match start, and game end.

### Observability
FastAPI is auto-instrumented via `prometheus-fastapi-instrumentator`. The C++ game server exposes custom Prometheus metrics on a dedicated port: connected socket count, active game count, total moves processed, move handling latency histogram, and error counts labeled by reason. Grafana dashboards are provisioned automatically on startup — no manual import required.

---

## Performance Results

Load test: 10 concurrent games, 10 moves each (100 total moves), measured end-to-end from WebSocket send to broadcast receipt by both players.

| Metric | Result |
|---|---|
| p50 | 1.76 ms |
| p95 | 8.00 ms |
| p99 | 12.40 ms |
| min | 0.73 ms |
| max | 12.60 ms |
| mean | 2.49 ms |
| Games completed | 10 / 10 |

See `loadtests/` for how to reproduce these numbers.

---

## Running Locally

**Prerequisites:** Docker + Docker Compose

```bash
# 1. Boot the full stack
docker compose --env-file infra/.env -f infra/docker-compose.yml up -d

# 2. Apply the database schema (first time only)
docker compose -f infra/docker-compose.yml exec -T postgres psql \
  -U <POSTGRES_USER> -d <POSTGRES_DB> < infra/tables.sql

# 3. Services
#   Frontend:   http://localhost:3000
#   API:        http://localhost:8000
#   Game server: ws://localhost:9001/ws
#   Prometheus: http://localhost:9090
#   Grafana:    http://localhost:3001  (admin / your GRAFANA_PASSWORD)
```

Copy `infra/.env.example` to `infra/.env` and fill in the required secrets before running.

---

## Repository Structure

```
Secure-Chess/
  proto/
    gamecontrol.proto         # gRPC contract between C++ and Python
  services/
    api/                      # FastAPI control plane (Python)
    gameserver/               # C++ WebSocket server
  frontend/                   # Next.js client
  infra/
    docker-compose.yml
    tables.sql                # initial schema
    migrations/               # subsequent schema changes
    grafana/                  # provisioned dashboards + datasources
    prometheus.yml            # scrape config
  scripts/                    # codegen + deliverable test scripts
  loadtests/                  # latency load test + rate limit tests
  docs/
    progress.md
```
