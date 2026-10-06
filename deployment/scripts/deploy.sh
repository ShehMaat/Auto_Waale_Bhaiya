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
docker compose -f deployment/docker-compose.prod.yml up -d --build frontend_$NEXT_ENV api_$NEXT_ENV celery_worker_$NEXT_ENV browser_worker_$NEXT_ENV

# Wait for N+1 API and Frontend to become healthy
echo "Waiting for api_$NEXT_ENV and frontend_$NEXT_ENV to become healthy..."
RETRIES=${DEPLOY_RETRIES:-30}
while [ $RETRIES -gt 0 ]; do
    API_HEALTH=$(docker inspect --format='{{json .State.Health.Status}}' "ai_job_agent_api_$NEXT_ENV" || echo "\"unknown\"")
    FRONTEND_HEALTH=$(docker inspect --format='{{json .State.Health.Status}}' "ai_job_agent_frontend_$NEXT_ENV" || echo "\"unknown\"")
    if [ "$API_HEALTH" == "\"healthy\"" ] && [ "$FRONTEND_HEALTH" == "\"healthy\"" ]; then
        break
    fi
    sleep 2
    RETRIES=$((RETRIES-1))
done

if [ $RETRIES -eq 0 ]; then
    echo "api_$NEXT_ENV or frontend_$NEXT_ENV failed to become healthy. Rolling back."
    docker compose -f deployment/docker-compose.prod.yml stop frontend_$NEXT_ENV api_$NEXT_ENV celery_worker_$NEXT_ENV browser_worker_$NEXT_ENV
    exit 1
fi

echo "Both api_$NEXT_ENV and frontend_$NEXT_ENV are healthy. Swapping NGINX traffic."

# Update NGINX upstream to the next release
echo -e "upstream api_upstream { server api_$NEXT_ENV:8000; }\nupstream frontend_upstream { server frontend_$NEXT_ENV:3000; }" > deployment/nginx/conf.d/upstream.conf

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
docker compose -f deployment/docker-compose.prod.yml stop -t 30 frontend_$OLD_ENV api_$OLD_ENV celery_worker_$OLD_ENV browser_worker_$OLD_ENV
docker compose -f deployment/docker-compose.prod.yml rm -f frontend_$OLD_ENV api_$OLD_ENV celery_worker_$OLD_ENV browser_worker_$OLD_ENV

echo "Deployment complete."
