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
echo "  OLS Vision AI — Bulk Image Analysis"
echo '  Budget: $90 | All galleries'
echo '  Est. cost: ~$0.0045/image'
echo "  Est. time: 2-4 hours"
echo "=============================================="
echo ""
echo "Starting bulk analysis at $(date)..."
echo ""

# Run the bulk analysis with $90 budget and API key auth
curl -s -X POST "http://localhost:8000/api/vision/analyze/bulk?budget=90" \
    -H "X-API-Key: $API_KEY" | python3 -m json.tool

echo ""
echo "=============================================="
echo "Finished at $(date)"
echo "=============================================="
echo ""
echo "Exporting CSV..."
curl -s "http://localhost:8000/api/vision/export/csv" \
    -H "X-API-Key: $API_KEY" \
    -o "$(dirname "$0")/data/image_analysis_export.csv"
echo "CSV saved to data/image_analysis_export.csv"
echo ""
echo "Press any key to close..."
read -n 1
