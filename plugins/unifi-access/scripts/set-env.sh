#!/bin/bash
# Merge environment variables into .claude/settings.json
# Usage: set-env.sh KEY1=VALUE1 KEY2=VALUE2 ...
#
# Creates .claude/settings.json if it doesn't exist.
# Merges into existing "env" object without overwriting other keys.
# Requires python3 (available on macOS/Linux by default).

set -e

SETTINGS_FILE=".claude/settings.json"

# Collect key=value pairs from arguments
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

# Build JSON merge payload
json_pairs=""
for key in "${!new_vars[@]}"; do
  value="${new_vars[$key]}"
  # Escape quotes in value
  escaped_value="${value//\"/\\\"}"
  if [ -n "$json_pairs" ]; then
    json_pairs="$json_pairs, "
  fi
  json_pairs="$json_pairs\"$key\": \"$escaped_value\""
done

# Ensure .claude directory exists
mkdir -p "$(dirname "$SETTINGS_FILE")"

# Merge into settings.json using python3 for reliable JSON handling
python3 -c "
import json, sys, os

settings_file = '$SETTINGS_FILE'
new_env = {$json_pairs}

# Read existing settings or start fresh
if os.path.exists(settings_file):
    with open(settings_file) as f:
        try:
            settings = json.load(f)
        except json.JSONDecodeError:
            settings = {}
else:
    settings = {}

# Merge into env
if 'env' not in settings:
    settings['env'] = {}
settings['env'].update(new_env)

# Write back with pretty formatting
with open(settings_file, 'w') as f:
    json.dump(settings, f, indent=2)
    f.write('\n')

# Report what was set
for k, v in new_env.items():
    display_v = v if len(v) <= 4 or k.endswith('_HOST') or k.endswith('_PORT') or k.endswith('_SITE') else v[:2] + '***' + v[-2:]
    print(f'  {k} = {display_v}')
"

echo ""
echo "Saved to $SETTINGS_FILE"
