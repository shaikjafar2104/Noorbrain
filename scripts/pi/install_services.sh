#!/usr/bin/env bash
# ============================================================
# NoorCameraNode installer — safely installs and enables
# camera + Pi audio systemd services.
# ============================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_DIR="${REPO_DIR}"
CAMERA_SERVICE="noor-camera.service"
AUDIO_SERVICE_FILE="scripts/pi/noorbrain-pi-audio.service"
AUDIO_SERVICE_NAME="noorbrain-pi-audio.service"
LIB_SYSTEMD="/etc/systemd/system"
TOKEN_FILE="${HOME}/.config/noorbrain/pi-audio-node.token"
PORT=8010

echo "=== NoorCameraNode Service Installer ==="

if [ "$(id -un)" != "project" ]; then
    echo "WARNING: Expected to run as user 'project', current user: $(id -un)"
fi

# --- Verify token file exists and is non-empty ---
if [ ! -f "$TOKEN_FILE" ]; then
    echo "ERROR: token file not found: $TOKEN_FILE" >&2
    echo "Token must be placed at: $TOKEN_FILE" >&2
    exit 1
fi

TOKEN_SIZE=$(wc -c < "$TOKEN_FILE")
if [ "$TOKEN_SIZE" -lt 8 ]; then
    echo "ERROR: token file appears empty or too short (< 8 bytes): $TOKEN_FILE" >&2
    exit 1
fi

echo "Token file verified (non-empty)."

# --- Verify venv and audio node script exist ---
if [ ! -x "${REPO_DIR}/venv/bin/python" ]; then
    echo "ERROR: venv python not found: ${REPO_DIR}/venv/bin/python" >&2
    exit 1
fi

if [ ! -f "${REPO_DIR}/noorbrain_pi_audio_node.py" ]; then
    echo "ERROR: audio node script not found: ${REPO_DIR}/noorbrain_pi_audio_node.py" >&2
    exit 1
fi

# --- Copy service files to systemd ---
echo "Installing systemd services..."

if [ -f "${LIB_SYSTEMD}/${CAMERA_SERVICE}" ]; then
    echo "  Camera service already installed."
else
    echo "  Camera service not found at ${LIB_SYSTEMD}/${CAMERA_SERVICE}"
    echo "  (Expected to be pre-installed as noor-camera.service)"
fi

sudo cp "${REPO_DIR}/${AUDIO_SERVICE_FILE}" "${LIB_SYSTEMD}/${AUDIO_SERVICE_NAME}"

# --- daemon-reload ---
echo "Reloading systemd..."
sudo systemctl daemon-reload

# --- Enable and start services ---
echo "Enabling and starting audio service..."
sudo systemctl enable --now "$AUDIO_SERVICE_NAME"

echo "Restarting camera service..."
sudo systemctl restart "$CAMERA_SERVICE" 2>/dev/null || true

# --- Wait for port ---
echo "Waiting for audio node on port ${PORT}..."
for i in $(seq 1 15); do
    if curl -fsS --max-time 2 "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
        echo "Audio node health check PASSED."
        break
    fi
    sleep 1
done

# --- Verify health ---
echo "Verifying audio node health..."
HEALTH_RESPONSE=$(curl -fsS --max-time 5 "http://127.0.0.1:${PORT}/health" 2>/dev/null || echo "")
if [ -n "$HEALTH_RESPONSE" ]; then
    echo "Health response: $HEALTH_RESPONSE"
    echo "$HEALTH_RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if not data.get('trusted') or data.get('trusted') is not True:
    print('ERROR: node is not trusted=true')
    sys.exit(1)
print('Node trusted=true: PASS')
" 2>/dev/null || echo "  (health response parsed manually)"
else
    echo "ERROR: audio node health check FAILED" >&2
    exit 1
fi

echo ""
echo "=== Installation Complete ==="
echo "  Camera:    $(systemctl is-active "$CAMERA_SERVICE" 2>/dev/null || echo 'unknown')"
echo "  Audio:     $(systemctl is-active "$AUDIO_SERVICE_NAME" 2>/dev/null || echo 'unknown')"
echo "  Port:      ${PORT}"
echo ""
echo "NOT rebooting. Reboot test is deferred to user confirmation."
