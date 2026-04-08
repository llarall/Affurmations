"""
Affirmation microservice — REQ/REP over ZeroMQ.
Generates warm, pet-focused affurmations (affirmations for furry friends).
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

import zmq

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.config import AFFIRMATION_BIND
from shared.messages import decode, encode

DEFAULT_PET_PHRASE = "your beloved companion"

TEMPLATES = [
    "You are doing everything you can for {pet}, and that love matters more than words can say.",
    "Healing takes time. {pet} is lucky to have someone who cares this deeply.",
    "It's okay to feel worried. {pet} feels your steady presence, and that is a kind of medicine too.",
    "Small comforts count: gentle words, soft resting places, and patience. {pet} is held in your care.",
    "You are not alone in this. Many hearts have walked this path with a treasured pet like {pet}.",
    "Rest is part of recovery. Give {pet} quiet moments and trust the process alongside your vet's guidance.",
    "Your devotion to {pet} is a gift. However today looks, that bond is real and beautiful.",
    "One day at a time. You and {pet} are allowed to have hard days and hopeful ones too.",
    "Courage looks like showing up again tomorrow. {pet} has your courage beside them.",
    "Whatever {pet} needs today, you are learning to listen — and that is profound love.",
    "It's brave to hope and brave to rest. {pet} is wrapped in the warmth you offer.",
    "You deserve gentleness too, while you care for {pet}. Your well-being helps you care well.",
]


def _pet_label(name: str | None) -> str:
    n = (name or "").strip()
    return n if n else DEFAULT_PET_PHRASE


def generate(pet_name: str | None, count: int) -> list[str]:
    k = max(1, min(count, len(TEMPLATES)))
    picks = random.sample(TEMPLATES, k)
    label = _pet_label(pet_name)
    return [t.format(pet=label) for t in picks]


def main() -> None:
    ctx = zmq.Context()
    sock = ctx.socket(zmq.REP)
    sock.bind(AFFIRMATION_BIND)
    print(f"Affirmation service listening on {AFFIRMATION_BIND}", flush=True)
    try:
        while True:
            raw = sock.recv()
            try:
                req = decode(raw)
            except Exception as e:
                sock.send(encode({"ok": False, "error": f"bad json: {e}"}))
                continue
            op = req.get("op")
            if op != "generate":
                sock.send(encode({"ok": False, "error": f"unknown op: {op!r}"}))
                continue
            pet = req.get("pet_name")
            if pet is not None and not isinstance(pet, str):
                sock.send(encode({"ok": False, "error": "pet_name must be a string or omitted"}))
                continue
            count = int(req.get("count", 1))
            try:
                lines = generate(pet if isinstance(pet, str) else None, count)
            except Exception as e:
                sock.send(encode({"ok": False, "error": str(e)}))
                continue
            sock.send(encode({"ok": True, "affirmations": lines}))
    finally:
        sock.close(0)
        ctx.term()


if __name__ == "__main__":
    main()
