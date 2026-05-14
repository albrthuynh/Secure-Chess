#!/usr/bin/env bash
# Tests the Week 2 deliverable: two players match and the requester receives {match_id, ws_url, ticket}
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REDIS_PASSWORD=$(grep "^REDIS_PASSWORD=" "$SCRIPT_DIR/../infra/.env" | cut -d= -f2- | tr -d '"')

redis_cli() {
  docker exec secure_chess_redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning "$@"
}

echo -e "${BLUE}--- Clearing rate limit keys for a clean test run ---${NC}"
mapfile -t RATE_LIMIT_KEYS < <(redis_cli --scan --pattern "rate_limit:*")
if [ "${#RATE_LIMIT_KEYS[@]}" -gt 0 ]; then
  redis_cli DEL "${RATE_LIMIT_KEYS[@]}" >/dev/null
  printf "cleared: %s\n" "${RATE_LIMIT_KEYS[*]}"
else
  echo "no rate limit keys found (already clean)"
fi
echo ""

post_json() {
  local output_file=$1
  local endpoint=$2
  local data=$3
  shift 3

  curl -sS -o "$output_file" -w "%{http_code}" -X POST "$BASE_URL$endpoint" \
    -H "Content-Type: application/json" \
    "$@" \
    -d "$data"
}

signup() {
  local username=$1 email=$2 password=$3
  local http_status
  http_status=$(post_json /tmp/signup_body.json "/auth/sign-up" "{\"username\": \"$username\", \"email\": \"$email\", \"password\": \"$password\"}")

  if [ "$http_status" = "201" ]; then
    echo "  created $username"
  elif [ "$http_status" = "409" ]; then
    echo "  $username already exists (ok)"
  else
    echo -e "  ${RED}sign-up failed for $username (HTTP $http_status):${NC}"
    cat /tmp/signup_body.json
    exit 1
  fi
}

echo -e "${BLUE}--- Step 1: Sign up two test players ---${NC}"
signup "testplayer1" "player1@test.com" "password123"
signup "testplayer2" "player2@test.com" "password123"
echo ""

echo -e "${BLUE}--- Step 2: Sign in both players ---${NC}"
post_json /tmp/signin1_body.json "/auth/sign-in" '{"username": "testplayer1", "password": "password123"}' >/tmp/signin1_status.txt
USER1=$(cat /tmp/signin1_body.json)
if ! TOKEN1=$(jq -er '.access_token // empty' /tmp/signin1_body.json); then
  echo -e "${RED}sign-in failed for testplayer1 (HTTP $(cat /tmp/signin1_status.txt)):${NC}"
  cat /tmp/signin1_body.json
  exit 1
fi
echo "  player1 token: $TOKEN1"

post_json /tmp/signin2_body.json "/auth/sign-in" '{"username": "testplayer2", "password": "password123"}' >/tmp/signin2_status.txt
USER2=$(cat /tmp/signin2_body.json)
if ! TOKEN2=$(jq -er '.access_token // empty' /tmp/signin2_body.json); then
  echo -e "${RED}sign-in failed for testplayer2 (HTTP $(cat /tmp/signin2_status.txt)):${NC}"
  cat /tmp/signin2_body.json
  exit 1
fi
echo "  player2 token: $TOKEN2"
echo ""

echo -e "${BLUE}--- Step 3: Player 1 enters matchmaking queue (expect: queued=true) ---${NC}"
curl -s -X POST "$BASE_URL/matchmaking/request" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN1" \
  -d '{"time_control": "10+0", "increment": 0}' | jq '.'
echo ""

echo -e "${BLUE}--- Step 4: Player 2 enters queue (expect: match_found with ws_url + ticket) ---${NC}"
MATCH=$(curl -s -X POST "$BASE_URL/matchmaking/request" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN2" \
  -d '{"time_control": "10+0", "increment": 0}')
echo "$MATCH" | jq '.'
echo ""

echo -e "${GREEN}--- Week 2 deliverable fields ---${NC}"
echo "match_id : $(echo "$MATCH" | jq -r '.match_id')"
echo "ws_url   : $(echo "$MATCH" | jq -r '.ws_url')"
echo "ticket   : $(echo "$MATCH" | jq -r '.ticket')"
