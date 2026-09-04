#!/bin/sh
# Milestone 6 demo entrypoint: creates one real investigation against the
# committed golden fixture dataset and prints where to watch it. Assumes
# `make up && make migrate && make ingest-fixtures` (or the full
# `make ingest SOURCE=data/raw` dataset) has already run — this script
# only depends on the API being reachable, not on which dataset is loaded.
set -eu

API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"
WEB_BASE_URL="${WEB_BASE_URL:-http://localhost:3000}"

echo "Waiting for the API at ${API_BASE_URL}..."
for _ in $(seq 1 30); do
    if curl -s -m 2 "${API_BASE_URL}/api/health" > /dev/null 2>&1; then
        break
    fi
    sleep 1
done

if ! curl -s -m 2 "${API_BASE_URL}/api/health" > /dev/null 2>&1; then
    echo "API is not reachable at ${API_BASE_URL} — run \`make up\` first." >&2
    exit 1
fi

echo "Creating a demo investigation (fixture dataset's Jan 2018 vs Dec 2017)..."
RESPONSE=$(curl -s -X POST "${API_BASE_URL}/api/investigations" \
    -H "Content-Type: application/json" \
    -d '{
        "metric": "product_revenue",
        "current_period": {"start": "2018-01-01", "end": "2018-01-31"},
        "comparison_period": {"start": "2017-12-01", "end": "2017-12-31"},
        "question": "Why did revenue decline?"
    }')

INVESTIGATION_ID=$(echo "$RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin)['investigation_id'])")

echo ""
echo "Investigation created: ${INVESTIGATION_ID}"
echo "Watch it live at: ${WEB_BASE_URL}/investigations/${INVESTIGATION_ID}"
echo "Or poll the API:  ${API_BASE_URL}/api/investigations/${INVESTIGATION_ID}"
echo ""
echo "It runs against a local Ollama model — this can take anywhere from"
echo "~30s to a couple of minutes depending on the model and hardware."
