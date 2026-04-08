"""
Care-tips microservice — REQ/REP over ZeroMQ.
Returns gentle, practical reminders for supporting an unwell pet (not veterinary advice).
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

import zmq

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.config import TIPS_BIND
from shared.messages import decode, encode

DEFAULT_PET_PHRASE = "your pet"

TEMPLATES = [
    "Keep water fresh and nearby so {pet} can sip without working too hard.",
    "Quiet, dim spaces often help {pet} rest — reduce noise and foot traffic for a while.",
    "Track eating, drinking, and bathroom habits in a simple note; it helps your vet see patterns.",
    "Warm (not hot) bedding can ease achy joints; let {pet} choose the spot that feels best.",
    "Offer food in small portions more often if appetite is low; warmth can make food smellier and more tempting.",
    "Avoid sudden diet changes while {pet} is recovering unless your vet suggests a specific plan.",
    "Wash food and water dishes daily; small hygiene wins matter when immunity is stretched.",
    "If {pet} is on medication, use phone alarms so doses stay on schedule.",
    "Gentle grooming — soft brushing or a damp cloth — can be soothing if {pet} tolerates it.",
    "Limit rough play; calm companionship (sitting nearby, slow pets) often comforts more than activity.",
    "When in doubt or if symptoms change, call your vet; you are not bothering them — you are advocating for {pet}.",
    "Take breaks for yourself; a rested caregiver steadies the whole household, {pet} included.",
]

MAX_TIPS = len(TEMPLATES)


def _pet_label(name: str | None) -> str:
    n = (name or "").strip()
    return n if n else DEFAULT_PET_PHRASE


def pick_tips(pet_name: str | None, count: int) -> list[str]:
    k = max(1, min(count, MAX_TIPS))
    choices = random.sample(TEMPLATES, k)
    label = _pet_label(pet_name)
    return [t.format(pet=label) for t in choices]


def main() -> None:
    ctx = zmq.Context()
    sock = ctx.socket(zmq.REP)
    sock.bind(TIPS_BIND)
    print(f"Tips service listening on {TIPS_BIND}", flush=True)
    try:
        while True:
            raw = sock.recv()
            try:
                req = decode(raw)
            except Exception as e:
                sock.send(encode({"ok": False, "error": f"bad json: {e}"}))
                continue
            op = req.get("op")
            if op != "tips":
                sock.send(encode({"ok": False, "error": f"unknown op: {op!r}"}))
                continue
            pet = req.get("pet_name")
            if pet is not None and not isinstance(pet, str):
                sock.send(encode({"ok": False, "error": "pet_name must be a string or omitted"}))
                continue
            try:
                count = int(req.get("count", 1))
            except (TypeError, ValueError):
                sock.send(encode({"ok": False, "error": "count must be a number"}))
                continue
            try:
                tips = pick_tips(pet if isinstance(pet, str) else None, count)
            except Exception as e:
                sock.send(encode({"ok": False, "error": str(e)}))
                continue
            sock.send(encode({"ok": True, "tips": tips}))
    finally:
        sock.close(0)
        ctx.term()


if __name__ == "__main__":
    main()
