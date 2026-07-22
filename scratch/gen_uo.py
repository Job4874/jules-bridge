lines = [  
    '\" \\UnifiedOperator "module.\\\',  
    'from __future__ import annotations',  
    'import json, os, sqlite3, subprocess, sys, time',  
    'from datetime import datetime, timezone',  
    'from pathlib import Path',  
    'from typing import Any, Dict, List, Optional, Tuple, TypedDict',  
    '_ROOT = Path(__file__).resolve().parent.parent',  
    '_DB_PATH = _ROOT / \memory\ / \unified_operator_state.db\',  
    '_HEARTBEAT_PATH = _ROOT / \memory\ / \operator_heartbeat.json\',  
]  
open('modules/unified_operator.py', 'w', encoding='utf-8').write('\n'.join(lines)) 
