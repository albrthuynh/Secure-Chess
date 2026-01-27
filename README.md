# Secure Chess

Secure Chess is a production-style real-time chess platform: a high-performance C++ WebSocket game server runs authoritative gameplay, while a FastAPI control plane handles auth, matchmaking, ratings, and persistence. Services communicate via gRPC and include Prometheus/Grafana observability for p95/p99 latency and reliability.

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

### Client
- **Next.js (TypeScript)**

### Control Plane (Backend)
- **FastAPI (Python)** — REST API
- **grpc.aio (Python)** — gRPC server (same service, separate port)

### Real-Time Game Service
- **C++ WebSocket Server** — **uWebSockets** (authoritative gameplay)
- **gRPC C++ client** — service-to-service calls into the control plane

### Data / Caching
- **PostgreSQL** — source of truth (users, matches, games, ratings, audit logs)
- **Redis** — rate limiting, presence, matchmaking queue, ephemeral state

### Observability
- **Prometheus** — metrics scraping (API + game server)
- **Grafana** — dashboards (latency, socket count, errors, CPU/mem)

### Infra
- **Docker + Docker Compose** — local dev + one-command boot

---

## Repository Structure

```
knightshield/
  README.md
  docs/
    architecture.md
    threat-model.md
    perf-report.md
  proto/
    gamecontrol.proto
  services/
    api/                      # FastAPI + gRPC server (Python)
      app/
      tests/
      Dockerfile
      pyproject.toml
    gameserver/               # C++ WebSocket server + gRPC client
      src/
      include/
      tests/
      Dockerfile
      CMakeLists.txt
  client/                        # Next.js frontend
    src/
    package.json
    Dockerfile
  infra/
    docker-compose.yml
    grafana/
    prometheus/
  scripts/
    dev.sh
    lint.sh
    generate_protos.sh
  loadtests/
    websocket/                # k6 / custom load harness
    api/
```
