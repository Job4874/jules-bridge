#!/bin/bash
# jules-start.sh — starts jules-worker-agent.py in the background
set -e
cd ~
pkill -f jules-worker-agent 2>/dev/null || true
sleep 1
nohup ~/venv/bin/python ~/jules-worker-agent.py >> ~/worker.log 2>&1 &
echo "Agent PID: $!"
sleep 3
if curl -s --connect-timeout 3 http://localhost:6000/ping > /tmp/ping.json 2>/dev/null; then
    echo "AGENT_RUNNING"
    cat /tmp/ping.json
else
    echo "AGENT_NOT_RESPONDING"
    tail -20 ~/worker.log
fi
