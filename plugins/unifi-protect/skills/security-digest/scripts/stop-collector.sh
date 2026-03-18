#!/usr/bin/env bash
# Stop the security digest event collector daemon.
# Usage: stop-collector.sh [--state-dir DIR]
#
# Reads PID from $STATE_DIR/.collector.pid, sends SIGTERM,
# waits up to 3 seconds, then SIGKILL if needed.

# Defaults
STATE_DIR=""

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --state-dir)
      STATE_DIR="$2"
      shift 2
      ;;
    *)
      echo "{\"error\": \"Unknown argument: $1\"}"
      exit 1
      ;;
  esac
done

# Resolve state directory
if [[ -z "$STATE_DIR" ]]; then
  STATE_DIR="${UNIFI_SKILLS_STATE_DIR:-.claude/unifi-skills}"
fi

PID_FILE="${STATE_DIR}/.collector.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo '{"status": "not_running"}'
  exit 0
fi

pid=$(cat "$PID_FILE")

# Send SIGTERM for graceful shutdown
kill "$pid" 2>/dev/null || true

# Wait up to 3 seconds
for i in {1..30}; do
  if ! kill -0 "$pid" 2>/dev/null; then
    rm -f "$PID_FILE"
    echo '{"status": "stopped"}'
    exit 0
  fi
  sleep 0.1
done

# Escalate to SIGKILL
kill -9 "$pid" 2>/dev/null || true
sleep 0.2

if kill -0 "$pid" 2>/dev/null; then
  echo '{"status": "failed", "error": "process still running"}'
  exit 1
fi

rm -f "$PID_FILE"
echo '{"status": "stopped"}'
