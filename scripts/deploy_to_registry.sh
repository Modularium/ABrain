#!/usr/bin/env bash
# Build and push canonical runtime images to container registry
set -e
cd "$(dirname "$0")/.."

REGISTRY="${REGISTRY:-ghcr.io/ecospherNetwork/agent-nn}"
SERVICES=(dispatcher registry session_manager vector_store llm_gateway routing_agent api_gateway user_manager)

./scripts/build_and_test.sh

for svc in "${SERVICES[@]}"; do
  docker build -t "$REGISTRY/$svc:latest" \
    -f Dockerfile . --build-arg SERVICE="$svc"
  docker push "$REGISTRY/$svc:latest"
done
