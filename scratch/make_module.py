db_code = '''import os, json, sqlite3, subprocess, sys, time  
from datetime import datetime, timezone  
from pathlib import Path  
from typing import Any, Dict, List, Optional, Tuple, TypedDict  
_ROOT = Path(__file__).resolve().parent.parent  
_DB_PATH = _ROOT / 'memory' / 'unified_operator_state.db'  
_HEARTBEAT_PATH = _ROOT / 'memory' / 'operator_heartbeat.json' 
