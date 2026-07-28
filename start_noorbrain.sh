#!/usr/bin/env bash
set -u
ROOT="$HOME/Projects/NoorBrain"
LOG="$ROOT/logs/noorbrain.log"
URL="http://127.0.0.1:8001"
mkdir -p "$ROOT/logs"
cd "$ROOT" || exit 1

# NoorBrain CPU limits
export OMP_NUM_THREADS=4
export MKL_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
export NUMEXPR_NUM_THREADS=4
OLD_PID="$(lsof -tiTCP:8001 -sTCP:LISTEN 2>/dev/null | head -n1 || true)"
if [ -n "$OLD_PID" ]; then
  if curl -fsS "$URL/health" >/dev/null 2>&1; then
    xdg-open "$URL/studio?v=$(date +%s)" >/dev/null 2>&1 &
    echo "NoorBrain is already running: $URL/studio"
    exit 0
  fi
  kill "$OLD_PID" 2>/dev/null || true
  sleep 2
  kill -9 "$OLD_PID" 2>/dev/null || true
fi
source "$ROOT/venv/bin/activate"
: > "$LOG"
nohup python -m uvicorn main:app --host 0.0.0.0 --port 8001 > "$LOG" 2>&1 &
PID=$!
for _ in $(seq 1 90); do
  if ! kill -0 "$PID" 2>/dev/null; then echo "NoorBrain failed:"; tail -80 "$LOG"; exit 1; fi
  if curl -fsS "$URL/health" >/dev/null 2>&1 && curl -fsS "$URL/studio" >/dev/null 2>&1; then
    xdg-open "$URL/studio?v=$(date +%s)" >/dev/null 2>&1 &
    echo "NoorBrain ready: $URL/studio"
    exit 0
  fi
  sleep 1
done
echo "Startup timeout"; tail -80 "$LOG"; exit 1
