"""Jules mesh registry — discover and coordinate all connected nodes.

Public interface:
    mesh_registry_path() -> Path
    load_mesh_registry() -> MeshRegistry
    register_local_node(**overrides) -> MeshRegistry
    get_mesh_status(repo_root) -> MeshStatus
"""
from __future__ import annotations

import json
import os
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request


class MeshRegistry(dict):
    """Keys: version, updated_utc, primary_host_id, nodes."""


class MeshStatus(dict):
    """Aggregated mesh view for GET /mesh/status."""


_DEFAULT_REGISTRY = {
    "version": 1,
    "primary_host_id": "school-64gb",
    "nodes": [],
}

_NODE_TEMPLATES = {
    "gcp-offload-worker": {
        "host_id": "gcp-offload-worker",
        "role": "compute_worker",
        "capabilities": ["shell", "llm", "build"],
        "parent_host_id": "school-64gb",
        "agent_url": "http://34.132.193.73:6000",
        "cloud": "gcp",
    },
    "jules-cloud-fleet": {
        "host_id": "jules-cloud-fleet",
        "role": "jules_workers",
        "capabilities": ["jules_cli", "jules_rest"],
        "parent_host_id": "school-64gb",
        "notes": "Google Jules remote sessions via POST /jules/fleet on primary bridge",
    },
    "laptop": {
        "host_id": "laptop",
        "role": "mobile",
        "capabilities": ["jules_cli", "cursor", "bridge"],
        "location": "mobile",
    },
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def mesh_registry_path(repo_root: str | None = None) -> Path:
    root = Path(repo_root) if repo_root else _repo_root()
    return root / "jules_inbox" / "MESH_REGISTRY.json"


def _ngrok_domain() -> str:
    return os.environ.get("NGROK_DOMAIN", "parade-marrow-pulp.ngrok-free.dev").strip()


def _ngrok_public_url() -> str:
    explicit = os.environ.get("NGROK_PUBLIC_URL", "").strip()
    if explicit:
        return explicit.rstrip("/")
    return f"https://{_ngrok_domain()}"


def _local_bridge_url() -> str:
    return os.environ.get("LOCAL_BRIDGE_URL", "http://127.0.0.1:5000").rstrip("/")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def load_mesh_registry(repo_root: str | None = None) -> MeshRegistry:
    path = mesh_registry_path(repo_root)
    data = dict(_DEFAULT_REGISTRY)
    if path.is_file():
        data.update(_read_json(path))
    if not data.get("nodes"):
        data["nodes"] = [_NODE_TEMPLATES["gcp-offload-worker"], _NODE_TEMPLATES["jules-cloud-fleet"]]
    return MeshRegistry(data)


def _upsert_node(nodes: list[dict[str, Any]], node: dict[str, Any]) -> list[dict[str, Any]]:
    host_id = node.get("host_id")
    if not host_id:
        return nodes
    updated = [n for n in nodes if n.get("host_id") != host_id]
    updated.append(node)
    return updated


def register_local_node(repo_root: str | None = None, **overrides: Any) -> MeshRegistry:
    """Register or refresh this machine in MESH_REGISTRY.json."""
    from modules import ghost_state  # local import avoids circular at load time

    identity = ghost_state.get_host_identity()
    host_id = overrides.get("host_id") or os.environ.get("HOST_ID") or identity.get("host_id", "school-64gb")
    role = overrides.get("role") or os.environ.get("HOST_ROLE") or (
        "primary" if host_id == "school-64gb" else "secondary"
    )

    node = {
        "host_id": host_id,
        "role": role,
        "hostname": socket.gethostname(),
        "location": overrides.get("location") or os.environ.get("HOST_LOCATION") or identity.get("location", "school"),
        "ram_gb": overrides.get("ram_gb") or int(os.environ.get("HOST_RAM_GB", identity.get("ram_gb", 64) or 64)),
        "capabilities": overrides.get("capabilities") or [
            "bridge", "jules_cli", "shell", "ui", "oracle", "git", "gpg",
        ],
        "bridge_urls": {
            "local": _local_bridge_url(),
            "remote": _ngrok_public_url(),
        },
        "github": {
            "user": "Job4874",
            "repo": "Job4874/jules-bridge",
            "remote": "https://github.com/Job4874/jules-bridge.git",
        },
        "jules_source": os.environ.get("JULES_SOURCE", "sources/github/Job4874/jules-bridge"),
        "ghost_locked": identity.get("ghost_locked", False),
        "last_seen_utc": datetime.now(timezone.utc).isoformat(),
        "status": "online",
    }
    node.update({k: v for k, v in overrides.items() if k not in ("host_id",)})

    registry = load_mesh_registry(repo_root)
    nodes = list(registry.get("nodes") or [])
    nodes = _upsert_node(nodes, node)

    for template_id in ("gcp-offload-worker", "jules-cloud-fleet"):
        tpl = dict(_NODE_TEMPLATES[template_id])
        if not any(n.get("host_id") == tpl["host_id"] for n in nodes):
            nodes.append(tpl)

    laptop = dict(_NODE_TEMPLATES["laptop"])
    if host_id != "laptop" and not any(n.get("host_id") == "laptop" for n in nodes):
        nodes.append({**laptop, "status": "offline", "notes": "Register laptop with HOST_ID=laptop on that machine"})

    primary = os.environ.get("MESH_PRIMARY_HOST_ID", registry.get("primary_host_id", "school-64gb"))
    registry["primary_host_id"] = primary
    registry["nodes"] = nodes
    registry["updated_utc"] = datetime.now(timezone.utc).isoformat()
    registry["connect"] = {
        "primary_bridge_remote": _ngrok_public_url(),
        "auth_header": "Authorization: Bearer <BRIDGE_TOKEN>",
        "ngrok_header": "ngrok-skip-browser-warning: true",
        "discovery": "GET /mesh/status",
        "identity": "GET /host/identity",
    }

    path = mesh_registry_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(registry, indent=2), encoding="utf-8")
    return MeshRegistry(registry)


def _ping_url(url: str, timeout: float = 3.0) -> bool:
    try:
        req = request.Request(f"{url.rstrip('/')}/ping", headers={"ngrok-skip-browser-warning": "true"})
        with request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except (error.URLError, OSError, TimeoutError):
        return False


def get_mesh_status(repo_root: str | None = None) -> MeshStatus:
    """Aggregate registry, tunnel, identity, and fleet snapshot."""
    root = Path(repo_root) if repo_root else _repo_root()
    registry = load_mesh_registry(str(root))
    primary_id = registry.get("primary_host_id", "school-64gb")
    nodes = list(registry.get("nodes") or [])

    tunnel_path = root / "jules_inbox" / "TUNNEL_HEALTH.json"
    tunnel = _read_json(tunnel_path)
    identity_path = root / "jules_inbox" / "HOST_IDENTITY.json"
    identity = _read_json(identity_path)
    fleet_path = root / "jules_inbox" / "jules_dispatch" / "JULES_FLEET_STATE.json"
    fleet = _read_json(fleet_path)

    primary = next((n for n in nodes if n.get("host_id") == primary_id), None)
    remote_url = (primary or {}).get("bridge_urls", {}).get("remote") or _ngrok_public_url()
    local_url = _local_bridge_url()

    return MeshStatus(
        {
            "status": "ok",
            "primary_host_id": primary_id,
            "primary_bridge": {
                "local": local_url,
                "remote": remote_url,
                "local_up": _ping_url(local_url),
                "remote_up": _ping_url(remote_url),
            },
            "tunnel": tunnel or {"status": "unknown"},
            "host_identity": identity,
            "nodes": nodes,
            "jules_fleet": {
                "status": fleet.get("status"),
                "active_remote_count": fleet.get("active_remote_count"),
                "max_concurrent": fleet.get("max_concurrent"),
            },
            "connect_hints": registry.get("connect", {}),
            "updated_utc": datetime.now(timezone.utc).isoformat(),
        }
    )
