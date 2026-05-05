#!/usr/bin/env bash
# Build the unifi-api-server Docker image, bring it up via the local-dev
# compose, run the GET-endpoint sweep, fail on any 5xx or network error,
# tear down on exit.
#
# Optional env vars to exercise a real controller (else only public
# endpoints + capability_mismatch paths get coverage):
#   UNIFI_HOST       e.g. 10.29.13.1
#   UNIFI_USERNAME   controller local account
#   UNIFI_PASSWORD   ...
#   UNIFI_API_TOKEN  optional; required for DPI endpoints to return 200
#                    instead of 501 api_key_required
#   UNIFI_VERIFY_TLS default false
#
# When the controller env vars are set, the script registers a controller
# via POST /v1/controllers before sweeping; without them, the sweep still
# verifies that the API container starts cleanly and that
# unauthenticated paths plus 409/501 cases all behave correctly.
#
# Usage:
#   ./scripts/smoke-api-image.sh
#
# CI: this is the harness that should run on every release tag. It
# closes the gap left by scripts/live_api_smoke.py which boots in-process.

set -euo pipefail

cd "$(dirname "$0")/.."

COMPOSE_FILE="docker/docker-compose-api.yml"
SERVICE="unifi-api-server"
URL_BASE="http://localhost:8089"

cleanup() {
  echo ""
  echo "→ Tearing down..."
  docker compose -f "$COMPOSE_FILE" down -v >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "→ Wiping any prior state and rebuilding image..."
docker compose -f "$COMPOSE_FILE" down -v >/dev/null 2>&1 || true
docker compose -f "$COMPOSE_FILE" up --build -d

echo "→ Waiting for HTTP listener..."
for _ in $(seq 1 30); do
  if curl -fsS -o /dev/null "$URL_BASE/v1/health" 2>/dev/null; then
    break
  fi
  sleep 1
done

# Pull bootstrap admin key (always present on first boot of a wiped volume).
admin_key=$(docker compose -f "$COMPOSE_FILE" exec -T "$SERVICE" \
              cat /var/lib/unifi-api/bootstrap-admin-key 2>/dev/null | tr -d '\r\n' || true)
if [ -z "$admin_key" ]; then
  echo "FAIL: bootstrap admin key not found — container did not start cleanly" >&2
  docker logs "$SERVICE" 2>&1 | tail -40
  exit 1
fi
echo "→ Bootstrap admin key acquired"

# Optionally register a real controller so the sweep can hit live endpoints.
controller_id=""
if [ -n "${UNIFI_HOST:-}" ] && [ -n "${UNIFI_USERNAME:-}" ] && [ -n "${UNIFI_PASSWORD:-}" ]; then
  echo "→ Registering controller against $UNIFI_HOST..."
  body=$(cat <<JSON
{
  "name": "smoke-test",
  "base_url": "https://${UNIFI_HOST}:443",
  "product_kinds": ["network"],
  "username": "${UNIFI_USERNAME}",
  "password": "${UNIFI_PASSWORD}",
  "api_token": "${UNIFI_API_TOKEN:-}",
  "verify_tls": ${UNIFI_VERIFY_TLS:-false},
  "is_default": true
}
JSON
)
  registration=$(curl -fsS -X POST -H "Authorization: Bearer $admin_key" \
    -H "Content-Type: application/json" -d "$body" \
    "$URL_BASE/v1/controllers" || true)
  if [ -z "$registration" ]; then
    echo "FAIL: controller registration returned empty/error response" >&2
    exit 1
  fi
  controller_id=$(printf '%s' "$registration" | \
                  python3 -c "import json,sys;print(json.load(sys.stdin)['id'])" || true)
  echo "→ Controller registered: $controller_id"
fi

echo ""
echo "→ Running endpoint sweep..."
echo ""
if [ -n "$controller_id" ]; then
  python3 scripts/api_image_smoke.py "$admin_key" "$controller_id"
else
  python3 scripts/api_image_smoke.py "$admin_key"
fi
