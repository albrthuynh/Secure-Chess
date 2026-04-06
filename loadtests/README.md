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

**Expected output:**
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


