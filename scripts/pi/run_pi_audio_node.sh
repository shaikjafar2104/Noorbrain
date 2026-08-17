#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# Pi Audio Node launcher — reboot-safe
# ============================================================
# Reads the node token from a secured file and execs
# the Pi audio node Python process.
# NEVER echoes the token.

TOKEN_FILE="/home/project/.config/noorbrain/pi-audio-node.token"

if [ ! -f "$TOKEN_FILE" ]; then
    echo "ERROR: Token file not found at $TOKEN_FILE" >&2
    exit 1
fi

# Read token without echo
TOKEN="$(cat "$TOKEN_FILE")"
if [ -z "$TOKEN" ]; then
    echo "ERROR: Token file is empty" >&2
    exit 1
fi

export NOORBRAIN_NODE_TOKEN="$TOKEN"
unset TOKEN

exec /home/project/Projects/NoorCameraNode/venv/bin/python \
    /home/project/Projects/NoorCameraNode/noorbrain_pi_audio_node.py
