import json
from pathlib import Path

from modules.repo_context_guard import build_repo_context_guard


def _repo(root: Path, name: str, remote: str = "") -> Path:
    path = root / name
    git_dir = path / ".git"
    git_dir.mkdir(parents=True)
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    if remote:
        (git_dir / "config").write_text(
            f'[remote "origin"]\n\turl = {remote}\n',
            encoding="utf-8",
        )
    return path


def _package(repo: Path, data: dict) -> None:
    (repo / "package.json").write_text(json.dumps(data), encoding="utf-8")


def test_build_repo_context_guard_detects_port_and_remote_collisions(tmp_path):
    repo_a = _repo(tmp_path, "alpha", "https://github.com/example/shared.git")
    repo_b = _repo(tmp_path, "beta", "https://github.com/example/shared.git")
    _package(repo_a, {"name": "alpha", "scripts": {"dev": "vite --port 5173"}})
    _package(repo_b, {"name": "beta", "scripts": {"dev": "next dev -p 5173"}})

    result = build_repo_context_guard(
        roots=[tmp_path],
        max_depth=2,
        include_repos=True,
        use_cache=False,
    )

    assert result["status"] == "ready"
    assert result["summary"]["repo_count"] == 2
    collision_types = {collision["type"] for collision in result["collisions"]}
    assert "remote_duplicate" in collision_types
    assert "port_collision" in collision_types


def test_build_repo_context_guard_flags_cross_project_local_dependencies(tmp_path):
    repo_a = _repo(tmp_path, "app")
    repo_b = _repo(tmp_path, "extension")
    _package(
        repo_a,
        {
            "name": "app",
            "dependencies": {
                "extension": "file:../extension",
            },
        },
    )
    _package(repo_b, {"name": "extension"})

    result = build_repo_context_guard(roots=[tmp_path], max_depth=2, use_cache=False)

    collisions = [
        collision
        for collision in result["collisions"]
        if collision["type"] == "local_dependency_cross_project"
    ]
    assert collisions
    assert collisions[0]["repo_names"] == ["app", "extension"]


def test_build_repo_context_guard_redacts_secret_values_but_keeps_key_names(tmp_path):
    repo = _repo(tmp_path, "secret-safe")
    (repo / ".env").write_text(
        "\n".join(
            [
                "API_KEY=raw-secret-value",
                "BRIDGE_PORT=5000",
                "WORKER_HOST=127.0.0.1",
            ]
        ),
        encoding="utf-8",
    )

    result = build_repo_context_guard(roots=[tmp_path], max_depth=1, use_cache=False)
    payload_text = json.dumps(result)

    assert "API_KEY" in result["repos"][0]["env_keys_present"]
    assert "raw-secret-value" not in payload_text
    assert result["repos"][0]["ports"][0]["port"] == 5000
    assert result["repos"][0]["node_refs"][0]["value"] == "127.0.0.1"


def test_build_repo_context_guard_never_raises_on_missing_root(tmp_path):
    result = build_repo_context_guard(roots=[tmp_path / "missing"], use_cache=False)

    assert result["status"] == "partial"
    assert result["summary"]["repo_count"] == 0
    assert result["roots_missing"]
