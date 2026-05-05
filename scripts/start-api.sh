#!/usr/bin/env bash
# Stand up unifi-api-server locally and print everything you need to sign in.
#
# Wraps `docker compose -f docker/docker-compose-api.yml up --build -d` plus
# the post-boot key retrieval, so first-time setup is a single command.
#
# Run from anywhere inside the repo:
#   ./scripts/start-api.sh
#
# To stop:
#   docker compose -f docker/docker-compose-api.yml down
# To wipe and re-bootstrap (regenerates encryption + admin keys):
#   docker compose -f docker/docker-compose-api.yml down -v

set -euo pipefail

cd "$(dirname "$0")/.."

COMPOSE_FILE="docker/docker-compose-api.yml"
SERVICE="unifi-api-server"
URL_BASE="http://localhost:8089"
KEY_PATH="/var/lib/unifi-api/bootstrap-admin-key"

echo "→ Building and starting ${SERVICE}..."
docker compose -f "$COMPOSE_FILE" up --build -d

# Wait for the bootstrap key file (written by `migrate` before `serve` starts).
echo "→ Waiting for first-boot bootstrap..."
for _ in $(seq 1 30); do
  if docker compose -f "$COMPOSE_FILE" exec -T "$SERVICE" \
       test -f "$KEY_PATH" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

key=$(docker compose -f "$COMPOSE_FILE" exec -T "$SERVICE" \
        cat "$KEY_PATH" 2>/dev/null | tr -d '\r\n' || true)

# Wait for the HTTP listener (compose healthcheck takes ~30s to flip green;
# poll the endpoint directly so we don't block on healthcheck cadence).
echo "→ Waiting for HTTP listener..."
for _ in $(seq 1 30); do
  if curl -fsS -o /dev/null "$URL_BASE/v1/health" 2>/dev/null; then
    break
  fi
  sleep 1
done

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  unifi-api-server is up"
echo "════════════════════════════════════════════════════════════"
echo "  Admin UI:    $URL_BASE/admin/login"
echo "  REST docs:   $URL_BASE/v1/docs"
echo "  GraphQL:     $URL_BASE/v1/graphql"
echo ""
if [ -n "$key" ]; then
  echo "  Admin API key (paste into the Sign in form):"
  echo ""
  echo "    $key"
  echo ""
  echo "  This is the bootstrap admin key, persisted inside the"
  echo "  container at $KEY_PATH. After signing in, mint a"
  echo "  personal key via the Keys tab and revoke 'bootstrap-admin'."
else
  echo "  Bootstrap key not yet available. Once the container is healthy:"
  echo "    docker compose -f $COMPOSE_FILE exec \\"
  echo "      $SERVICE cat $KEY_PATH"
fi
echo "════════════════════════════════════════════════════════════"
