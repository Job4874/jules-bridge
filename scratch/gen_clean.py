from pathlib import Path  
code = '''import json, os, sqlite3, subprocess, sys, time  
from datetime import datetime, timezone  
from pathlib import Path  
from typing import Any, Dict, List, Optional, Tuple, TypedDict  
_ROOT = Path(__file__).resolve().parent.parent  
_DB_PATH = _ROOT / 'memory' / 'unified_operator_state.db'  
_HEARTBEAT_PATH = _ROOT / 'memory' / 'operator_heartbeat.json'  
'''  
code += '''  
class CheckpointRecord(TypedDict):  
    idempotency_key: str  
    goal: str  
    workflow_step: str  
    status: str  
    git_branch: str  
    git_commit: str  
    cloud_session_id: Optional[str]  
    payload: Dict[str, Any]  
    created_at_utc: str  
    updated_at_utc: str  
class UnifiedOperatorStateDB:  
    def __init__(self, db_path: Path = _DB_PATH) -> None:  
        self.db_path = db_path  
        self.db_path.parent.mkdir(parents=True, exist_ok=True)  
        self._init_db()  
    def _get_connection(self) -> sqlite3.Connection:  
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)  
        conn.execute('PRAGMA journal_mode=WAL;')  
        conn.execute('PRAGMA busy_timeout=5000;')  
        conn.row_factory = sqlite3.Row  
        return conn  
'''  
Path('modules/unified_operator.py').write_text(code, encoding='utf-8')  
code += '''  
    def _init_db(self) -> None:  
        with self._get_connection() as conn:  
            conn.executescript('''  
                CREATE TABLE IF NOT EXISTS checkpoints (idempotency_key TEXT PRIMARY KEY, goal TEXT NOT NULL, workflow_step TEXT NOT NULL, status TEXT NOT NULL, git_branch TEXT, git_commit TEXT, cloud_session_id TEXT, payload_json TEXT NOT NULL, created_at_utc TEXT NOT NULL, updated_at_utc TEXT NOT NULL);  
                CREATE TABLE IF NOT EXISTS task_queue (task_id TEXT PRIMARY KEY, description TEXT NOT NULL, dependencies_json TEXT NOT NULL, status TEXT NOT NULL, priority INTEGER DEFAULT 0, idempotency_key TEXT UNIQUE, payload_json TEXT NOT NULL, created_at_utc TEXT NOT NULL);  
                CREATE TABLE IF NOT EXISTS cloud_outbox (outbox_id TEXT PRIMARY KEY, action_type TEXT NOT NULL, payload_json TEXT NOT NULL, status TEXT NOT NULL, retry_count INTEGER DEFAULT 0, created_at_utc TEXT NOT NULL);  
                CREATE TABLE IF NOT EXISTS recovery_events (event_id TEXT PRIMARY KEY, reason TEXT NOT NULL, component TEXT NOT NULL, recovered_at_utc TEXT NOT NULL, details_json TEXT);  
            ''')  
            conn.commit()  
    def save_checkpoint(self, idempotency_key: str, goal: str, workflow_step: str, status: str = 'in_progress', git_branch: str = '', git_commit: str = '', cloud_session_id: Optional[str] = None, payload: Optional[Dict[str, Any]] = None) -> CheckpointRecord:  
        now = datetime.now(timezone.utc).isoformat()  
        payload_json = json.dumps(payload or {})  
        with self._get_connection() as conn:  
            conn.execute('''INSERT INTO checkpoints (idempotency_key, goal, workflow_step, status, git_branch, git_commit, cloud_session_id, payload_json, created_at_utc, updated_at_utc) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(idempotency_key) DO UPDATE SET status=excluded.status, workflow_step=excluded.workflow_step, payload_json=excluded.payload_json, updated_at_utc=excluded.updated_at_utc''', (idempotency_key, goal, workflow_step, status, git_branch, git_commit, cloud_session_id, payload_json, now, now))  
            conn.commit()  
        return self.get_checkpoint(idempotency_key)  
    def get_checkpoint(self, idempotency_key: str) -> Optional[CheckpointRecord]:  
        with self._get_connection() as conn:  
            row = conn.execute('SELECT * FROM checkpoints WHERE idempotency_key = ?', (idempotency_key,)).fetchone()  
            if not row: return None  
            return {'idempotency_key': row['idempotency_key'], 'goal': row['goal'], 'workflow_step': row['workflow_step'], 'status': row['status'], 'git_branch': row['git_branch'], 'git_commit': row['git_commit'], 'cloud_session_id': row['cloud_session_id'], 'payload': json.loads(row['payload_json']), 'created_at_utc': row['created_at_utc'], 'updated_at_utc': row['updated_at_utc']}  
    def list_active_checkpoints(self) -> List[CheckpointRecord]:  
        with self._get_connection() as conn:  
            rows = conn.execute(\" SELECT * FROM checkpoints WHERE status NOT IN completed failed ORDER BY updated_at_utc "DESC\).fetchall()  
            return [{'idempotency_key': r['idempotency_key'], 'goal': r['goal'], 'workflow_step': r['workflow_step'], 'status': r['status'], 'git_branch': r['git_branch'], 'git_commit': r['git_commit'], 'cloud_session_id': r['cloud_session_id'], 'payload': json.loads(r['payload_json']), 'created_at_utc': r['created_at_utc'], 'updated_at_utc': r['updated_at_utc']} for r in rows]  
    def record_recovery_event(self, reason: str, component: str, details: Optional[Dict[str, Any]] = None) -> str:  
        now = datetime.now(timezone.utc).isoformat()  
        event_id = f'rec_{int(time.time() * 1000)}'  
        with self._get_connection() as conn:  
            conn.execute('INSERT INTO recovery_events (event_id, reason, component, recovered_at_utc, details_json) VALUES (?, ?, ?, ?, ?)', (event_id, reason, component, now, json.dumps(details or {})))  
            conn.commit()  
        return event_id  
'''  
code += '''  
    def _init_db(self) -> None:  
        with self._get_connection() as conn:  
            conn.executescript('CREATE TABLE IF NOT EXISTS checkpoints (idempotency_key TEXT PRIMARY KEY, goal TEXT NOT NULL, workflow_step TEXT NOT NULL, status TEXT NOT NULL, git_branch TEXT, git_commit TEXT, cloud_session_id TEXT, payload_json TEXT NOT NULL, created_at_utc TEXT NOT NULL, updated_at_utc TEXT NOT NULL); CREATE TABLE IF NOT EXISTS task_queue (task_id TEXT PRIMARY KEY, description TEXT NOT NULL, dependencies_json TEXT NOT NULL, status TEXT NOT NULL, priority INTEGER DEFAULT 0, idempotency_key TEXT UNIQUE, payload_json TEXT NOT NULL, created_at_utc TEXT NOT NULL); CREATE TABLE IF NOT EXISTS cloud_outbox (outbox_id TEXT PRIMARY KEY, action_type TEXT NOT NULL, payload_json TEXT NOT NULL, status TEXT NOT NULL, retry_count INTEGER DEFAULT 0, created_at_utc TEXT NOT NULL); CREATE TABLE IF NOT EXISTS recovery_events (event_id TEXT PRIMARY KEY, reason TEXT NOT NULL, component TEXT NOT NULL, recovered_at_utc TEXT NOT NULL, details_json TEXT);')  
            conn.commit()  
    def save_checkpoint(self, idempotency_key: str, goal: str, workflow_step: str, status: str = 'in_progress', git_branch: str = '', git_commit: str = '', cloud_session_id: Optional[str] = None, payload: Optional[Dict[str, Any]] = None) -> CheckpointRecord:  
        now = datetime.now(timezone.utc).isoformat()  
        payload_json = json.dumps(payload or {})  
        with self._get_connection() as conn:  
            conn.execute('INSERT INTO checkpoints (idempotency_key, goal, workflow_step, status, git_branch, git_commit, cloud_session_id, payload_json, created_at_utc, updated_at_utc) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(idempotency_key) DO UPDATE SET status=excluded.status, workflow_step=excluded.workflow_step, payload_json=excluded.payload_json, updated_at_utc=excluded.updated_at_utc', (idempotency_key, goal, workflow_step, status, git_branch, git_commit, cloud_session_id, payload_json, now, now))  
            conn.commit()  
        return self.get_checkpoint(idempotency_key)  
    def get_checkpoint(self, idempotency_key: str) -> Optional[CheckpointRecord]:  
        with self._get_connection() as conn:  
            row = conn.execute('SELECT * FROM checkpoints WHERE idempotency_key = ?', (idempotency_key,)).fetchone()  
            if not row: return None  
            return {'idempotency_key': row['idempotency_key'], 'goal': row['goal'], 'workflow_step': row['workflow_step'], 'status': row['status'], 'git_branch': row['git_branch'], 'git_commit': row['git_commit'], 'cloud_session_id': row['cloud_session_id'], 'payload': json.loads(row['payload_json']), 'created_at_utc': row['created_at_utc'], 'updated_at_utc': row['updated_at_utc']}  
    def list_active_checkpoints(self) -> List[CheckpointRecord]:  
        with self._get_connection() as conn:  
            rows = conn.execute(\" SELECT * FROM checkpoints WHERE status NOT IN completed failed ORDER BY updated_at_utc "DESC\).fetchall()  
            return [{'idempotency_key': r['idempotency_key'], 'goal': r['goal'], 'workflow_step': r['workflow_step'], 'status': r['status'], 'git_branch': r['git_branch'], 'git_commit': r['git_commit'], 'cloud_session_id': r['cloud_session_id'], 'payload': json.loads(r['payload_json']), 'created_at_utc': r['created_at_utc'], 'updated_at_utc': r['updated_at_utc']} for r in rows]  
    def record_recovery_event(self, reason: str, component: str, details: Optional[Dict[str, Any]] = None) -> str:  
        now = datetime.now(timezone.utc).isoformat()  
        event_id = f'rec_{int(time.time() * 1000)}'  
        with self._get_connection() as conn:  
            conn.execute('INSERT INTO recovery_events (event_id, reason, component, recovered_at_utc, details_json) VALUES (?, ?, ?, ?, ?)', (event_id, reason, component, now, json.dumps(details or {})))  
            conn.commit()  
        return event_id  
'''  
