#!/usr/bin/env python3
"""
Start banner, affirmation, tips, and TTS microservices, then launch the text client.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> None:
    scripts = [
        ROOT / "services" / "banner_service.py",
        ROOT / "services" / "affirmation_service.py",
        ROOT / "services" / "tips_service.py",
        ROOT / "services" / "tts_service.py",
    ]
    procs: list[subprocess.Popen] = []
    try:
        for script in scripts:
            procs.append(
                subprocess.Popen(
                    [sys.executable, str(script)],
                    cwd=str(ROOT),
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
                )
            )
        time.sleep(1.0)
        r = subprocess.run([sys.executable, str(ROOT / "affurmations.py")], cwd=str(ROOT))
        raise SystemExit(r.returncode)
    finally:
        for p in procs:
            p.terminate()
            try:
                p.wait(timeout=3)
            except subprocess.TimeoutExpired:
                p.kill()


if __name__ == "__main__":
    main()
