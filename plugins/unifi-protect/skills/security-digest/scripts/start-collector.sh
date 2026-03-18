#!/usr/bin/env bash
# Start the security digest event collector daemon.
# Usage: start-collector.sh [--state-dir DIR] [--poll-interval N] [--servers LIST] [--timeout N]
#
# Launches collector.py as a background daemon via nohup.
# Writes PID to $STATE_DIR/.collector.pid.
# Outputs JSON with status on success.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Defaults
STATE_DIR=""
POLL_INTERVAL=10
SERVERS="protect,network"
TIMEOUT=1800  # 30 minutes

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --state-dir)
      STATE_DIR="$2"
      shift 2
      ;;
    --poll-interval)
      POLL_INTERVAL="$2"
      shift 2
      ;;
    --servers)
      SERVERS="$2"
      shift 2
      ;;
    --timeout)
      TIMEOUT="$2"
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

mkdir -p "$STATE_DIR"

PID_FILE="${STATE_DIR}/.collector.pid"
LOG_FILE="${STATE_DIR}/.collector.log"

# Kill any existing collector
if [[ -f "$PID_FILE" ]]; then
  old_pid=$(cat "$PID_FILE")
  if kill -0 "$old_pid" 2>/dev/null; then
    kill "$old_pid" 2>/dev/null
    sleep 0.5
  fi
  rm -f "$PID_FILE"
fi

# Start collector.py as background daemon
nohup python3 "$SCRIPT_DIR/collector.py" \
  --state-dir "$STATE_DIR" \
  --poll-interval "$POLL_INTERVAL" \
  --servers "$SERVERS" \
  --timeout "$TIMEOUT" \
  > "$LOG_FILE" 2>&1 &

SERVER_PID=$!
disown "$SERVER_PID" 2>/dev/null
echo "$SERVER_PID" > "$PID_FILE"

# Poll for startup (check if process is alive)
for i in {1..20}; do
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "{\"error\": \"Collector process exited immediately. Check $LOG_FILE for details.\"}"
    rm -f "$PID_FILE"
    exit 1
  fi
  # Check if the DB file was created (signals successful init)
  if [[ -f "${STATE_DIR}/events.db" ]]; then
    echo "{\"status\": \"running\", \"pid\": $SERVER_PID, \"state_dir\": \"$STATE_DIR\", \"poll_interval\": $POLL_INTERVAL, \"timeout\": $TIMEOUT}"
    exit 0
  fi
  sleep 0.25
done

# Process is alive but DB not created yet — still report running
if kill -0 "$SERVER_PID" 2>/dev/null; then
  echo "{\"status\": \"running\", \"pid\": $SERVER_PID, \"state_dir\": \"$STATE_DIR\", \"poll_interval\": $POLL_INTERVAL, \"timeout\": $TIMEOUT}"
  exit 0
fi

echo "{\"error\": \"Collector failed to start within 5 seconds.\"}"
rm -f "$PID_FILE"
exit 1
