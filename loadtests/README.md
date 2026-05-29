## Purpose

This directory contains load tests and validation scripts for the Secure Chess API.

## Available Tests

### Rate Limiting Test (`test_rate_limiting.sh`)

Validates that the API rate limiting is working correctly for authentication endpoints.

**What it tests:**
- `/auth/sign-in` - 5 requests per 15 minutes (IP-based)
- `/auth/sign-up` - 3 requests per 1 hour (IP-based)

**Prerequisites:**
- Docker containers must be running
- API must be accessible at `http://localhost:8000` (or set `API_URL` env var)

**Usage:**
```bash
# Run the test
./loadtests/test_rate_limiting.sh

# Clear rate limits before running (recommended if you've been testing manually)
./loadtests/test_rate_limiting.sh --clear

# Or with custom API URL
API_URL=http://localhost:8080 ./loadtests/test_rate_limiting.sh
```

**Example recent output:**
```
========================================
  Rate Limiting Test Suite
========================================

✓ API is reachable

Test 1: Sign-in Rate Limit (5 req/15min)
  Request 1: ✓ PASSED (Status: 401)
  Request 2: ✓ PASSED (Status: 401)
  Request 3: ✓ PASSED (Status: 401)
  Request 4: ✓ PASSED (Status: 401)
  Request 5: ✓ PASSED (Status: 401)
  Request 6: ✓ PASSED (Status: 429 - Rate limited)

Test 2: Sign-up Rate Limit (3 req/1hour)
  Request 1: ✓ PASSED (Status: 201)
  Request 2: ✓ PASSED (Status: 201)
  Request 3: ✓ PASSED (Status: 201)
  Request 4: ✓ PASSED (Status: 429 - Rate limited)

========================================
  Test Summary
========================================
Tests Passed: 2
Tests Failed: 0

✓ All rate limiting tests passed!
```

**Note:** After running the test, you may need to wait for rate limit windows to expire or clear Redis keys before running again:
```bash
# Clear all rate limit keys from Redis
docker exec secure_chess_redis redis-cli -a [YOUR_PASSWORD] EVAL "return redis.call('del', unpack(redis.call('keys', 'rate_limit:*')))" 0
```

---


### Move Handling Latency Load Test (`latency_load_test.py`)

Spins up N total chess games with bounded concurrency and measures round-trip WebSocket latency for each move — from when the client sends the move to when both players have received the broadcast. Reports p50/p95/p99.

**What it measures:**
- Round-trip move latency: WebSocket send → C++ move validation → broadcast received by both players
- Runs N games with bounded `asyncio` concurrency to simulate real load
- Clears stale API `rate_limit:*` Redis keys before starting
- Throttles account creation/sign-in/matchmaking setup separately from gameplay
- Staggers WebSocket joins so the local game server is not flooded by handshakes
- Adds a short delay between half-moves so the test stays under the WebSocket rate limit
- Each game plays 37 moves (Ruy Lopez opening line) — all legal, alternating white/black

**Prerequisites:**
- All Docker containers must be running (`docker compose up -d`)
- Install test dependencies (separate from the main service requirements):
```bash
pip install -r loadtests/requirements.txt
```

**Usage:**
```bash
python3 loadtests/latency_load_test.py
```

To increase load, edit `N_GAMES` or `CONCURRENCY` at the top of the script.

**Example recent output:**
```
cleared rate limits: 0 keys

secure-chess — move handling latency load test
  total games      : 100
  concurrency      : 50
  setup concurrency: 5
  join concurrency : 1
  move delay       : 0.12s
  join timeout     : 30s
  moves per game   : 37
  total moves      : 3700

  games completed  : 100/100
  moves measured   : 3700
  total test time  : 115.5s

move handling latency  (WebSocket send → broadcast received)
  p50  :  1.20 ms
  p95  :  5.06 ms
  p99  :  7.09 ms
  min  :  0.38 ms
  max  :  13.96 ms
  mean :  1.79 ms
```

**Note:** Numbers will be green (< 10ms), yellow (< 50ms), or red (≥ 50ms) in the terminal output. On a local Docker setup you should see green across the board. The p99 under concurrent load is the key number — it tells you the worst-case experience any player would have during peak usage.
