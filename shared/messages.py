"""JSON helpers for ZeroMQ payloads."""

import json
from typing import Any


def encode(obj: dict[str, Any]) -> bytes:
    return json.dumps(obj, ensure_ascii=False).encode("utf-8")


def decode(data: bytes) -> dict[str, Any]:
    return json.loads(data.decode("utf-8"))
