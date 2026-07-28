#!/usr/bin/env bash
PID="$(lsof -tiTCP:8001 -sTCP:LISTEN 2>/dev/null | head -n1 || true)"
if [ -z "$PID" ]; then echo "NoorBrain is already stopped."; exit 0; fi
kill "$PID" 2>/dev/null || true
for _ in $(seq 1 10); do kill -0 "$PID" 2>/dev/null || { echo "NoorBrain stopped."; exit 0; }; sleep 1; done
kill -9 "$PID" 2>/dev/null || true
echo "NoorBrain force-stopped."
