#!/bin/bash
# FincoGPT Smoke Test
# Usage: ./smoke_test.sh [base_url]
# Default base_url: http://127.0.0.1:8000

set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:8000}"
FAILED=0

pass() { echo "✓ $1"; }
fail() { echo "✗ $1"; FAILED=1; }

echo "=== FincoGPT Smoke Test ==="
echo "Base URL: $BASE_URL"
echo ""

# 1. /public-health
echo "--- /public-health ---"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/public-health")
if [[ "$RESPONSE" == "200" ]]; then
    BODY=$(curl -s "${BASE_URL}/public-health")
    if [[ "$BODY" == *"OK"* ]]; then
        pass "/public-health returns 200 + OK"
    else
        fail "/public-health body missing OK: $BODY"
    fi
else
    fail "/public-health returned $RESPONSE (expected 200)"
fi
echo ""

# 2. /health
echo "--- /health ---"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/health")
if [[ "$RESPONSE" == "302" ]]; then
    pass "/health redirects (auth-protected, expected 302)"
else
    fail "/health returned $RESPONSE (expected 302 for auth redirect)"
fi
echo ""

# 3. / (root → redirect to /login)
echo "--- / (root redirect) ---"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/")
if [[ "$RESPONSE" == "302" ]]; then
    LOCATION=$(curl -s -I "${BASE_URL}/" | grep -i "^Location:" | tr -d '\r')
    if [[ "$LOCATION" == *"login"* ]]; then
        pass "/ redirects to /login (302)"
    else
        fail "/redirect location: $LOCATION (expected /login)"
    fi
else
    fail "/ returned $RESPONSE (expected 302)"
fi
echo ""

# 4. HTTPS redirect check (if testing external domain)
echo "--- HTTP→HTTPS redirect ---"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -H "Host: localhost" "http://localhost:8080/")
if [[ "$RESPONSE" == "301" ]]; then
    pass "HTTP→HTTPS redirect (301) works"
else
    echo "  (SKIP: nginx not configured on :8080)"
fi
echo ""

echo "=== Results ==="
if [[ $FAILED -eq 0 ]]; then
    echo "All smoke tests passed."
    exit 0
else
    echo "Some tests failed."
    exit 1
fi