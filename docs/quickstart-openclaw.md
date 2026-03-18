# UniFi MCP — OpenClaw Quickstart

Get UniFi Network, Protect, and Access tools running in OpenClaw in about 10 minutes.

---

## Prerequisites

- UniFi controller running and reachable (UDM, UCG, CloudKey, or self-hosted)
- Local admin credentials (not a Ubiquiti SSO account)
- Python 3.13+ with `uv` installed ([install uv](https://docs.astral.sh/uv/getting-started/installation/))
- OpenClaw installed and the gateway running (`openclaw gateway status`)

---

## Step 1: Install the MCP Servers

`uvx` runs each server without a permanent install. No virtualenv setup needed.

Verify each server launches cleanly before adding it to OpenClaw:

```bash
uvx unifi-network-mcp --help
uvx unifi-protect-mcp --help   # only if you have Protect
uvx unifi-access-mcp --help    # only if you have Access
```

---

## Step 2: Add MCP Servers to OpenClaw

Edit `~/.openclaw/openclaw.json`. Add a block under `mcpServers` for each server you want. The `env` section holds your controller credentials — keep this file private.

```json
{
  "mcpServers": {
    "unifi-network": {
      "command": "uvx",
      "args": ["unifi-network-mcp"],
      "env": {
        "UNIFI_NETWORK_HOST": "192.168.1.1",
        "UNIFI_NETWORK_USERNAME": "admin",
        "UNIFI_NETWORK_PASSWORD": "your-password",
        "UNIFI_NETWORK_VERIFY_SSL": "false"
      }
    },
    "unifi-protect": {
      "command": "uvx",
      "args": ["unifi-protect-mcp"],
      "env": {
        "UNIFI_PROTECT_HOST": "192.168.1.1",
        "UNIFI_PROTECT_USERNAME": "admin",
        "UNIFI_PROTECT_PASSWORD": "your-password",
        "UNIFI_PROTECT_VERIFY_SSL": "false"
      }
    },
    "unifi-access": {
      "command": "uvx",
      "args": ["unifi-access-mcp"],
      "env": {
        "UNIFI_ACCESS_HOST": "192.168.1.1",
        "UNIFI_ACCESS_USERNAME": "admin",
        "UNIFI_ACCESS_PASSWORD": "your-password",
        "UNIFI_ACCESS_VERIFY_SSL": "false"
      }
    }
  }
}
```

Only add the servers that match your hardware. If Protect and Network are on the same controller, the same host/credentials apply to both.

Restart the gateway to load the new config:

```bash
openclaw gateway restart
```

---

## Step 3: Install the Skills

The skills live in the `plugins/` directory of this repo. Copy them into your OpenClaw user skills directory so they are available to all agents:

```bash
# Clone or pull the repo if you haven't already
git clone https://github.com/sirkirby/unifi-network-mcp.git
cd unifi-network-mcp

# Copy skills into OpenClaw
mkdir -p ~/.openclaw/skills
cp -r plugins/unifi-network/skills/* ~/.openclaw/skills/
cp -r plugins/unifi-protect/skills/* ~/.openclaw/skills/
cp -r plugins/unifi-access/skills/* ~/.openclaw/skills/
```

Or install each skill from clawhub if they are published there:

```bash
clawhub install sirkirby/unifi-network
clawhub install sirkirby/unifi-protect
clawhub install sirkirby/unifi-access
```

To scope skills to a single agent workspace instead of all agents, copy into `<workspace>/skills/` rather than `~/.openclaw/skills/`.

Skill precedence: `<workspace>/skills` > `~/.openclaw/skills` > bundled skills.

---

## Step 4: Try It

Open a session and run a few quick checks.

**Network health check:**

> "Run a network health check"

The agent will use the `network-health-check` skill, batch-query your controller, and return a structured report: device status, firmware update candidates, active alarms, and recommendations.

**Security digest (requires Protect):**

> "Generate a security digest for the last 24 hours"

The agent uses the `security-digest` skill to pull camera events, smart detections, door badge-ins (if Access is connected), and firewall blocks into a single summary.

**Firewall audit:**

> "Audit my firewall rules"

Uses the `firewall-auditor` skill to review your firewall policies for coverage gaps, redundant rules, and common misconfigurations.

**Initial setup (first time only):**

> "Set up my UniFi Network connection"

The `setup` skill walks you through controller host, credentials, and permission configuration step by step.

---

## Step 5: Enable Write Permissions (Optional)

By default the servers are read-only for high-risk operations. To enable mutations, add permission variables to the server's `env` block in `openclaw.json`:

```json
"env": {
  "UNIFI_NETWORK_HOST": "192.168.1.1",
  "UNIFI_NETWORK_USERNAME": "admin",
  "UNIFI_NETWORK_PASSWORD": "your-password",
  "UNIFI_NETWORK_VERIFY_SSL": "false",
  "UNIFI_PERMISSIONS_FIREWALL_POLICIES_CREATE": "true",
  "UNIFI_PERMISSIONS_FIREWALL_POLICIES_UPDATE": "true",
  "UNIFI_PERMISSIONS_PORT_FORWARDS_CREATE": "true",
  "UNIFI_PERMISSIONS_PORT_FORWARDS_UPDATE": "true"
}
```

All mutations use a preview-then-confirm flow. The agent will show you exactly what would change before executing anything.

Delete operations are disabled by default regardless of other settings. To enable a specific delete:

```
"UNIFI_PERMISSIONS_FIREWALL_POLICIES_DELETE": "true"
```

---

## Step 6: Schedule Recurring Checks

Use OpenClaw's built-in cron scheduler to run health checks and digests automatically.

**Daily network health check at 7 AM:**

```bash
openclaw cron add \
  --name "unifi-health-check" \
  --cron "0 7 * * *" \
  --tz "America/Los_Angeles" \
  --session isolated \
  --message "Run a UniFi network health check and summarize results." \
  --announce
```

**Weekly security digest every Monday at 6 AM:**

```bash
openclaw cron add \
  --name "unifi-security-digest" \
  --cron "0 6 * * 1" \
  --tz "America/Los_Angeles" \
  --session isolated \
  --message "Generate a UniFi security digest covering the past 7 days. Include camera events, door events, and firewall activity." \
  --announce
```

**Nightly firewall audit at midnight:**

```bash
openclaw cron add \
  --name "unifi-firewall-audit" \
  --cron "0 0 * * *" \
  --tz "America/Los_Angeles" \
  --session isolated \
  --message "Audit my UniFi firewall rules and flag any issues." \
  --announce
```

List active cron jobs:

```bash
openclaw cron list
```

Remove a job:

```bash
openclaw cron remove --name "unifi-health-check"
```

Jobs persist under `~/.openclaw/cron/` and survive gateway restarts. OpenClaw applies exponential retry backoff if your controller is temporarily unreachable.

---

## Available Skills

| Skill | Plugin | Description |
|-------|--------|-------------|
| `network-health-check` | unifi-network | Device status, firmware updates, alarms, recommendations |
| `firewall-auditor` | unifi-network | Review firewall rules for gaps and misconfigurations |
| `firewall-manager` | unifi-network | Create and modify firewall policies with preview-confirm |
| `setup` | unifi-network | Interactive first-time configuration wizard |
| `unifi-network` | unifi-network | General context: all 91 tools, safety model, workflows |
| `security-digest` | unifi-protect | Cross-system security event digest (cameras + access + network) |
| `setup` | unifi-protect | Interactive first-time configuration wizard for Protect |
| `unifi-protect` | unifi-protect | General context: all 34 Protect tools |
| `setup` | unifi-access | Interactive first-time configuration wizard for Access |
| `unifi-access` | unifi-access | General context: all 29 Access tools |

---

## Troubleshooting

**Server not connecting**
- Confirm the host is reachable: `curl -k https://192.168.1.1`
- Check that `UNIFI_NETWORK_VERIFY_SSL=false` is set if your controller uses a self-signed certificate
- Local admin credentials only — Ubiquiti SSO accounts do not work

**Tools not showing up**
- The servers use lazy loading by default. Meta-tools (`unifi_tool_index`, `unifi_execute`, `unifi_batch`) load first. The agent discovers other tools through `unifi_tool_index`.
- To load all tools eagerly: add `"UNIFI_TOOL_REGISTRATION_MODE": "eager"` to the server's `env` block

**Permission denied on mutations**
- Check the error message — it includes the exact env var to set (e.g., `UNIFI_PERMISSIONS_NETWORKS_UPDATE=true`)
- Add the variable to the server's `env` block in `openclaw.json` and restart the gateway

**Cron job not running**
- Verify the gateway is running: `openclaw gateway status`
- Check cron job status: `openclaw cron list`
- Review gateway logs: `openclaw gateway logs`
