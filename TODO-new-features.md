# UniFi MCP Server - Neue Features

## Status: Abgeschlossen
Erstellt: 2025-11-23
Letzte Aktualisierung: 2025-11-23

### Fortschritt
- [x] **Hotspot Vouchers** - FERTIG (2025-11-23)
- [x] **User Groups / Bandwidth Limits** - FERTIG (2025-11-23)
- [x] **Static Routes (Routing-Tabellen)** - FERTIG (2025-11-23)
- [x] **Event Logs** - FERTIG (2025-11-23)

---

## Geplante Features

### 1. Hotspot Vouchers
**Priorität:** Hoch

| Tool | Endpoint | Beschreibung |
|------|----------|--------------|
| `unifi_list_vouchers` | GET `/stat/voucher` | Alle Vouchers auflisten |
| `unifi_create_voucher` | POST `/cmd/hotspot` cmd=create-voucher | Voucher erstellen |
| `unifi_revoke_voucher` | POST `/cmd/hotspot` cmd=delete-voucher | Voucher widerrufen |

**Create Voucher Parameter:**
- `expire` (int): Minuten gültig nach Aktivierung
- `n` (int): Anzahl Vouchers (default 1)
- `quota` (int): 0=multi-use, 1=single-use, n=n-mal nutzbar
- `note` (str): Notiz zum Drucken
- `up` (int): Upload-Limit in Kbps
- `down` (int): Download-Limit in Kbps
- `bytes` (int): Daten-Limit in MB

**Dateien:**
- [x] `src/managers/hotspot_manager.py`
- [x] `src/tools/hotspot.py`
- [x] `src/schemas.py` - VOUCHER_SCHEMA hinzufügen
- [x] `src/validator_registry.py` - voucher Validator registrieren
- [x] `src/utils/permissions.py` - CATEGORY_MAP erweitern
- [x] `src/runtime.py` - hotspot_manager hinzufügen
- [x] `tests/unit/test_hotspot.py`

---

### 2. User Groups / Bandwidth Limits
**Priorität:** Hoch

| Tool | Endpoint | Beschreibung |
|------|----------|--------------|
| `unifi_list_usergroups` | GET `/rest/usergroup` | Alle Benutzergruppen |
| `unifi_create_usergroup` | POST `/rest/usergroup` | Neue Gruppe mit Limits |
| `unifi_update_usergroup` | PUT `/rest/usergroup/{id}` | Limits ändern |
| `unifi_get_usergroup_details` | GET `/rest/usergroup/{id}` | Gruppen-Details |

**Usergroup Parameter:**
- `name` (str, required): Gruppenname
- `qos_rate_max_down` (int): Download-Limit in Kbps
- `qos_rate_max_up` (int): Upload-Limit in Kbps

**Dateien:**
- [x] `src/managers/usergroup_manager.py`
- [x] `src/tools/usergroups.py`
- [x] `src/schemas.py` - USERGROUP_SCHEMA hinzufügen
- [x] `src/validator_registry.py` - usergroup Validator registrieren
- [x] `src/utils/permissions.py` - CATEGORY_MAP erweitern
- [x] `src/runtime.py` - usergroup_manager hinzufügen
- [x] `tests/unit/test_usergroups.py`

---

### 3. Static Routes (Routing-Tabellen)
**Priorität:** Mittel

| Tool | Endpoint | Beschreibung |
|------|----------|--------------|
| `unifi_list_routes` | GET `/rest/routing` | Statische Routen |
| `unifi_get_route_details` | GET `/rest/routing/{id}` | Route-Details |
| `unifi_create_route` | POST `/rest/routing` | Neue Route anlegen |
| `unifi_update_route` | PUT `/rest/routing/{id}` | Route bearbeiten |

**Route Parameter:**
- `name` (str): Routenname
- `static_route_network` (str): Ziel-Netzwerk (CIDR)
- `static_route_nexthop` (str): Next-Hop IP oder Interface
- `static_route_distance` (int): Administrative Distanz
- `enabled` (bool): Aktiviert

**Dateien:**
- [x] `src/managers/routing_manager.py`
- [x] `src/tools/routing.py`
- [x] `src/schemas.py` - ROUTE_SCHEMA hinzufügen
- [x] `src/validator_registry.py` - route Validator registrieren
- [x] `src/utils/permissions.py` - CATEGORY_MAP erweitern
- [x] `src/runtime.py` - routing_manager hinzufügen
- [x] `tests/unit/test_routing.py`

---

### 4. Event Logs
**Priorität:** Mittel

| Tool | Endpoint | Beschreibung |
|------|----------|--------------|
| `unifi_list_events` | POST `/stat/event` | Events mit Filtern |

**Event Query Parameter:**
- `within` (int): Stunden zurück (default 24)
- `limit` (int): Max. Anzahl Events (default 100, max 3000)
- `_start` (int): Offset für Pagination
- `type` (str, optional): Event-Typ Filter

**Event-Typen (Beispiele):**
- `EVT_SW_*` - Switch Events
- `EVT_AP_*` - Access Point Events
- `EVT_GW_*` - Gateway Events
- `EVT_LAN_*` - LAN Events
- `EVT_WU_*` - WLAN User Events

**Dateien:**
- [x] `src/managers/event_manager.py`
- [x] `src/tools/events.py`
- [x] `src/runtime.py` - event_manager hinzufügen
- [x] `tests/unit/test_events.py`

**Hinweis:** Hauptsächlich read-only. Zusätzlich implementiert: Alarm-Archivierung.

**Implementierte Tools:**
- `unifi_list_events` - Events mit Filtern auflisten
- `unifi_list_alarms` - Aktive Alarme auflisten
- `unifi_get_event_types` - Event-Typ Prefixe anzeigen
- `unifi_archive_alarm` - Einzelnen Alarm archivieren
- `unifi_archive_all_alarms` - Alle Alarme archivieren

---

## Architektur-Referenz

### Manager Pattern
```python
import logging
from typing import Dict, List, Optional, Any
from aiounifi.models.api import ApiRequest  # oder ApiRequestV2
from .connection_manager import ConnectionManager

logger = logging.getLogger("unifi-network-mcp")
CACHE_PREFIX_XXX = "xxx"

class XxxManager:
    def __init__(self, connection_manager: ConnectionManager):
        self._connection = connection_manager

    async def get_xxx(self) -> List[Dict[str, Any]]:
        cache_key = f"{CACHE_PREFIX_XXX}_{self._connection.site}"
        cached = self._connection.get_cached(cache_key)
        if cached is not None:
            return cached
        try:
            api_request = ApiRequest(method="get", path="/rest/xxx")
            response = await self._connection.request(api_request)
            # Handle response...
            self._connection._update_cache(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"Error getting xxx: {e}")
            return []
```

### Tool Pattern
```python
from src.runtime import server, config, xxx_manager
from src.utils.permissions import parse_permission

@server.tool(
    name="unifi_list_xxx",
    description="List all xxx on the UniFi controller.",
)
async def list_xxx() -> Dict[str, Any]:
    if not parse_permission(config.permissions, "xxx", "read"):
        return {"success": False, "error": "Permission denied."}
    try:
        items = await xxx_manager.get_xxx()
        return {
            "success": True,
            "site": xxx_manager._connection.site,
            "count": len(items),
            "items": items,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
```

### Permission Category Map (zu erweitern in permissions.py)
```python
CATEGORY_MAP = {
    # ... existing ...
    "voucher": "vouchers",
    "usergroup": "usergroups",
    "route": "routes",
    "event": "events",
}
```

---

## Implementierungs-Reihenfolge

1. **Hotspot Vouchers** - Sehr praktisch für Gäste-Management
2. **User Groups** - Bandbreiten-Management
3. **Event Logs** - Read-only, einfach zu implementieren
4. **Static Routes** - Fortgeschrittenes Routing

---

## Notizen

- API verwendet V1 (`ApiRequest`) für die meisten REST-Endpoints
- V2 (`ApiRequestV2`) nur für neuere Endpoints wie `/qos-rules`
- Delete-Operationen sind global deaktiviert (permissions.py)
- Alle write-Operationen brauchen `confirm=True` Parameter
- Tests folgen Pattern in `tests/unit/test_client_ip_settings.py`
