import os
import re

filepath = 'modules/jules_orchestrator.py'
with open(filepath, 'r') as f:
    lines = f.readlines()

def get_block(start_line, end_line):
    return "".join(lines[start_line-1:end_line])

# Parser
with open('modules/jules/parser.py', 'w') as f:
    f.write("from __future__ import annotations\nfrom .models import *\nfrom .utils import *\nimport hashlib\nimport re\nfrom pathlib import Path\nfrom typing import Iterable\n\n")
    f.write(get_block(117, 163))
    f.write("\n")
    f.write(get_block(165, 226))
    f.write("\n")
    f.write(get_block(1525, 1612)) # helpers
    f.write("\n")
    f.write(get_block(1618, 1636)) # more helpers
    f.write("\n")
    f.write(get_block(1666, 1682)) # dedupe
    f.write("\n")
    f.write(get_block(1638, 1647)) # status filter
    f.write("\n")
    f.write(get_block(1649, 1664)) # select tasks
    f.write("\n")
    f.write(get_block(2197, 2204)) # _packet_id_from_path
    f.write("\n")
    f.write(get_block(2247, 2250)) # _extract_packet_ids
