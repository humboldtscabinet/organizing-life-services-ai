#!/bin/bash
cd "$(dirname "$0")"

# Load API key from .env
API_KEY=$(grep '^OLS_API_KEY=' .env | cut -d'=' -f2)

echo "Restarting OLS API container..."
docker compose restart api
echo ""
echo "Waiting 10 seconds for startup..."
sleep 10

echo ""
echo "Health check:"
curl -s http://localhost:8000/health | python3 -m json.tool

if [ -n "$API_KEY" ]; then
    echo ""
    echo "Vision results:"
    curl -s http://localhost:8000/api/vision/results \
        -H "X-API-Key: $API_KEY" | python3 -m json.tool
fi

echo ""
echo "Press any key to close..."
read -n 1
