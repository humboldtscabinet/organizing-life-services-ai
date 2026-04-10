#!/bin/bash
cd "$(dirname "$0")"

# Load API key from .env
API_KEY=$(grep '^OLS_API_KEY=' .env | cut -d'=' -f2)

echo "=============================================="
echo "  Rebuilding OLS API v0.5.0 (Auth Enabled)"
echo "=============================================="
echo ""

# Rebuild the API container
docker compose up -d --build api

echo ""
echo "Waiting 20 seconds for API startup..."
sleep 20

echo ""
echo "=== TEST 1: Health check (no auth needed) ==="
curl -s http://localhost:8000/health | python3 -m json.tool

echo ""
echo "=== TEST 2: Unauthenticated request (should return 401) ==="
curl -s -w "\nHTTP Status: %{http_code}\n" http://localhost:8000/api/vision/results | python3 -m json.tool 2>/dev/null || echo "(raw response above)"

echo ""
echo "=== TEST 3: Authenticated request (should return results) ==="
curl -s -w "\nHTTP Status: %{http_code}\n" http://localhost:8000/api/vision/results \
    -H "X-API-Key: $API_KEY" | python3 -m json.tool 2>/dev/null || echo "(raw response above)"

echo ""
echo "=== TEST 4: Wrong API key (should return 403) ==="
curl -s -w "\nHTTP Status: %{http_code}\n" http://localhost:8000/api/vision/results \
    -H "X-API-Key: wrong-key-test" | python3 -m json.tool 2>/dev/null || echo "(raw response above)"

echo ""
echo "=============================================="
echo "  Auth Tests Complete"
echo "=============================================="
echo ""
echo "Your API key: $API_KEY"
echo "Use it in all requests: -H 'X-API-Key: $API_KEY'"
echo ""
echo "Press any key to close..."
read -n 1
