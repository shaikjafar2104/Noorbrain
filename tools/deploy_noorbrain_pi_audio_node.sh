#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 <ssh-user@pi-host> [token-file]" >&2
  echo "Default token file: \${XDG_CONFIG_HOME:-\$HOME/.config}/noorbrain/pi-audio-node.token" >&2
}

if [[ $# -lt 1 || $# -gt 2 ]]; then
  usage
  exit 2
fi

target=$1
config_root=${XDG_CONFIG_HOME:-"$HOME/.config"}
token_file=${2:-"$config_root/noorbrain/pi-audio-node.token"}
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repository_root=$(cd -- "$script_dir/.." && pwd)
node_source="$repository_root/tools/noorbrain_pi_audio_node.py"
service_template="$repository_root/deploy/pi-audio/noorbrain-pi-audio.service.in"

if [[ ! -f "$node_source" || ! -f "$service_template" ]]; then
  echo "Pi audio deployment assets are missing." >&2
  exit 1
fi

if [[ ! -f "$token_file" ]]; then
  mkdir -p -- "$(dirname -- "$token_file")"
  umask 077
  python3 -c 'import secrets; print(secrets.token_urlsafe(48))' >"$token_file"
fi
chmod 600 -- "$token_file"

token_length=$(tr -d '\r\n' <"$token_file" | wc -c)
if (( token_length < 32 )); then
  echo "Node token must contain at least 32 characters." >&2
  exit 1
fi

ssh_options=(-F /dev/null -o ConnectTimeout=8)
remote_directory=".noorbrain-pi-audio-deploy"

ssh "${ssh_options[@]}" "$target" "mkdir -p -- '$remote_directory' && chmod 700 -- '$remote_directory'"
scp "${ssh_options[@]}" "$node_source" "$target:$remote_directory/noorbrain_pi_audio_node.py"
scp "${ssh_options[@]}" "$service_template" "$target:$remote_directory/noorbrain-pi-audio.service.in"
scp "${ssh_options[@]}" "$token_file" "$target:$remote_directory/node.token"

ssh "${ssh_options[@]}" "$target" 'bash -s' -- "$remote_directory" <<'REMOTE_INSTALL'
set -euo pipefail
remote_directory=$1
trap 'rm -rf -- "$HOME/$remote_directory"' EXIT

project="$HOME/Projects/NoorCameraNode"
python="$project/venv/bin/python"
source_file="$HOME/$remote_directory/noorbrain_pi_audio_node.py"
service_template="$HOME/$remote_directory/noorbrain-pi-audio.service.in"
token_file="$HOME/$remote_directory/node.token"

if [[ ! -x "$python" ]]; then
  echo "Required Pi venv Python not found: $python" >&2
  exit 1
fi
"$python" -c 'import fastapi, uvicorn'

install -d -m 755 -- "$project"
install -m 644 -- "$source_file" "$project/noorbrain_pi_audio_node.py"

service_file=$(mktemp)
environment_file=$(mktemp)
trap 'rm -f -- "$service_file" "$environment_file"; rm -rf -- "$HOME/$remote_directory"' EXIT
sed \
  -e "s|@NOORBRAIN_USER@|$(id -un)|g" \
  -e "s|@NOORBRAIN_HOME@|$HOME|g" \
  "$service_template" >"$service_file"

token=$(tr -d '\r\n' <"$token_file")
{
  printf 'NOORBRAIN_NODE_TOKEN=%s\n' "$token"
  printf 'NOORBRAIN_NODE_ID=existing-pi-audio\n'
  printf 'NOORBRAIN_NODE_NAME="NoorBrain Raspberry Pi"\n'
  printf 'NOORBRAIN_NODE_ROOM="Unassigned"\n'
  printf 'NOORBRAIN_NODE_PORT=8010\n'
  printf 'NOORBRAIN_PLAYBACK_DEVICE=plughw:CARD=Headphones,DEV=0\n'
  printf 'NOORBRAIN_CAPTURE_DEVICE=plughw:CARD=Device,DEV=0\n'
} >"$environment_file"
chmod 600 -- "$environment_file"

sudo install -d -m 750 /etc/noorbrain
sudo install -m 600 -- "$environment_file" /etc/noorbrain/pi-audio-node.env
sudo install -m 644 -- "$service_file" /etc/systemd/system/noorbrain-pi-audio.service
sudo systemctl daemon-reload
sudo systemctl enable --now noorbrain-pi-audio.service
sudo systemctl restart noorbrain-pi-audio.service
sleep 2
"$python" -c 'import json, urllib.request; print(json.load(urllib.request.urlopen("http://127.0.0.1:8010/health", timeout=5)))'
REMOTE_INSTALL

echo "Pi audio node deployed. The shared token remains only in: $token_file"
echo "Configure node existing-pi-audio with that token in NoorBrain Rooms & Speakers."
