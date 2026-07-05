import subprocess
from pathlib import Path

from modules.cloud_sync import build_cloud_publish_packet, get_cloud_sync_status


def _run(args, cwd):
    subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


def _make_synced_repo(tmp_path):
    work = tmp_path / "work"
    remote = tmp_path / "remote.git"
    work.mkdir()
    _run(["git", "init", "-b", "master"], work)
    _run(["git", "config", "user.email", "test@example.com"], work)
    _run(["git", "config", "user.name", "Test User"], work)
    (work / "README.md").write_text("hello\n", encoding="utf-8")
    _run(["git", "add", "README.md"], work)
    _run(["git", "commit", "-m", "initial"], work)
    _run(["git", "init", "--bare", str(remote)], tmp_path)
    _run(["git", "remote", "add", "origin", str(remote)], work)
    _run(["git", "push", "-u", "origin", "master"], work)
    return work


def test_cloud_sync_status_reports_synced_clean_repo(tmp_path, monkeypatch):
    work = _make_synced_repo(tmp_path)
    monkeypatch.setattr("modules.cloud_sync.shutil.which", lambda name: None)

    result = get_cloud_sync_status(work, use_cache=False)

    assert result["status"] == "ready"
    assert result["state"] == "synced"
    assert result["synced"] is True
    assert result["publish_ready"] is False
    assert result["git"]["dirty_count"] == 0
    assert result["git"]["ahead"] == 0
    assert result["git"]["behind"] == 0
    assert result["blockers"] == []
    assert result["privacy"]["remote_url_returned"] is False


def test_cloud_sync_status_blocks_dirty_worktree(tmp_path, monkeypatch):
    work = _make_synced_repo(tmp_path)
    monkeypatch.setattr("modules.cloud_sync.shutil.which", lambda name: None)
    (work / "README.md").write_text("hello\nchanged\n", encoding="utf-8")
    (work / "scratch.txt").write_text("new\n", encoding="utf-8")

    result = get_cloud_sync_status(work, use_cache=False)

    assert result["status"] == "blocked"
    assert result["state"] == "blocked"
    assert "dirty_worktree" in result["blockers"]
    assert result["git"]["dirty_count"] == 2
    assert result["git"]["unstaged_count"] == 1
    assert result["git"]["untracked_count"] == 1
    assert result["publish_ready"] is False


def test_cloud_sync_status_blocks_missing_repo(tmp_path):
    missing = tmp_path / "missing"

    result = get_cloud_sync_status(missing, use_cache=False)

    assert result["status"] == "blocked"
    assert result["state"] == "blocked"
    assert result["blockers"] == ["missing_repo"]


def test_cloud_publish_packet_classifies_dirty_worktree(tmp_path, monkeypatch):
    work = _make_synced_repo(tmp_path)
    monkeypatch.setattr("modules.cloud_sync.shutil.which", lambda name: None)
    modules_dir = work / "modules"
    modules_dir.mkdir()
    (modules_dir / "cloud_sync.py").write_text("# sync\n", encoding="utf-8")
    (work / "bridge.py").write_text("# bridge\n", encoding="utf-8")
    (work / "bridge.log.1").write_text("rotated log\n", encoding="utf-8")

    result = build_cloud_publish_packet(work, objective="Publish dashboard sync work", use_cache=False)

    assert result["status"] == "blocked"
    assert result["state"] == "blocked"
    assert "dirty_worktree" in result["blockers"]
    families = {row["family"]: row for row in result["change_families"]}
    assert families["backend_modules"]["count"] == 1
    assert families["bridge_routes"]["count"] == 1
    assert families["generated_noise"]["count"] == 1
    assert result["include_candidate_count"] == 2
    assert result["exclude_candidate_count"] == 1
    assert "git add --" in result["commands"][1]["command"]
    assert "bridge.log.1" not in result["commands"][1]["command"]
    assert "This packet did not run git add" in result["packet"]


def test_cloud_publish_packet_writes_repo_local_packet(tmp_path, monkeypatch):
    work = _make_synced_repo(tmp_path)
    monkeypatch.setattr("modules.cloud_sync.shutil.which", lambda name: None)
    (work / "tests").mkdir()
    (work / "tests" / "test_cloud_sync.py").write_text("def test_x(): pass\n", encoding="utf-8")

    result = build_cloud_publish_packet(
        work,
        objective="Save publish packet",
        write_packet=True,
        output_dir="jules_inbox/cloud_sync",
        use_cache=False,
    )

    assert result["artifacts"]["packet_written"] is True
    packet_path = work / result["artifacts"]["packet_path"]
    state_path = work / result["artifacts"]["state_path"]
    assert packet_path.is_file()
    assert state_path.is_file()
    assert packet_path.read_text(encoding="utf-8").startswith("# Cloud Publish Packet")


def test_cloud_publish_packet_rejects_output_dir_outside_repo(tmp_path, monkeypatch):
    work = _make_synced_repo(tmp_path)
    monkeypatch.setattr("modules.cloud_sync.shutil.which", lambda name: None)
    (work / "README.md").write_text("changed\n", encoding="utf-8")

    result = build_cloud_publish_packet(
        work,
        write_packet=True,
        output_dir=str(tmp_path / "outside"),
        use_cache=False,
    )

    assert result["artifacts"]["packet_written"] is False
    assert "inside the repository" in result["artifacts"]["error"]
