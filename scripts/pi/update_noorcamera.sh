#!/usr/bin/env bash
# ============================================================
# NoorCameraNode updater — safely updates source and
# restarts both camera and Pi audio services.
# ============================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CAMERA_SERVICE="noor-camera.service"
AUDIO_SERVICE_NAME="noorbrain-pi-audio.service"

echo "=== NoorCameraNode Update ==="

cd "$REPO_DIR"

# --- Git pull ---
echo "Fetching latest source..."
git fetch origin
git pull origin main 2>/dev/null || git pull origin master 2>/dev/null || true

# --- Update dependencies if needed ---
if [ -f "requirements.txt" ]; then
    echo "Installing Python dependencies..."
    "${REPO_DIR}/venv/bin/pip" install -r requirements.txt --quiet 2>/dev/null || true
fi

# --- Install/update systemd services ---
echo "Installing service files..."
if [ -f "${REPO_DIR}/scripts/pi/noorbrain-pi-audio.service" ]; then
    sudo cp "${REPO_DIR}/scripts/pi/noorbrain-pi-audio.service" "/etc/systemd/system/${AUDIO_SERVICE_NAME}"
    sudo systemctl daemon-reload
    echo "Service file updated."
else
    echo "WARNING: Pi audio service file not found in repo"
fi

# --- Restart both services ---
echo "Restarting camera service..."
sudo systemctl restart "$CAMERA_SERVICE"

echo "Restarting Pi audio service..."
sudo systemctl restart "$AUDIO_SERVICE_NAME"

# --- Verify ---
sleep 2
echo ""
echo "=== Update Complete ==="
echo "  Camera: $(systemctl is-active "$CAMERA_SERVICE" 2>/dev/null || echo 'unknown')"
echo "  Audio:   $(systemctl is-active "$AUDIO_SERVICE_NAME" 2>/dev/null || echo 'unknown')"
