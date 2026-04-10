#!/bin/bash
cd "$(dirname "$0")"

# Load API key from .env
API_KEY=$(grep '^OLS_API_KEY=' .env | cut -d'=' -f2)

echo "=============================================="
echo "  Rebuilding OLS API (v0.5.0 — Auth Enabled)"
echo "=============================================="
echo ""

# Rebuild the API container
docker compose up -d --build api

echo ""
echo "Waiting 20 seconds for API startup..."
sleep 20

echo ""
echo "Health check (no auth needed):"
curl -s http://localhost:8000/health | python3 -m json.tool

echo ""
if [ -z "$API_KEY" ]; then
    echo "WARNING: OLS_API_KEY not found in .env — API will auto-generate one"
    echo "Check Docker logs: docker compose logs api | grep OLS_API_KEY"
else
    echo "Auth test (should return results):"
    curl -s http://localhost:8000/api/vision/results \
        -H "X-API-Key: $API_KEY" | python3 -m json.tool
    echo ""
    echo "Auth rejection test (should return 401):"
    curl -s http://localhost:8000/api/vision/results | python3 -m json.tool
fi

echo ""
echo "Press any key to close..."
read -n 1
