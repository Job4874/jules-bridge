"""Tests for mesh_registry module."""
import json
import modules.mesh_registry as mesh


def test_register_local_node_writes_registry(tmp_path, monkeypatch):
    reg_path = tmp_path / "jules_inbox" / "MESH_REGISTRY.json"
    monkeypatch.setattr(mesh, "mesh_registry_path", lambda repo_root=None: reg_path)
    monkeypatch.setenv("HOST_ID", "school-64gb")
    monkeypatch.setenv("HOST_ROLE", "primary")

    result = mesh.register_local_node(repo_root=str(tmp_path))
    assert result["primary_host_id"] == "school-64gb"
    assert reg_path.is_file()

    data = json.loads(reg_path.read_text(encoding="utf-8"))
    host_ids = {n["host_id"] for n in data["nodes"]}
    assert "school-64gb" in host_ids
    assert "gcp-offload-worker" in host_ids
    assert "jules-cloud-fleet" in host_ids


def test_get_mesh_status_shape(tmp_path, monkeypatch):
    reg_path = tmp_path / "jules_inbox" / "MESH_REGISTRY.json"
    monkeypatch.setattr(mesh, "mesh_registry_path", lambda repo_root=None: reg_path)
    mesh.register_local_node(repo_root=str(tmp_path))

    status = mesh.get_mesh_status(repo_root=str(tmp_path))
    assert status["status"] == "ok"
    assert "primary_bridge" in status
    assert "nodes" in status
