#!/usr/bin/env python3
"""Compatibility entry point for the retired dual-audio installer.

The active server implementation and Pi protocol live in the repository. This
installer deliberately does not regenerate the historical unauthenticated node.
"""

from __future__ import annotations

import py_compile
from pathlib import Path


def project_root() -> Path:
    candidate = Path(__file__).resolve().parents[2]
    if (candidate / "main.py").is_file():
        return candidate
    raise SystemExit("NoorBrain repository root was not found")


def main() -> int:
    root = project_root()
    required = [
        root / "services" / "playback_router" / "router.py",
        root / "services" / "playback_router" / "routes.py",
        root / "services" / "playback_router" / "tts_audio.py",
        root / "services" / "dual_audio_v15" / "routes.py",
        root / "tools" / "noorbrain_pi_audio_node.py",
        root / "tools" / "deploy_noorbrain_pi_audio_node.sh",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit("Missing authoritative Pi audio files: " + ", ".join(missing))
    for path in required:
        if path.suffix == ".py":
            py_compile.compile(str(path), doraise=True)
    print("AUTHORITATIVE PI AUDIO CONTRACT READY")
    print("Deploy with: ./tools/deploy_noorbrain_pi_audio_node.sh <ssh-user@pi-host>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
