#!/bin/bash
set -e

# Identify current active environment
CURRENT_UPSTREAM=$(grep -o "api_[a-z]*" deployment/nginx/conf.d/upstream.conf | head -n 1)

if [ "$CURRENT_UPSTREAM" == "api_blue" ]; then
    BROKEN_ENV="green"
    SAFE_ENV="blue"
else
    BROKEN_ENV="blue"
    SAFE_ENV="green"
fi

echo "Rolling back to $SAFE_ENV (removing $BROKEN_ENV)"

# Ensure NGINX points to safe environment
echo -e "upstream api_upstream { server api_$SAFE_ENV:8000; }\nupstream frontend_upstream { server frontend_$SAFE_ENV:3000; }" > deployment/nginx/conf.d/upstream.conf
docker exec ai_job_agent_nginx nginx -s reload || true

# Stop the broken environment
docker compose -f deployment/docker-compose.prod.yml stop frontend_$BROKEN_ENV api_$BROKEN_ENV celery_worker_$BROKEN_ENV browser_worker_$BROKEN_ENV
docker compose -f deployment/docker-compose.prod.yml rm -f frontend_$BROKEN_ENV api_$BROKEN_ENV celery_worker_$BROKEN_ENV browser_worker_$BROKEN_ENV

echo "Rollback complete."
