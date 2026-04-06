#!/bin/bash

# Rate Limiting Test Script for Secure Chess API
# I will be transparent and say that AI generated this test script...
# I tested it manually, and figured that I wanted to automate it, but I felt lazy so here it is the test script
# Tests sign-up (3 req/hour) and sign-in (5 req/15min) endpoints

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

API_URL="${API_URL:-http://localhost:8000}"
PASSED=0
FAILED=0

# Option to clear rate limits before testing
if [ "$1" == "--clear" ]; then
    echo -e "${YELLOW}Clearing existing rate limit keys from Redis...${NC}"
    # Get Redis password from environment or Docker container
    REDIS_PASS=$(docker exec infra-api-server-1 sh -c 'echo $REDIS_URL' 2>/dev/null | cut -d: -f3 | cut -d@ -f1)
    if [ -n "$REDIS_PASS" ]; then
        docker exec secure_chess_redis redis-cli -a "$REDIS_PASS" --scan --pattern "rate_limit:*" 2>/dev/null | while read key; do
            docker exec secure_chess_redis redis-cli -a "$REDIS_PASS" DEL "$key" > /dev/null 2>&1
        done
        echo -e "${GREEN}✓ Rate limits cleared${NC}"
    else
        echo -e "${RED}✗ Could not get Redis password${NC}"
    fi
    echo ""
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Rate Limiting Test Suite${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Helper function to make a request and capture status code
make_request() {
    local endpoint=$1
    local data=$2
    local expected_status=$3
    
    response=$(curl -s -w "\n%{http_code}" -X POST "${API_URL}${endpoint}" \
        -H "Content-Type: application/json" \
        -d "$data")
    
    # Split response body and status code (macOS compatible)
    status_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    echo "$status_code"
}

# Test 1: Sign-in Rate Limit (5 requests per 15 minutes)
test_signin_rate_limit() {
    echo -e "${YELLOW}Test 1: Sign-in Rate Limit (5 req/15min)${NC}"
    echo "Making 6 sign-in requests..."
    echo ""
    
    local fail_count=0
    
    # First 5 requests should succeed (or return 401 for invalid creds)
    for i in {1..5}; do
        status=$(make_request "/auth/sign-in" '{"username":"testuser","password":"wrongpass"}' "401")
        
        if [ "$status" == "401" ]; then
            echo -e "  Request $i: ${GREEN}✓ PASSED${NC} (Status: $status - Invalid credentials as expected)"
        elif [ "$status" == "429" ]; then
            echo -e "  Request $i: ${RED}✗ FAILED${NC} (Status: $status - Rate limited too early!)"
            ((fail_count++))
        else
            echo -e "  Request $i: ${YELLOW}⚠ WARNING${NC} (Status: $status - Unexpected status)"
        fi
    done
    
    # 6th request should be rate limited
    status=$(make_request "/auth/sign-in" '{"username":"testuser","password":"wrongpass"}' "429")
    
    if [ "$status" == "429" ]; then
        echo -e "  Request 6: ${GREEN}✓ PASSED${NC} (Status: $status - Rate limited as expected)"
    else
        echo -e "  Request 6: ${RED}✗ FAILED${NC} (Status: $status - Should be rate limited!)"
        ((fail_count++))
    fi
    
    echo ""
    
    if [ $fail_count -eq 0 ]; then
        echo -e "${GREEN}✓ Sign-in rate limit test PASSED${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ Sign-in rate limit test FAILED${NC}"
        ((FAILED++))
    fi
    
    echo ""
}

# Test 2: Sign-up Rate Limit (3 requests per hour)
test_signup_rate_limit() {
    echo -e "${YELLOW}Test 2: Sign-up Rate Limit (3 req/1hour)${NC}"
    echo "Making 4 sign-up requests..."
    echo ""
    
    local fail_count=0
    local timestamp=$(date +%s)
    
    # First 3 requests should succeed (or return error but not 429)
    for i in {1..3}; do
        status=$(make_request "/auth/sign-up" "{\"username\":\"testuser${timestamp}_${i}\",\"email\":\"test${timestamp}_${i}@example.com\",\"password\":\"password123\"}" "201")
        
        if [ "$status" == "201" ] || [ "$status" == "409" ] || [ "$status" == "500" ]; then
            echo -e "  Request $i: ${GREEN}✓ PASSED${NC} (Status: $status - Not rate limited)"
        elif [ "$status" == "429" ]; then
            echo -e "  Request $i: ${RED}✗ FAILED${NC} (Status: $status - Rate limited too early!)"
            ((fail_count++))
        else
            echo -e "  Request $i: ${YELLOW}⚠ WARNING${NC} (Status: $status - Unexpected status)"
        fi
    done
    
    # 4th request should be rate limited
    status=$(make_request "/auth/sign-up" "{\"username\":\"testuser${timestamp}_4\",\"email\":\"test${timestamp}_4@example.com\",\"password\":\"password123\"}" "429")
    
    if [ "$status" == "429" ]; then
        echo -e "  Request 4: ${GREEN}✓ PASSED${NC} (Status: $status - Rate limited as expected)"
    else
        echo -e "  Request 4: ${RED}✗ FAILED${NC} (Status: $status - Should be rate limited!)"
        ((fail_count++))
    fi
    
    echo ""
    
    if [ $fail_count -eq 0 ]; then
        echo -e "${GREEN}✓ Sign-up rate limit test PASSED${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ Sign-up rate limit test FAILED${NC}"
        ((FAILED++))
    fi
    
    echo ""
}

# Check if API is running
echo -e "${BLUE}Checking API availability...${NC}"
if ! curl -s "${API_URL}/" > /dev/null; then
    echo -e "${RED}✗ API is not reachable at ${API_URL}${NC}"
    echo -e "${YELLOW}Make sure Docker containers are running:${NC}"
    echo "  docker compose --env-file infra/.env -f infra/docker-compose.yml up -d"
    exit 1
fi
echo -e "${GREEN}✓ API is reachable${NC}"
echo ""

# Run tests
test_signin_rate_limit
test_signup_rate_limit

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Test Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Tests Passed: ${GREEN}${PASSED}${NC}"
echo -e "Tests Failed: ${RED}${FAILED}${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All rate limiting tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed. Check the output above.${NC}"
    exit 1
fi
