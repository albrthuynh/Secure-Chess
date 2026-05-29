# Secure Chess — Frontend

Next.js 16 frontend for the Secure Chess platform. Currently exposes the load demo cockpit at `/`.

## What's real vs. simulated

**The home page cockpit (`/`) → intentionally simulated.**
The chess boards, latency numbers (p50/p95/p99), event log, and game counters are all generated locally in JavaScript. No network requests are made. It's a demo visualization of what the system looks like under load, not a live feed.

The *actual* real-time performance data lives in **Grafana** (`http://localhost:3001`), which reads from Prometheus metrics emitted by the C++ game server.

## Setup

```bash
cp .env.example .env.local
npm install
npm run dev
```

Start the full stack first:

```bash
cd ../infra && docker compose up
```
