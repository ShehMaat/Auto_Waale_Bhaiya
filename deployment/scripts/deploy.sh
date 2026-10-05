#!/bin/bash
set -e

# Identify current active environment
CURRENT_UPSTREAM=$(grep -o "api_[a-z]*" deployment/nginx/conf.d/upstream.conf | head -n 1)

if [ "$CURRENT_UPSTREAM" == "api_blue" ]; then
    NEXT_ENV="green"
    OLD_ENV="blue"
else
    NEXT_ENV="blue"
    OLD_ENV="green"
fi

echo "Current environment: $OLD_ENV. Deploying to: $NEXT_ENV"

# Start next release containers
docker compose -f deployment/docker-compose.prod.yml up -d --build api_$NEXT_ENV celery_worker_$NEXT_ENV browser_worker_$NEXT_ENV

# Wait for N+1 API to become healthy
echo "Waiting for api_$NEXT_ENV to become healthy..."
RETRIES=30
while [ $RETRIES -gt 0 ]; do
    HEALTH=$(docker inspect --format='{{json .State.Health.Status}}' "ai_job_agent_api_$NEXT_ENV" || echo "\"unknown\"")
    if [ "$HEALTH" == "\"healthy\"" ]; then
        break
    fi
    sleep 2
    RETRIES=$((RETRIES-1))
done

if [ $RETRIES -eq 0 ]; then
    echo "api_$NEXT_ENV failed to become healthy. Rolling back."
    docker compose -f deployment/docker-compose.prod.yml stop api_$NEXT_ENV celery_worker_$NEXT_ENV browser_worker_$NEXT_ENV
    exit 1
fi

echo "api_$NEXT_ENV is healthy. Swapping NGINX traffic."

# Update NGINX upstream to the next release
echo "upstream api_upstream { server api_$NEXT_ENV:8000; }" > deployment/nginx/conf.d/upstream.conf

# Reload NGINX
docker exec ai_job_agent_nginx nginx -s reload
echo "Traffic switched to $NEXT_ENV."

# ---> ADDED FOR GATE 2 <---
echo "=== MEASURING BLUE+GREEN OVERLAP ==="
.venv/Scripts/python.exe deployment/scripts/measure_resources.py BLUE_PLUS_GREEN

echo "=== RUNNING BENCHMARK DURING OVERLAP ==="
.venv/Scripts/python.exe deployment/scripts/benchmark.py 100 500
# --------------------------

# Send graceful stop to old release
echo "Draining old release: $OLD_ENV..."
docker compose -f deployment/docker-compose.prod.yml stop -t 30 api_$OLD_ENV celery_worker_$OLD_ENV browser_worker_$OLD_ENV
docker compose -f deployment/docker-compose.prod.yml rm -f api_$OLD_ENV celery_worker_$OLD_ENV browser_worker_$OLD_ENV

echo "Deployment complete."
