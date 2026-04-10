#!/bin/bash
# Import the OLS Daily Data Sync workflow into n8n
cd "$(dirname "$0")"

echo "Importing OLS Daily Data Sync workflow into n8n..."
docker exec -i organizing-life-services-ai-n8n-1 n8n import:workflow --input=/dev/stdin < workflows/ols_daily_data_sync.json

if [ $? -eq 0 ]; then
  echo ""
  echo "Workflow imported successfully!"
  echo "Open http://localhost:5678 to view and activate it."
  echo ""
  echo "After importing:"
  echo "  1. Log into n8n at http://localhost:5678"
  echo "  2. Open the 'OLS Daily Data Sync' workflow"
  echo "  3. Click the toggle in the top-right to activate it"
else
  echo ""
  echo "Import failed. Make sure Docker containers are running:"
  echo "  cd organizing-life-services-ai && docker-compose up -d"
fi
