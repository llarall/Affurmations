"""
Text-to-speech microservice — REQ/REP over ZeroMQ.
Synthesizes spoken audio via pyttsx3 and returns a path to a WAV file.
"""

from __future__ import annotations

import sys
import tempfile
import uuid
from pathlib import Path

import pyttsx3
import zmq

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.config import TTS_BIND
from shared.messages import decode, encode

OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def synthesize_to_file(text: str, out_path: Path | None = None) -> Path:
    text = (text or "").strip()
    if not text:
        raise ValueError("empty text")
    path = out_path or OUTPUT_DIR / f"affurmation_{uuid.uuid4().hex[:12]}.wav"
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = pyttsx3.init()
    try:
        engine.save_to_file(text, str(path))
        engine.runAndWait()
    finally:
        try:
            engine.stop()
        except Exception:
            pass
    if not path.is_file():
        raise RuntimeError("TTS did not create output file")
    return path


def main() -> None:
    ctx = zmq.Context()
    sock = ctx.socket(zmq.REP)
    sock.bind(TTS_BIND)
    print(f"TTS service listening on {TTS_BIND}", flush=True)
    try:
        while True:
            raw = sock.recv()
            try:
                req = decode(raw)
            except Exception as e:
                sock.send(encode({"ok": False, "error": f"bad json: {e}"}))
                continue
            op = req.get("op")
            if op != "synthesize":
                sock.send(encode({"ok": False, "error": f"unknown op: {op!r}"}))
                continue
            text = req.get("text", "")
            out = req.get("out_path")
            out_path = Path(out) if isinstance(out, str) and out.strip() else None
            try:
                path = synthesize_to_file(str(text), out_path)
            except Exception as e:
                sock.send(encode({"ok": False, "error": str(e)}))
                continue
            sock.send(encode({"ok": True, "path": str(path)}))
    finally:
        sock.close(0)
        ctx.term()


if __name__ == "__main__":
    main()
