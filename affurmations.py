#!/usr/bin/env python3
"""
Affurmations — text client for affirmation, TTS, banner, and care-tips microservices (ZeroMQ).
"""

from __future__ import annotations

import platform
import subprocess
import sys
from pathlib import Path

import zmq

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.config import AFFIRMATION_BIND, BANNER_BIND, REQUEST_TIMEOUT_MS, TIPS_BIND, TTS_BIND
from shared.messages import decode, encode

FALLBACK_BANNER = """
  Affurmations
  ------------
  (Banner service unavailable — start services/banner_service.py or run_affurmations.py)
"""


def play_audio_file(path: Path) -> None:
    path = path.resolve()
    if not path.is_file():
        print("Audio file not found.")
        return
    system = platform.system()
    if system == "Windows":
        import winsound

        winsound.PlaySound(str(path), winsound.SND_FILENAME)
    elif system == "Darwin":
        subprocess.run(["afplay", str(path)], check=False)
    else:
        for cmd in (["aplay", str(path)], ["paplay", str(path)]):
            try:
                subprocess.run(cmd, check=False, timeout=600)
                return
            except FileNotFoundError:
                continue
        print("Could not find a player (try installing aplay or paplay). Path saved:", path)


class AffurmationsClient:
    def __init__(self) -> None:
        self._ctx = zmq.Context()
        self.affirmations: list[str] = []
        self.last_pet_name: str | None = None
        self.last_count: int = 1
        self.last_audio_path: Path | None = None

    def close(self) -> None:
        self._ctx.term()

    def _req(self, url: str, payload: dict) -> dict:
        sock = self._ctx.socket(zmq.REQ)
        sock.setsockopt(zmq.RCVTIMEO, REQUEST_TIMEOUT_MS)
        sock.setsockopt(zmq.LINGER, 0)
        try:
            sock.connect(url)
            sock.send(encode(payload))
            return decode(sock.recv())
        except zmq.Again:
            return {"ok": False, "error": "timeout — is the service running?"}
        except zmq.ZMQError as e:
            return {"ok": False, "error": str(e)}
        finally:
            sock.close(0)

    def generate_remote(self, pet_name: str | None, count: int) -> tuple[bool, str]:
        self.last_count = max(1, count)
        self.last_pet_name = pet_name
        res = self._req(
            AFFIRMATION_BIND,
            {"op": "generate", "pet_name": pet_name, "count": self.last_count},
        )
        if not res.get("ok"):
            return False, res.get("error", "unknown error")
        lines = res.get("affirmations") or []
        if not lines:
            return False, "no affirmations returned"
        self.affirmations = lines
        return True, ""

    def synthesize_remote(self, text: str, out_path: Path | None = None) -> tuple[bool, str, Path | None]:
        payload: dict = {"op": "synthesize", "text": text}
        if out_path is not None:
            payload["out_path"] = str(out_path)
        res = self._req(TTS_BIND, payload)
        if not res.get("ok"):
            return False, res.get("error", "unknown error"), None
        p = res.get("path")
        if not p:
            return False, "no path in response", None
        path = Path(p)
        self.last_audio_path = path
        return True, "", path

    def fetch_banner(self) -> str:
        res = self._req(BANNER_BIND, {"op": "banner"})
        if not res.get("ok"):
            return FALLBACK_BANNER.strip("\n")
        b = res.get("banner")
        if not isinstance(b, str) or not b.strip():
            return FALLBACK_BANNER.strip("\n")
        return b.strip("\n")

    def tips_remote(self, pet_name: str | None, count: int) -> tuple[bool, str, list[str]]:
        res = self._req(
            TIPS_BIND,
            {"op": "tips", "pet_name": pet_name, "count": max(1, count)},
        )
        if not res.get("ok"):
            return False, res.get("error", "unknown error"), []
        tips = res.get("tips") or []
        if not tips:
            return False, "no tips returned", []
        return True, "", tips


def prompt_pet_name() -> str | None:
    raw = input("Pet's name (press Enter to skip — we'll use a gentle generic phrase): ").strip()
    return raw if raw else None


def pick_affirmation_index(client: AffurmationsClient) -> int | None:
    if not client.affirmations:
        print("Generate an affurmation first.")
        return None
    if len(client.affirmations) == 1:
        return 0
    for i, line in enumerate(client.affirmations, 1):
        print(f"  [{i}] {line}")
    s = input(f"Choose 1–{len(client.affirmations)} (Enter for 1): ").strip()
    if not s:
        return 0
    try:
        n = int(s)
    except ValueError:
        print("Invalid number.")
        return None
    if 1 <= n <= len(client.affirmations):
        return n - 1
    print("Out of range.")
    return None


def menu() -> None:
    client = AffurmationsClient()
    try:
        print(client.fetch_banner())
        print()
        while True:
            print(
                """
--- Main menu ---
  1) Generate a basic affurmation (no name needed)
  2) Generate with your pet's name
  3) Generate several at once (pick your favorite)
  4) Hear an affurmation (text-to-speech + play)
  5) Save affurmation text to a file
  6) Save spoken affurmation as an audio file
  7) Regenerate (new messages, same settings as last time)
  8) Show current affurmations
  9) Gentle care tips (practical reminders for supporting your pet)
  0) Quit
"""
            )
            choice = input("Choose: ").strip()

            if choice == "0":
                print("Take gentle care of yourself and your pet. Goodbye.")
                break

            if choice == "1":
                ok, err = client.generate_remote(None, 1)
                if ok:
                    print("\n" + client.affirmations[0] + "\n")
                else:
                    print("Could not generate:", err)

            elif choice == "2":
                name = prompt_pet_name()
                ok, err = client.generate_remote(name, 1)
                if ok:
                    print("\n" + client.affirmations[0] + "\n")
                else:
                    print("Could not generate:", err)

            elif choice == "3":
                name = prompt_pet_name()
                s = input("How many affurmations (1–12)? ").strip()
                try:
                    n = int(s)
                except ValueError:
                    print("Please enter a number.")
                    continue
                ok, err = client.generate_remote(name, n)
                if ok:
                    print()
                    for i, line in enumerate(client.affirmations, 1):
                        print(f"  {i}. {line}")
                    print()
                else:
                    print("Could not generate:", err)

            elif choice == "4":
                idx = pick_affirmation_index(client)
                if idx is None:
                    continue
                text = client.affirmations[idx]
                ok, err, path = client.synthesize_remote(text)
                if not ok:
                    print("TTS failed:", err)
                    continue
                print("Playing…")
                play_audio_file(path)

            elif choice == "5":
                idx = pick_affirmation_index(client)
                if idx is None:
                    continue
                default = Path.home() / "affurmation.txt"
                p = input(f"Save to [{default}]: ").strip()
                out = Path(p) if p else default
                try:
                    out.write_text(client.affirmations[idx] + "\n", encoding="utf-8")
                    print("Saved to", out.resolve())
                except OSError as e:
                    print("Could not save:", e)

            elif choice == "6":
                idx = pick_affirmation_index(client)
                if idx is None:
                    continue
                default = ROOT / "output" / "my_affurmation.wav"
                p = input(f"Audio file path [{default}]: ").strip()
                out = Path(p) if p else default
                ok, err, path = client.synthesize_remote(client.affirmations[idx], out_path=out)
                if ok:
                    print("Audio saved to", path.resolve())
                else:
                    print("TTS failed:", err)

            elif choice == "7":
                ok, err = client.generate_remote(client.last_pet_name, client.last_count)
                if ok:
                    print()
                    for i, line in enumerate(client.affirmations, 1):
                        print(f"  {i}. {line}")
                    print()
                else:
                    print("Could not regenerate:", err)

            elif choice == "8":
                if not client.affirmations:
                    print("(none yet)")
                else:
                    for i, line in enumerate(client.affirmations, 1):
                        print(f"  {i}. {line}")

            elif choice == "9":
                name = prompt_pet_name()
                s = input(f"How many tips (1–12)? [1]: ").strip()
                try:
                    n = int(s) if s else 1
                except ValueError:
                    print("Please enter a number.")
                    continue
                ok, err, tips = client.tips_remote(name, n)
                if ok:
                    print("\n  (Tips support your judgment; they are not a substitute for a veterinarian.)\n")
                    for i, line in enumerate(tips, 1):
                        print(f"  {i}. {line}")
                    print()
                else:
                    print("Could not fetch tips:", err)

            else:
                print("Unknown option.")
    finally:
        client.close()


if __name__ == "__main__":
    try:
        menu()
    except KeyboardInterrupt:
        print("\nInterrupted. Bye.")
        sys.exit(0)
