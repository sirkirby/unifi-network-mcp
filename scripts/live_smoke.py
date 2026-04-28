#!/usr/bin/env python3
"""Live UniFi MCP smoke harness.

The harness intentionally exercises the public MCP tool layer instead of
manager internals. It defaults to conservative behavior:

* read-only tools are run when required arguments can be discovered
* mutating tools are previewed with ``confirm=False``
* only named lifecycle scenarios use ``confirm=True``
* risky physical/destructive operations are reported as pending approval
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import os
import subprocess
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_PREFIX = "codex-smoke"


SERVER_PACKAGES = {
    "network": "unifi-network-mcp",
    "protect": "unifi-protect-mcp",
    "access": "unifi-access-mcp",
}


SERVER_CONFIGS = {
    "network": {
        "main": "unifi_network_mcp.main",
        "runtime": "unifi_network_mcp.runtime",
        "bootstrap": "unifi_network_mcp.bootstrap",
        "categories": "unifi_network_mcp.categories",
        "jobs": "unifi_network_mcp.jobs",
        "tool_index": "unifi_network_mcp.tool_index",
        "base_package": "unifi_network_mcp.tools",
        "manifest": REPO_ROOT / "apps/network/src/unifi_network_mcp/tools_manifest.json",
        "close": "cleanup",
    },
    "protect": {
        "main": "unifi_protect_mcp.main",
        "runtime": "unifi_protect_mcp.runtime",
        "bootstrap": "unifi_protect_mcp.bootstrap",
        "categories": "unifi_protect_mcp.categories",
        "jobs": "unifi_protect_mcp.jobs",
        "tool_index": "unifi_protect_mcp.tool_index",
        "base_package": "unifi_protect_mcp.tools",
        "manifest": REPO_ROOT / "apps/protect/src/unifi_protect_mcp/tools_manifest.json",
        "prefix": "protect",
        "server_label": "UniFi Protect",
        "close": "close",
    },
    "access": {
        "main": "unifi_access_mcp.main",
        "runtime": "unifi_access_mcp.runtime",
        "bootstrap": "unifi_access_mcp.bootstrap",
        "categories": "unifi_access_mcp.categories",
        "jobs": "unifi_access_mcp.jobs",
        "tool_index": "unifi_access_mcp.tool_index",
        "base_package": "unifi_access_mcp.tools",
        "manifest": REPO_ROOT / "apps/access/src/unifi_access_mcp/tools_manifest.json",
        "prefix": "access",
        "server_label": "UniFi Access",
        "close": "close",
    },
}


STREAM_OR_HEAVY_READS = {
    "access_subscribe_events",
    "protect_subscribe_events",
    "protect_export_clip",
}


RISKY_OPERATION_NAMES = {
    "access_lock_door",
    "access_reboot_device",
    "access_revoke_credential",
    "access_unlock_door",
    "protect_delete_recording",
    "protect_reboot_camera",
    "protect_ptz_move",
    "protect_ptz_preset",
    "protect_toggle_recording",
    "protect_trigger_chime",
    "unifi_adopt_device",
    "unifi_authorize_guest",
    "unifi_block_client",
    "unifi_force_provision_device",
    "unifi_force_reconnect_client",
    "unifi_forget_client",
    "unifi_locate_device",
    "unifi_power_cycle_port",
    "unifi_reboot_device",
    "unifi_revoke_voucher",
    "unifi_set_device_led",
    "unifi_set_site_leds",
    "unifi_toggle_device",
    "unifi_trigger_rf_scan",
    "unifi_trigger_speedtest",
    "unifi_unauthorize_guest",
    "unifi_unblock_client",
    "unifi_upgrade_device",
}


@dataclass
class SmokeRecord:
    tool: str
    phase: str
    status: str
    args: dict[str, Any] = field(default_factory=dict)
    duration_ms: int = 0
    success: bool | None = None
    error: str | None = None
    summary: dict[str, Any] = field(default_factory=dict)


@dataclass
class SmokeReport:
    server: str
    started_at: str
    finished_at: str | None = None
    connected: bool = False
    records: list[SmokeRecord] = field(default_factory=list)
    created_resources: list[dict[str, Any]] = field(default_factory=list)
    cleaned_resources: list[dict[str, Any]] = field(default_factory=list)
    pending_approval: list[dict[str, Any]] = field(default_factory=list)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run live smoke checks against UniFi MCP tools.")
    parser.add_argument("--server", choices=["network", "protect", "access", "all"], required=True)
    parser.add_argument(
        "--phase",
        choices=["inventory", "readonly", "preview", "lifecycle", "approved", "safe"],
        default="safe",
        help="'safe' runs readonly, preview, and named safe lifecycles. 'approved' runs explicitly approved mutations.",
    )
    parser.add_argument("--report-dir", default="live-smoke-results")
    parser.add_argument("--delay", type=float, default=0.25, help="Delay between tool calls in seconds.")
    parser.add_argument("--tool", action="append", default=[], help="Restrict to one or more tool names.")
    parser.add_argument("--include-heavy-reads", action="store_true")
    parser.add_argument("--interactive-risky", action="store_true")
    return parser.parse_args()


def load_manifest(server_key: str) -> dict[str, Any]:
    with SERVER_CONFIGS[server_key]["manifest"].open() as fh:
        return json.load(fh)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n")


def run_all_servers(args: argparse.Namespace) -> int:
    failures = 0
    for server_key, package in SERVER_PACKAGES.items():
        cmd = [
            "uv",
            "run",
            "--package",
            package,
            "python",
            str(Path(__file__).resolve()),
            "--server",
            server_key,
            "--phase",
            args.phase,
            "--report-dir",
            args.report_dir,
            "--delay",
            str(args.delay),
        ]
        if args.include_heavy_reads:
            cmd.append("--include-heavy-reads")
        if args.interactive_risky:
            cmd.append("--interactive-risky")
        for tool in args.tool:
            cmd.extend(["--tool", tool])
        print(f"\n=== {server_key}: {' '.join(cmd)} ===", flush=True)
        completed = subprocess.run(cmd, cwd=REPO_ROOT, check=False)
        if completed.returncode != 0:
            failures += 1
    return 1 if failures else 0


def configure_environment() -> None:
    os.environ["UNIFI_TOOL_REGISTRATION_MODE"] = "eager"
    os.environ["UNIFI_TOOL_PERMISSION_MODE"] = "confirm"
    os.environ["UNIFI_AUTO_CONFIRM"] = "false"
    os.environ["UNIFI_MCP_LOG_LEVEL"] = "WARNING"
    os.environ["UNIFI_MCP_DIAGNOSTICS"] = "false"


def required_params(tool: dict[str, Any]) -> list[str]:
    return list(tool.get("schema", {}).get("input", {}).get("required") or [])


def is_read_only(tool: dict[str, Any]) -> bool:
    return tool.get("annotations", {}).get("readOnlyHint") is True


def is_destructive(tool: dict[str, Any]) -> bool:
    return tool.get("annotations", {}).get("destructiveHint") is True


def collection_items(payload: Any) -> dict[str, list[dict[str, Any]]]:
    found: dict[str, list[dict[str, Any]]] = {}

    def walk(value: Any, key: str = "") -> None:
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                walk(child_value, child_key)
        elif isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
            found.setdefault(key, []).extend(value)

    walk(payload)
    return found


def first_value(item: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return value
    return None


def looks_ptz_capable(item: dict[str, Any]) -> bool:
    markers = (
        "is_ptz",
        "isPtz",
        "is_ptz_camera",
        "ptz",
        "ptz_capable",
        "has_ptz",
        "pan_tilt_zoom",
    )
    for key in markers:
        value = item.get(key)
        if value is True or (isinstance(value, dict) and value):
            return True
    model_text = " ".join(str(item.get(key, "")) for key in ("name", "model", "type", "display_name")).lower()
    return "ptz" in model_text


def find_int_by_key(value: Any, keys: tuple[str, ...]) -> int | None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in keys:
                try:
                    return int(child)
                except (TypeError, ValueError):
                    pass
            found = find_int_by_key(child, keys)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = find_int_by_key(child, keys)
            if found is not None:
                return found
    return None


class ResourceCache:
    def __init__(self) -> None:
        self.by_collection: dict[str, list[dict[str, Any]]] = {}
        self.by_tool: dict[str, Any] = {}

    def remember(self, tool: str, result: Any) -> None:
        self.by_tool[tool] = result
        for key, items in collection_items(result).items():
            self.by_collection.setdefault(key, []).extend(items)

    def items(self, *collections: str) -> list[dict[str, Any]]:
        output: list[dict[str, Any]] = []
        for collection in collections:
            output.extend(self.by_collection.get(collection, []))
        return output

    def items_from_tool(self, tool: str, collection: str) -> list[dict[str, Any]]:
        return collection_items(self.by_tool.get(tool, {})).get(collection, [])

    def id_from(self, collections: tuple[str, ...], keys: tuple[str, ...] = ("id", "_id", "mac", "mac_address")) -> Any:
        for item in self.items(*collections):
            value = first_value(item, keys)
            if value is not None:
                return value
        return None

    def id_from_tool(
        self,
        tool: str,
        collection: str,
        keys: tuple[str, ...] = ("id", "_id", "mac", "mac_address"),
    ) -> Any:
        for item in self.items_from_tool(tool, collection):
            value = first_value(item, keys)
            if value is not None:
                return value
        return None

    def device_mac(self, prefer: str | None = None) -> Any:
        devices = self.items("devices")
        if prefer:
            preferred = [
                item
                for item in devices
                if prefer.lower() in str(item.get("type", "")).lower()
                or prefer.lower() in str(item.get("model", "")).lower()
                or prefer.lower() in str(item.get("device_category", "")).lower()
                or prefer.lower() in str(item.get("displayable_version", "")).lower()
            ]
            for item in preferred:
                value = first_value(item, ("mac", "mac_address", "id", "_id"))
                if value:
                    return value
        for item in devices:
            value = first_value(item, ("mac", "mac_address", "id", "_id"))
            if value:
                return value
        return None

    def client_mac(self) -> Any:
        return self.id_from(("clients",), ("mac", "mac_address", "id", "_id"))

    def client_ip(self) -> Any:
        for item in self.items("clients"):
            value = first_value(item, ("ip", "ip_address", "fixed_ip"))
            if value:
                return value
        return None


class LiveSmokeRunner:
    def __init__(self, server_key: str, args: argparse.Namespace) -> None:
        self.server_key = server_key
        self.args = args
        self.config = SERVER_CONFIGS[server_key]
        self.manifest = load_manifest(server_key)
        self.cache = ResourceCache()
        self.report = SmokeReport(server=server_key, started_at=datetime.now(UTC).isoformat())
        self.server: Any | None = None
        self.connection_manager: Any | None = None

    async def setup(self) -> None:
        configure_environment()
        main_mod = importlib.import_module(self.config["main"])
        runtime_mod = importlib.import_module(self.config["runtime"])
        bootstrap_mod = importlib.import_module(self.config["bootstrap"])
        categories_mod = importlib.import_module(self.config["categories"])
        jobs_mod = importlib.import_module(self.config["jobs"])
        tool_index_mod = importlib.import_module(self.config["tool_index"])
        registration_mod = importlib.import_module("unifi_mcp_shared.tool_registration")

        self.server = runtime_mod.server
        self.connection_manager = runtime_mod.connection_manager
        self.report.connected = await self.connection_manager.initialize()

        kwargs = {
            "mode": bootstrap_mod.UNIFI_TOOL_REGISTRATION_MODE,
            "server": self.server,
            "original_tool_decorator": main_mod._original_tool_decorator,
            "tool_index_handler": tool_index_mod.tool_index_handler,
            "start_async_tool": jobs_mod.start_async_tool,
            "get_job_status": jobs_mod.get_job_status,
            "register_tool": tool_index_mod.register_tool,
            "tool_module_map": categories_mod.TOOL_MODULE_MAP,
            "setup_lazy_loading": categories_mod.setup_lazy_loading,
            "base_package": self.config["base_package"],
            "config": runtime_mod.config,
            "logger": bootstrap_mod.logger,
        }
        if self.config.get("prefix"):
            kwargs["prefix"] = self.config["prefix"]
            kwargs["server_label"] = self.config["server_label"]
        await registration_mod.register_tools_for_mode(**kwargs)

    async def close(self) -> None:
        if not self.connection_manager:
            return
        close_name = self.config["close"]
        close_fn = getattr(self.connection_manager, close_name, None)
        if close_fn:
            await close_fn()

    async def call(self, tool: str, args: dict[str, Any], phase: str) -> SmokeRecord:
        assert self.server is not None
        started = time.perf_counter()
        record = SmokeRecord(tool=tool, phase=phase, status="error", args=args)
        try:
            raw = await self.server.call_tool(tool, args)
            data = self.unwrap_result(raw)
            record.duration_ms = int((time.perf_counter() - started) * 1000)
            record.success = data.get("success") if isinstance(data, dict) else None
            record.status = "ok" if record.success is not False else "failed"
            if isinstance(data, dict):
                if data.get("error"):
                    record.error = str(data["error"])
                record.summary = summarize_payload(data)
                self.cache.remember(tool, data)
        except Exception as exc:
            record.duration_ms = int((time.perf_counter() - started) * 1000)
            record.status = "exception"
            record.success = False
            record.error = str(exc)
        self.report.records.append(record)
        print(f"{self.server_key} {phase} {record.status}: {tool} ({record.duration_ms}ms)", flush=True)
        if self.args.delay:
            await asyncio.sleep(self.args.delay)
        return record

    def unwrap_result(self, raw: Any) -> dict[str, Any]:
        if isinstance(raw, tuple) and len(raw) > 1 and isinstance(raw[1], dict):
            meta_result = raw[1].get("result")
            if isinstance(meta_result, dict):
                return meta_result
        content = raw[0] if isinstance(raw, tuple) and raw else raw
        if isinstance(content, list) and content:
            text = getattr(content[0], "text", None)
            if text:
                return json.loads(text)
        if isinstance(raw, dict):
            return raw
        return {"success": False, "error": f"Unrecognized tool result shape: {type(raw).__name__}"}

    async def run(self) -> None:
        if self.args.phase == "inventory":
            self.inventory()
            return

        await self.seed_read_lists()

        if self.args.phase in ("readonly", "safe"):
            await self.run_readonly()
        if self.args.phase in ("preview", "safe"):
            await self.run_previews()
        if self.args.phase in ("lifecycle", "safe"):
            await self.run_lifecycles()
        if self.args.phase == "approved":
            await self.run_approved()

    def selected_tools(self) -> list[dict[str, Any]]:
        tools = list(self.manifest["tools"])
        if self.args.tool:
            selected = set(self.args.tool)
            tools = [tool for tool in tools if tool["name"] in selected]
        return tools

    def inventory(self) -> None:
        tools = self.selected_tools()
        for tool in tools:
            self.report.records.append(
                SmokeRecord(
                    tool=tool["name"],
                    phase="inventory",
                    status=self.safety_tier(tool),
                    summary={
                        "read_only": is_read_only(tool),
                        "destructive": is_destructive(tool),
                        "required": required_params(tool),
                        "permission_action": tool.get("permission_action"),
                        "permission_category": tool.get("permission_category"),
                    },
                )
            )

    def safety_tier(self, tool: dict[str, Any]) -> str:
        name = tool["name"]
        if name in STREAM_OR_HEAVY_READS:
            return "defer_heavy_read"
        if is_read_only(tool):
            return "read_only"
        if name in RISKY_OPERATION_NAMES or is_destructive(tool):
            return "requires_approval"
        if "confirm" in tool.get("schema", {}).get("input", {}).get("properties", {}):
            return "preview_or_safe_lifecycle"
        return "mutating_requires_review"

    async def seed_read_lists(self) -> None:
        seed_tools = [
            tool
            for tool in self.selected_tools()
            if is_read_only(tool)
            and not required_params(tool)
            and tool["name"] not in STREAM_OR_HEAVY_READS
            and ("list_" in tool["name"] or tool["name"].endswith("_status") or tool["name"].endswith("_info"))
        ]
        for tool in seed_tools:
            await self.call(tool["name"], {}, "seed")

    async def run_readonly(self) -> None:
        for tool in self.selected_tools():
            name = tool["name"]
            if not is_read_only(tool):
                continue
            if name in STREAM_OR_HEAVY_READS and not self.args.include_heavy_reads:
                self.skip(name, "readonly", "heavy or streaming read deferred")
                continue
            args, reason = self.args_for_tool(name, required_params(tool))
            if args is None:
                self.skip(name, "readonly", reason)
                continue
            await self.call(name, args, "readonly")

    async def run_previews(self) -> None:
        for tool in self.selected_tools():
            name = tool["name"]
            if is_read_only(tool):
                continue
            tier = self.safety_tier(tool)
            if tier == "requires_approval":
                self.defer_approval(tool, "preview", "risky or destructive operation")
                continue
            args, reason = self.preview_args(name)
            if args is None:
                self.skip(name, "preview", reason)
                continue
            args["confirm"] = False
            await self.call(name, args, "preview")

    async def run_lifecycles(self) -> None:
        if self.server_key == "network":
            await self.lifecycle_network_dns()
            await self.lifecycle_network_client_group()
            await self.lifecycle_network_firewall_group()
        elif self.server_key == "access":
            await self.lifecycle_access_visitor()
        elif self.server_key == "protect":
            self.skip(
                "protect_create_liveview/protect_delete_liveview",
                "lifecycle",
                "Protect liveview API is validation-only",
            )

    async def run_approved(self) -> None:
        if self.server_key == "network":
            await self.run_lifecycles()
            await self.lifecycle_network_acl_rule()
            await self.lifecycle_network_ap_group()
            await self.lifecycle_network_wlan()
            await self.lifecycle_network_port_profile()
            await self.lifecycle_network_firewall_policy()
            await self.lifecycle_network_oon_policy()
            await self.lifecycle_network_voucher()
        elif self.server_key == "protect":
            await self.approved_protect_physical()
        elif self.server_key == "access":
            await self.approved_access_physical()

    def skip(self, tool: str, phase: str, reason: str) -> None:
        self.report.records.append(SmokeRecord(tool=tool, phase=phase, status="skipped", error=reason))
        print(f"{self.server_key} {phase} skipped: {tool} - {reason}", flush=True)

    def defer_approval(self, tool: dict[str, Any], phase: str, reason: str) -> None:
        item = {
            "tool": tool["name"],
            "phase": phase,
            "reason": reason,
            "required": required_params(tool),
            "destructive": is_destructive(tool),
        }
        self.report.pending_approval.append(item)
        self.report.records.append(SmokeRecord(tool=tool["name"], phase=phase, status="pending_approval", summary=item))
        print(f"{self.server_key} {phase} pending approval: {tool['name']}", flush=True)

    def args_for_tool(self, name: str, required: list[str]) -> tuple[dict[str, Any] | None, str]:
        args: dict[str, Any] = {}
        for param in required:
            value = self.value_for_param(name, param)
            if value is None:
                return None, f"could not discover required argument {param}"
            args[param] = value
        return args, ""

    def value_for_param(self, name: str, param: str) -> Any:
        if param in {"mac_address", "client_mac"}:
            if name == "unifi_get_device_radio":
                return self.cache.device_mac("ap")
            return self.cache.client_mac() if "client" in name else self.cache.device_mac()
        if param in {"device_mac", "gateway_mac"}:
            return self.cache.device_mac("gateway") if param == "gateway_mac" else self.cache.device_mac()
        if param == "ap_mac":
            return self.cache.device_mac("ap") or self.cache.device_mac("uap")
        if param == "ip_address":
            return self.cache.client_ip()
        if param == "camera_id":
            return self.cache.id_from(("cameras",), ("id", "_id"))
        if param == "door_id":
            return self.cache.id_from(("doors",), ("id", "_id"))
        if param == "event_id":
            return self.cache.id_from(("events",), ("id", "_id", "event_id", "uuid"))
        if param == "credential_id":
            return self.cache.id_from(("credentials",), ("id", "_id", "credential_id", "uuid"))
        if param == "visitor_id":
            return self.cache.id_from(("visitors",), ("id", "_id", "visitor_id", "uuid"))
        if param == "policy_id":
            if "firewall" in name:
                return self.cache.id_from_tool("unifi_list_firewall_policies", "policies", ("id", "_id"))
            if "oon" in name:
                return self.cache.id_from_tool("unifi_list_oon_policies", "policies", ("id", "_id"))
            return self.cache.id_from_tool(
                "access_list_policies",
                "policies",
                ("id", "_id", "policy_id", "uuid"),
            ) or self.cache.id_from(("policies",), ("id", "_id", "policy_id", "uuid"))
        if param == "group_id":
            if "ap_group" in name:
                return self.cache.id_from_tool("unifi_list_ap_groups", "ap_groups", ("id", "_id"))
            if "client_group" in name:
                return self.cache.id_from_tool("unifi_list_client_groups", "groups", ("id", "_id"))
            if "firewall_group" in name:
                return self.cache.id_from_tool("unifi_list_firewall_groups", "groups", ("id", "_id"))
            if "usergroup" in name:
                return self.cache.id_from_tool("unifi_list_usergroups", "usergroups", ("id", "_id"))
            return self.cache.id_from(("groups",), ("id", "_id"))
        if param == "client_id":
            if "vpn_client" in name:
                return self.cache.id_from_tool("unifi_list_vpn_clients", "vpn_clients", ("_id", "id"))
            return self.cache.client_mac()
        if param == "device_id":
            return self.cache.device_mac()
        if param == "server_id":
            return self.cache.id_from_tool("unifi_list_vpn_servers", "vpn_servers", ("_id", "id"))
        if param == "rule_id":
            if "acl_rule" in name:
                return self.cache.id_from_tool("unifi_list_acl_rules", "rules", ("id", "_id"))
            if "qos_rule" in name:
                return self.cache.id_from_tool("unifi_list_qos_rules", "qos_rules", ("id", "_id"))
            return self.cache.id_from(("rules",), ("id", "_id"))
        collection_by_param = {
            "record_id": ("records",),
            "network_id": ("networks",),
            "wlan_id": ("wlans",),
            "route_id": ("traffic_routes",) if "traffic_route" in name else ("routes",),
            "port_forward_id": ("port_forwards", "rules"),
            "profile_id": ("profiles", "port_profiles"),
            "filter_id": ("filters", "content_filters"),
            "voucher_id": ("vouchers",),
            "liveview_id": ("liveviews",),
            "chime_id": ("chimes",),
            "light_id": ("lights",),
        }
        if param in collection_by_param:
            return self.cache.id_from(collection_by_param[param], ("id", "_id", "mac", "mac_address"))
        return None

    def preview_args(self, name: str) -> tuple[dict[str, Any] | None, str]:
        stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        simple: dict[str, dict[str, Any]] = {
            "unifi_create_dns_record": {
                "record_data": {
                    "key": f"{RUN_PREFIX}-{stamp}.test",
                    "value": "192.0.2.123",
                    "record_type": "A",
                    "ttl": 60,
                }
            },
            "unifi_create_client_group": {"name": f"{RUN_PREFIX}-{stamp}", "members": []},
            "unifi_create_firewall_group": {
                "name": f"{RUN_PREFIX}-{stamp}",
                "group_type": "address-group",
                "group_members": ["192.0.2.123"],
            },
            "access_create_visitor": self.visitor_args(stamp),
        }
        if name in simple:
            return dict(simple[name]), ""
        if name == "unifi_set_client_ip_settings":
            mac = self.cache.client_mac()
            if not mac:
                return None, "could not discover required argument mac_address"
            return {"mac_address": mac, "local_dns_record_enabled": False}, ""
        if name == "unifi_update_route":
            route_id = self.value_for_param(name, "route_id")
            if not route_id:
                return None, "could not discover required argument route_id"
            return {"route_id": route_id, "enabled": True}, ""
        if name == "unifi_update_traffic_route":
            route_id = self.value_for_param(name, "route_id")
            if not route_id:
                return None, "could not discover required argument route_id"
            return {"route_id": route_id, "enabled": True}, ""
        if name == "unifi_update_usergroup":
            group_id = self.value_for_param(name, "group_id")
            if not group_id:
                return None, "could not discover required argument group_id"
            current_name = None
            for item in self.cache.items_from_tool("unifi_list_usergroups", "usergroups"):
                if first_value(item, ("id", "_id")) == group_id:
                    current_name = item.get("name")
                    break
            return {"group_id": group_id, "name": current_name or f"{RUN_PREFIX}-preview"}, ""
        return self.args_for_tool(name, required_params(next(t for t in self.manifest["tools"] if t["name"] == name)))

    def visitor_args(self, stamp: str) -> dict[str, Any]:
        start = datetime.now(UTC) + timedelta(minutes=5)
        end = start + timedelta(minutes=30)
        return {
            "name": f"{RUN_PREFIX}-{stamp}",
            "access_start": start.isoformat().replace("+00:00", "Z"),
            "access_end": end.isoformat().replace("+00:00", "Z"),
        }

    def protect_camera_id(self, prefer_ptz: bool = False) -> str | None:
        cameras = self.cache.items("cameras")
        if prefer_ptz:
            for camera in cameras:
                if looks_ptz_capable(camera):
                    value = first_value(camera, ("id", "_id", "camera_id", "uuid"))
                    if value:
                        return str(value)
        for camera in cameras:
            value = first_value(camera, ("id", "_id", "camera_id", "uuid"))
            if value:
                return str(value)
        return None

    def protect_preset_slot(self, camera_id: str) -> int | None:
        payload = self.cache.by_tool.get("protect_get_camera", {})
        detail = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(detail, dict):
            return None
        if str(first_value(detail, ("id", "_id", "camera_id", "uuid"))) not in ("", "None", camera_id):
            return None
        return find_int_by_key(detail, ("slot", "preset_slot", "presetSlot"))

    def protect_recording_enabled(self, camera_id: str) -> bool | None:
        payload = self.cache.by_tool.get("protect_get_camera", {})
        detail = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(detail, dict):
            return None
        if str(first_value(detail, ("id", "_id", "camera_id", "uuid"))) not in ("", "None", camera_id):
            return None
        mode = str(detail.get("recording_mode") or detail.get("recordingMode") or "").lower()
        if mode:
            return mode not in {"never", "disabled", "off"}
        value = detail.get("is_recording")
        return value if isinstance(value, bool) else None

    def firewall_zone_id(self, preferred_name: str) -> str | None:
        zones = self.cache.items_from_tool("unifi_list_firewall_zones", "zones")
        for zone in zones:
            if str(zone.get("name", "")).lower() == preferred_name.lower():
                value = first_value(zone, ("id", "_id", "zone_id"))
                if value:
                    return str(value)
        for zone in zones:
            value = first_value(zone, ("id", "_id", "zone_id"))
            if value:
                return str(value)
        return None

    async def lifecycle_network_dns(self) -> None:
        stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        key = f"{RUN_PREFIX}-{stamp}.test"
        create = await self.call(
            "unifi_create_dns_record",
            {"record_data": {"key": key, "value": "192.0.2.123", "record_type": "A", "ttl": 60}, "confirm": True},
            "lifecycle:create",
        )
        record_id = create.summary.get("resource_id")
        if not record_id:
            self.skip("unifi_update_dns_record/unifi_delete_dns_record", "lifecycle", "DNS create did not return an id")
            return
        self.report.created_resources.append({"type": "dns_record", "id": record_id, "name": key})
        await self.call(
            "unifi_update_dns_record",
            {"record_id": record_id, "update_data": {"value": "192.0.2.124"}, "confirm": True},
            "lifecycle:update",
        )
        await self.call("unifi_get_dns_record_details", {"record_id": record_id}, "lifecycle:get")
        delete = await self.call(
            "unifi_delete_dns_record",
            {"record_id": record_id, "confirm": True},
            "lifecycle:delete",
        )
        if delete.success:
            self.report.cleaned_resources.append({"type": "dns_record", "id": record_id, "name": key})

    async def lifecycle_network_client_group(self) -> None:
        stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        name = f"{RUN_PREFIX}-client-group-{stamp}"
        create = await self.call(
            "unifi_create_client_group",
            {"name": name, "members": [], "confirm": True},
            "lifecycle:create",
        )
        group_id = create.summary.get("resource_id")
        if not group_id:
            self.skip(
                "unifi_update_client_group/unifi_delete_client_group",
                "lifecycle",
                "client group create did not return an id",
            )
            return
        self.report.created_resources.append({"type": "client_group", "id": group_id, "name": name})
        await self.call(
            "unifi_update_client_group",
            {"group_id": group_id, "group_data": {"name": f"{name}-updated"}, "confirm": True},
            "lifecycle:update",
        )
        delete = await self.call(
            "unifi_delete_client_group",
            {"group_id": group_id, "confirm": True},
            "lifecycle:delete",
        )
        if delete.success:
            self.report.cleaned_resources.append({"type": "client_group", "id": group_id, "name": name})

    async def lifecycle_network_firewall_group(self) -> None:
        stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        name = f"{RUN_PREFIX}-fw-group-{stamp}"
        create = await self.call(
            "unifi_create_firewall_group",
            {"name": name, "group_type": "address-group", "group_members": ["192.0.2.123"], "confirm": True},
            "lifecycle:create",
        )
        group_id = create.summary.get("resource_id")
        if not group_id:
            self.skip(
                "unifi_update_firewall_group/unifi_delete_firewall_group",
                "lifecycle",
                "firewall group create did not return an id",
            )
            return
        self.report.created_resources.append({"type": "firewall_group", "id": group_id, "name": name})
        await self.call(
            "unifi_update_firewall_group",
            {
                "group_id": group_id,
                "group_data": {"name": f"{name}-updated", "group_members": ["192.0.2.124"]},
                "confirm": True,
            },
            "lifecycle:update",
        )
        delete = await self.call(
            "unifi_delete_firewall_group",
            {"group_id": group_id, "confirm": True},
            "lifecycle:delete",
        )
        if delete.success:
            self.report.cleaned_resources.append({"type": "firewall_group", "id": group_id, "name": name})

    async def lifecycle_network_acl_rule(self) -> None:
        network_id = self.value_for_param("unifi_create_acl_rule", "network_id")
        if not network_id:
            self.skip("unifi_create_acl_rule/unifi_delete_acl_rule", "approved", "could not discover network_id")
            return

        stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        name = f"{RUN_PREFIX}-acl-{stamp}"
        create = await self.call(
            "unifi_create_acl_rule",
            {
                "name": name,
                "acl_index": 65000,
                "action": "ALLOW",
                "network_id": network_id,
                "enabled": False,
                "source_macs": [],
                "destination_macs": [],
                "confirm": True,
            },
            "approved:create",
        )
        rule_id = create.summary.get("resource_id")
        if not rule_id:
            self.skip("unifi_delete_acl_rule", "approved", "ACL create did not return an id")
            return
        self.report.created_resources.append({"type": "acl_rule", "id": rule_id, "name": name})
        delete = await self.call("unifi_delete_acl_rule", {"rule_id": rule_id, "confirm": True}, "approved:delete")
        if delete.success:
            self.report.cleaned_resources.append({"type": "acl_rule", "id": rule_id, "name": name})

    async def lifecycle_network_ap_group(self) -> None:
        stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        name = f"{RUN_PREFIX}-ap-group-{stamp}"
        create = await self.call(
            "unifi_create_ap_group",
            {"group_data": {"name": name, "device_macs": [], "wlan_group_ids": []}, "confirm": True},
            "approved:create",
        )
        group_id = create.summary.get("resource_id")
        if not group_id:
            self.skip("unifi_delete_ap_group", "approved", "AP group create did not return an id")
            return
        self.report.created_resources.append({"type": "ap_group", "id": group_id, "name": name})
        delete = await self.call("unifi_delete_ap_group", {"group_id": group_id, "confirm": True}, "approved:delete")
        if delete.success:
            self.report.cleaned_resources.append({"type": "ap_group", "id": group_id, "name": name})

    async def lifecycle_network_wlan(self) -> None:
        ap_group_id = self.cache.id_from_tool("unifi_list_ap_groups", "ap_groups", ("_id", "id"))
        if not ap_group_id:
            self.skip("unifi_create_wlan/unifi_delete_wlan", "approved", "could not discover AP group id")
            return

        stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        name = f"{RUN_PREFIX}-ssid-{stamp}"
        create = await self.call(
            "unifi_create_wlan",
            {
                "wlan_data": {
                    "name": name,
                    "security": "open",
                    "enabled": False,
                    "hide_ssid": True,
                    "guest_policy": True,
                    "ap_group_ids": [ap_group_id],
                    "ap_group_mode": "groups",
                },
                "confirm": True,
            },
            "approved:create",
        )
        wlan_id = create.summary.get("resource_id")
        if not wlan_id:
            self.skip("unifi_delete_wlan", "approved", "WLAN create did not return an id")
            return
        self.report.created_resources.append({"type": "wlan", "id": wlan_id, "name": name})
        delete = await self.call("unifi_delete_wlan", {"wlan_id": wlan_id, "confirm": True}, "approved:delete")
        if delete.success:
            self.report.cleaned_resources.append({"type": "wlan", "id": wlan_id, "name": name})

    async def lifecycle_network_port_profile(self) -> None:
        stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        name = f"{RUN_PREFIX}-port-profile-{stamp}"
        create = await self.call(
            "unifi_create_port_profile",
            {"name": name, "forward": "disabled", "poe_mode": "off", "confirm": True},
            "approved:create",
        )
        profile_id = create.summary.get("resource_id")
        if not profile_id:
            self.skip("unifi_delete_port_profile", "approved", "port profile create did not return an id")
            return
        self.report.created_resources.append({"type": "port_profile", "id": profile_id, "name": name})
        delete = await self.call(
            "unifi_delete_port_profile",
            {"profile_id": profile_id, "confirm": True},
            "approved:delete",
        )
        if delete.success:
            self.report.cleaned_resources.append({"type": "port_profile", "id": profile_id, "name": name})

    async def lifecycle_network_firewall_policy(self) -> None:
        source_zone = self.firewall_zone_id("Internal")
        destination_zone = self.firewall_zone_id("External")
        if not source_zone or not destination_zone:
            self.skip(
                "unifi_create_firewall_policy/unifi_delete_firewall_policy",
                "approved",
                "could not discover source/destination firewall zones",
            )
            return

        stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        name = f"{RUN_PREFIX}-fw-policy-{stamp}"
        endpoint = {"matching_target": "ANY"}
        create = await self.call(
            "unifi_create_firewall_policy",
            {
                "policy_data": {
                    "name": name,
                    "action": "ALLOW",
                    "index": 65000,
                    "enabled": False,
                    "logging": False,
                    "protocol": "all",
                    "source": {**endpoint, "zone_id": source_zone},
                    "destination": {**endpoint, "zone_id": destination_zone},
                },
                "confirm": True,
            },
            "approved:create",
        )
        policy_id = create.summary.get("resource_id")
        if not policy_id:
            self.skip("unifi_delete_firewall_policy", "approved", "firewall policy create did not return an id")
            return
        self.report.created_resources.append({"type": "firewall_policy", "id": policy_id, "name": name})
        delete = await self.call(
            "unifi_delete_firewall_policy",
            {"policy_id": policy_id, "confirm": True},
            "approved:delete",
        )
        if delete.success:
            self.report.cleaned_resources.append({"type": "firewall_policy", "id": policy_id, "name": name})

    async def lifecycle_network_oon_policy(self) -> None:
        client_mac = self.cache.client_mac()
        if not client_mac:
            self.skip("unifi_create_oon_policy/unifi_delete_oon_policy", "approved", "could not discover client MAC")
            return

        stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        name = f"{RUN_PREFIX}-oon-{stamp}"
        create = await self.call(
            "unifi_create_oon_policy",
            {
                "name": name,
                "target_type": "CLIENTS",
                "targets": [{"type": "MAC", "id": client_mac}],
                "enabled": False,
                "secure": {"internet_access_enabled": True, "apps": []},
                "confirm": True,
            },
            "approved:create",
        )
        policy_id = create.summary.get("resource_id")
        if not policy_id:
            self.skip("unifi_delete_oon_policy", "approved", "OON policy create did not return an id")
            return
        self.report.created_resources.append({"type": "oon_policy", "id": policy_id, "name": name})
        delete = await self.call(
            "unifi_delete_oon_policy", {"policy_id": policy_id, "confirm": True}, "approved:delete"
        )
        if delete.success:
            self.report.cleaned_resources.append({"type": "oon_policy", "id": policy_id, "name": name})

    async def lifecycle_network_voucher(self) -> None:
        stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        note = f"{RUN_PREFIX}-voucher-{stamp}"
        create = await self.call(
            "unifi_create_voucher",
            {"expire_minutes": 10, "count": 1, "quota": 1, "note": note, "confirm": True},
            "approved:create",
        )
        voucher_id = create.summary.get("resource_id")
        if not voucher_id:
            await self.call("unifi_list_vouchers", {}, "approved:list")
            for voucher in self.cache.items_from_tool("unifi_list_vouchers", "vouchers"):
                if voucher.get("note") == note:
                    voucher_id = first_value(voucher, ("_id", "id", "voucher_id"))
                    break
        if not voucher_id:
            self.skip("unifi_revoke_voucher", "approved", "voucher create did not return an id")
            return
        self.report.created_resources.append({"type": "voucher", "id": voucher_id, "name": note})
        revoke = await self.call(
            "unifi_revoke_voucher",
            {"voucher_id": voucher_id, "confirm": True},
            "approved:delete",
        )
        if revoke.success:
            self.report.cleaned_resources.append({"type": "voucher", "id": voucher_id, "name": note})

    async def approved_protect_physical(self) -> None:
        camera_id = self.protect_camera_id()
        if not camera_id:
            self.skip("protect approved camera operations", "approved", "could not discover camera_id")
            return

        ptz_camera_id = self.protect_camera_id(prefer_ptz=True)
        if ptz_camera_id:
            await self.call("protect_get_camera", {"camera_id": ptz_camera_id}, "approved:get")
            await self.call("protect_ptz_move", {"camera_id": ptz_camera_id, "zoom": 0}, "approved:physical")
            preset_slot = self.protect_preset_slot(ptz_camera_id)
            if preset_slot is not None:
                await self.call(
                    "protect_ptz_preset",
                    {"camera_id": ptz_camera_id, "preset_slot": preset_slot},
                    "approved:physical",
                )
            else:
                self.skip("protect_ptz_preset", "approved", "no PTZ preset slot discovered")
        else:
            self.skip("protect_ptz_move/protect_ptz_preset", "approved", "no PTZ-capable camera discovered")

        await self.call("protect_get_camera", {"camera_id": camera_id}, "approved:get")
        enabled = self.protect_recording_enabled(camera_id)
        if enabled is None:
            enabled = True
        await self.call(
            "protect_toggle_recording",
            {"camera_id": camera_id, "enabled": enabled, "confirm": False},
            "approved:preview",
        )
        await self.call(
            "protect_toggle_recording",
            {"camera_id": camera_id, "enabled": enabled, "confirm": True},
            "approved:physical",
        )
        await self.call("protect_reboot_camera", {"camera_id": camera_id, "confirm": False}, "approved:preview")
        await self.call("protect_reboot_camera", {"camera_id": camera_id, "confirm": True}, "approved:physical")

    async def approved_access_physical(self) -> None:
        door_id = self.cache.id_from(("doors",), ("id", "_id", "door_id", "uuid"))
        if door_id:
            await self.call(
                "access_unlock_door", {"door_id": door_id, "duration": 2, "confirm": False}, "approved:preview"
            )
            await self.call(
                "access_unlock_door", {"door_id": door_id, "duration": 2, "confirm": True}, "approved:physical"
            )
            await self.call("access_lock_door", {"door_id": door_id, "confirm": False}, "approved:preview")
            await self.call("access_lock_door", {"door_id": door_id, "confirm": True}, "approved:physical")
        else:
            self.skip("access_unlock_door/access_lock_door", "approved", "could not discover door_id")

        device_id = self.cache.id_from(("devices",), ("id", "_id", "device_id", "uuid"))
        if device_id:
            await self.call("access_reboot_device", {"device_id": device_id, "confirm": False}, "approved:preview")
            await self.call("access_reboot_device", {"device_id": device_id, "confirm": True}, "approved:physical")
        else:
            self.skip("access_reboot_device", "approved", "could not discover device_id")

    async def lifecycle_access_visitor(self) -> None:
        stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        args = self.visitor_args(stamp)
        create = await self.call("access_create_visitor", {**args, "confirm": True}, "lifecycle:create")
        visitor_id = create.summary.get("resource_id")
        if not visitor_id:
            self.skip("access_delete_visitor", "lifecycle", "visitor create did not return an id")
            return
        self.report.created_resources.append({"type": "visitor", "id": visitor_id, "name": args["name"]})
        delete = await self.call(
            "access_delete_visitor",
            {"visitor_id": visitor_id, "confirm": True},
            "lifecycle:delete",
        )
        if delete.success:
            self.report.cleaned_resources.append({"type": "visitor", "id": visitor_id, "name": args["name"]})


def summarize_payload(data: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for key in (
        "success",
        "count",
        "site",
        "message",
        "requires_confirmation",
        "action",
        "resource_type",
        "resource_name",
    ):
        if key in data:
            summary[key] = data[key]
    resource_id = find_resource_id(data)
    if resource_id:
        summary["resource_id"] = resource_id
    for collection, items in collection_items(data).items():
        summary[f"{collection}_count"] = len(items)
    if "error" in data:
        summary["error"] = data["error"]
    return summary


def find_resource_id(data: Any) -> str | None:
    if isinstance(data, dict):
        for key in (
            "id",
            "_id",
            "record_id",
            "group_id",
            "rule_id",
            "policy_id",
            "profile_id",
            "voucher_id",
            "visitor_id",
            "wlan_id",
            "liveview_id",
        ):
            value = data.get(key)
            if value:
                return str(value)
        for key in ("details", "group", "policy", "profile", "rule", "data", "result"):
            value = find_resource_id(data.get(key))
            if value:
                return value
    elif isinstance(data, list):
        for item in data:
            value = find_resource_id(item)
            if value:
                return value
    return None


async def run_one(args: argparse.Namespace) -> int:
    runner = LiveSmokeRunner(args.server, args)
    try:
        await runner.setup()
        await runner.run()
    finally:
        runner.report.finished_at = datetime.now(UTC).isoformat()
        await runner.close()
        report_dir = REPO_ROOT / args.report_dir
        stamp = runner.report.started_at.replace(":", "").replace("+0000", "Z")
        path = report_dir / f"{runner.server_key}-{stamp}.json"
        write_json(path, asdict(runner.report))
        print(f"\nReport: {path}", flush=True)
    failed = [record for record in runner.report.records if record.status in {"failed", "exception"}]
    return 1 if failed else 0


def main() -> int:
    args = parse_args()
    if args.server == "all":
        return run_all_servers(args)
    return asyncio.run(run_one(args))


if __name__ == "__main__":
    raise SystemExit(main())
