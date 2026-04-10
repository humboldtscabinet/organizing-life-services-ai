#!/bin/bash
cd "$(dirname "$0")"

# Load API key from .env
API_KEY=$(grep '^OLS_API_KEY=' .env | cut -d'=' -f2)
if [ -z "$API_KEY" ]; then
    echo "ERROR: OLS_API_KEY not found in .env file"
    echo "Press any key to close..."
    read -n 1
    exit 1
fi

echo "=============================================="
echo "  OLS SEO Update — Alt Text Push to Shopify"
echo "=============================================="
echo ""

# Step 1: Rebuild API
echo ">>> Rebuilding API with alt text push endpoint..."
docker compose up -d --build api
echo "Waiting 20 seconds for startup..."
sleep 20

echo ""
echo "Health check:"
curl -s http://localhost:8000/health | python3 -m json.tool
echo ""

# Step 2: Push alt text to Shopify Files
echo "=============================================="
echo ">>> Pushing alt text to Shopify Files..."
echo "  Matching 12,273 analyzed images to Shopify"
echo "  This may take 5-15 minutes..."
echo "=============================================="
echo ""
curl -s -X POST "http://localhost:8000/api/vision/push-alt-text" \
    -H "X-API-Key: $API_KEY" | python3 -m json.tool
echo ""

echo "=============================================="
echo "  Alt text push complete!"
echo "=============================================="
echo ""
echo "Press any key to close..."
read -n 1
