#!/usr/bin/env bash
DESKTOP="$HOME/Desktop"
mkdir -p "$DESKTOP"
cat > "$DESKTOP/NoorBrain.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=NoorBrain AI Studio
Comment=Start NoorBrain and open its dashboard
Exec=$HOME/Projects/NoorBrain/start_noorbrain.sh
Icon=applications-multimedia
Terminal=true
Categories=Utility;
EOF
chmod +x "$DESKTOP/NoorBrain.desktop"
echo "Desktop launcher installed."
