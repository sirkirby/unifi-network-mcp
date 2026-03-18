#!/bin/bash
# Merge environment variables into .claude/settings.json
# Usage: set-env.sh KEY1=VALUE1 KEY2=VALUE2 ...
#
# Creates .claude/settings.json if it doesn't exist.
# Merges into existing "env" object without overwriting other keys.
# Pure bash + sed — no python3, jq, or other dependencies required.

set -e

SETTINGS_FILE=".claude/settings.json"

# Parse arguments
declare -A new_vars
for arg in "$@"; do
  if [[ "$arg" == *"="* ]]; then
    key="${arg%%=*}"
    value="${arg#*=}"
    new_vars["$key"]="$value"
  else
    echo "ERROR: Invalid argument '$arg'. Expected KEY=VALUE format." >&2
    exit 1
  fi
done

if [ ${#new_vars[@]} -eq 0 ]; then
  echo "Usage: set-env.sh KEY1=VALUE1 KEY2=VALUE2 ..." >&2
  exit 1
fi

# Ensure .claude directory exists
mkdir -p "$(dirname "$SETTINGS_FILE")"

# Read existing settings or start with empty env object
if [ -f "$SETTINGS_FILE" ]; then
  existing=$(cat "$SETTINGS_FILE")
else
  existing='{ "env": {} }'
fi

# Ensure "env" key exists — if the file has no env block, wrap it
if ! echo "$existing" | grep -q '"env"'; then
  # Strip trailing } and add env block
  existing=$(echo "$existing" | sed 's/}[[:space:]]*$/,\n  "env": {}\n}/')
fi

# For each new key=value, either update the existing key or insert it
for key in "${!new_vars[@]}"; do
  value="${new_vars[$key]}"
  # Escape special characters for JSON and sed
  escaped_value=$(printf '%s' "$value" | sed 's/\\/\\\\/g; s/"/\\"/g; s/&/\\&/g')

  if echo "$existing" | grep -q "\"$key\""; then
    # Key exists — replace its value
    existing=$(echo "$existing" | sed "s|\"$key\"[[:space:]]*:[[:space:]]*\"[^\"]*\"|\"$key\": \"$escaped_value\"|")
  else
    # Key doesn't exist — insert before the closing brace of "env"
    # Find the last entry in env and add after it
    existing=$(echo "$existing" | sed "s|\"env\"[[:space:]]*:[[:space:]]*{|\"env\": {\n    \"$key\": \"$escaped_value\",|")
  fi
done

# Clean up any trailing commas before closing braces (invalid JSON)
existing=$(echo "$existing" | sed 's/,[[:space:]]*}/\n  }/g')

# Write back
echo "$existing" > "$SETTINGS_FILE"

# Report what was set (mask sensitive values)
for key in "${!new_vars[@]}"; do
  value="${new_vars[$key]}"
  if [ ${#value} -gt 4 ] && [[ ! "$key" =~ _(HOST|PORT|SITE)$ ]] && [ "$value" != "true" ] && [ "$value" != "false" ]; then
    display="${value:0:2}***${value: -2}"
  else
    display="$value"
  fi
  echo "  $key = $display"
done

echo ""
echo "Saved to $SETTINGS_FILE"
