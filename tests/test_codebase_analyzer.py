import json

from modules.codebase_analyzer import analyze_codebase


def _write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_analyze_codebase_summarizes_routes_and_integrations(tmp_path):
    _write(
        tmp_path / "bridge.py",
        '''
from flask import Flask
app = Flask(__name__)
@app.route("/chat", methods=["POST"])
def chat_route():
    pass
@app.route("/codebase/analyze", methods=["POST"])
def codebase_route():
    pass
@app.route("/inbox/append", methods=["POST"])
def inbox_append_route():
    pass
''',
    )
    _write(tmp_path / "modules" / "vm_relay.py", "# vm")
    _write(tmp_path / "modules" / "chat_service.py", "# chat")
    _write(tmp_path / "modules" / "inbox_service.py", "# inbox")
    _write(tmp_path / "modules" / "gemini_cli.py", "# gemini")
    _write(tmp_path / "modules" / "antigravity_cli.py", "# agy")
    _write(tmp_path / "modules" / "alliance_switchboard.py", "# alliance")
    _write(tmp_path / "tests" / "test_chat_service.py", "def test_chat(): pass")
    _write(
        tmp_path / "dashboard-ui" / "package.json",
        json.dumps({
            "name": "dashboard-ui",
            "dependencies": {"react": "^19.0.0"},
            "devDependencies": {"vite": "^8.0.0"},
            "scripts": {"build": "vite build"},
        }),
    )
    _write(tmp_path / "dashboard-ui" / "src" / "App.jsx", "export default function App() {}")

    result = analyze_codebase(root_path=tmp_path, max_files=200)

    assert result["ok"] is True
    assert result["summary"]["route_count"] == 3
    assert result["summary"]["module_count"] == 6
    assert result["frontend"]["dependency_count"] == 2
    ready = {row["id"]: row["ready"] for row in result["integrations"]}
    assert ready["vm_worker_chat"] is True
    assert ready["codebase_analyzer"] is True
    assert ready["gemini_cli"] is True
    assert result["handoff"]["route"] == "POST /codebase/analyze"


def test_analyze_codebase_redacts_env_values(tmp_path):
    _write(tmp_path / "bridge.py", "@app.route('/ping')\ndef ping(): pass")
    _write(tmp_path / ".env", "OPENAI_API_KEY=super-secret-value\nGCE_WORKER_IP=10.0.0.1\n")

    result = analyze_codebase(root_path=tmp_path, max_files=50)
    payload_text = json.dumps(result)

    assert result["environment"]["values_redacted"] is True
    assert "OPENAI_API_KEY" in result["environment"]["env_keys_present"]
    assert "GCE_WORKER_IP" in result["environment"]["env_keys_present"]
    assert "super-secret-value" not in payload_text
    assert "10.0.0.1" not in payload_text


def test_analyze_codebase_missing_root_returns_error(tmp_path):
    result = analyze_codebase(root_path=tmp_path / "missing")

    assert result["ok"] is False
    assert result["status"] == "error"
    assert "root_path" in result["error"]


def test_analyze_codebase_skips_node_modules(tmp_path):
    _write(tmp_path / "bridge.py", "@app.route('/ping')\ndef ping(): pass")
    _write(tmp_path / "node_modules" / "package" / "index.js", "const secret = 'skip me';")

    result = analyze_codebase(root_path=tmp_path, max_files=50, include_files=True)

    assert result["ok"] is True
    assert all("node_modules" not in row["path"] for row in result["files"])
