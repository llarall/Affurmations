"""
Banner microservice — REQ/REP over ZeroMQ.
Returns random ASCII art banners titled Affurmations.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

import zmq

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.config import BANNER_BIND
from shared.messages import decode, encode

# Each banner includes the title Affurmations prominently (ASCII only).
BANNERS: list[str] = [
    r"""
    ___   __ __  _____  _   _  ___  _____  _____  __  __  _____  _____  _____  ___  _____
   /   \ |  |  ||     || | | ||   ||     ||     ||  ||  ||     ||   __||     ||   ||_   _|
  |     ||  |  ||  |  || | | ||   ||  |  ||   --||  ||  || |__/||   __||   --||   |  | |
  |  O  ||  |  ||  |  || |_| ||   ||  |  ||   --||  ||  ||  |  ||   __||   --||   |  | |
  |     ||  :  ||  |  ||     ||   ||  |  ||   __||  ||  ||  |  ||   __||   __||   |  | |
   \___/  \___/ |_____| \___/ |___||_____||_____||__||__||_____||_____||_____||___|  |_|

              *  gentle words for you and your pet  *

                              |\__/,|   (`
                            _.|o o  |_   )
                          -(((---(((--------   purr-spective matters.
""",
    r"""
+------------------------------------------------------------------+
|                         Affurmations                             |
|                  gentle words for you & your pet                 |
+------------------------------------------------------------------+

       /\     /\
      /  \~~~/  \
     (    @ @    )
      \   .^.   /
       `-------'     ~~ soft thoughts, steady hearts ~~
""",
    r"""
       *  .  *  Affurmations  *  .  *
    .    *    _____________________    *    .
  *    .      |  /\_/\   purrrrr   |      .    *
    .     *   | ( o.o )             |   *     .
      *       |  > ^ <   welcome   |       *
    .    .    |_____________________|    .    .

""",
    r"""
        __^__                                      __^__
       ( ___ )-----------------------------------( ___ )
        |   |         Affurmations               |   |
        |___|    gentle light for you & your pet  |___|
       (_____)-----------------------------------(_____)
              \   /\   /\
               ) (  ) (  )
              (__/    \__)
""",
    r"""
  /////////////     Affurmations     \\\\\\\\\\\\\\\
 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   (\__/)
   (o  o)   your care is louder than worry
   (>^^<)
""",
    r"""
  _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____ _____
 |     |     |     |     |     |     |     |     |     |     |     |     |
 |  A  |  f  |  f  |  u  |  r  |  m  |  a  |  t  |  i  |  o  |  n  |  s  |
 |_____|_____|_____|_____|_____|_____|_____|_____|_____|_____|_____|_____|

                    * Affurmations — for your pet *
""",
]


def pick_banner() -> tuple[int, str]:
    idx = random.randrange(len(BANNERS))
    text = BANNERS[idx].strip("\n")
    return idx, text


def main() -> None:
    ctx = zmq.Context()
    sock = ctx.socket(zmq.REP)
    sock.bind(BANNER_BIND)
    print(f"Banner service listening on {BANNER_BIND}", flush=True)
    try:
        while True:
            raw = sock.recv()
            try:
                req = decode(raw)
            except Exception as e:
                sock.send(encode({"ok": False, "error": f"bad json: {e}"}))
                continue
            op = req.get("op")
            if op != "banner":
                sock.send(encode({"ok": False, "error": f"unknown op: {op!r}"}))
                continue
            variant_idx, banner = pick_banner()
            sock.send(encode({"ok": True, "banner": banner, "variant": variant_idx}))
    finally:
        sock.close(0)
        ctx.term()


if __name__ == "__main__":
    main()
