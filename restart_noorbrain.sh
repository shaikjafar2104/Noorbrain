#!/usr/bin/env bash
ROOT="$HOME/Projects/NoorBrain"
"$ROOT/stop_noorbrain.sh"
sleep 2
"$ROOT/start_noorbrain.sh"
