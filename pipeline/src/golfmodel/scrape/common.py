"""Shared scraping utilities: HTTP, the odds row type, and name normalisation."""
from __future__ import annotations

import time
import unicodedata
from dataclasses import asdict, dataclass
from typing import Any

import requests

# Canonical market keys used across every book and the model.
MARKETS = ("win", "top_5", "top_10", "top_20", "top_30", "make_cut", "miss_cut")


@dataclass
class OddsRow:
    book: str
    event: str
    market: str          # one of MARKETS
    player: str          # book's player name, as shown
    price: float         # decimal odds
    pid: int | None = None
    line: float | None = None
    start_iso: str | None = None

    def dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class PickemLine:
    book: str
    event: str
    market: str          # e.g. "top_5", "top_10", "top_20", "round_strokes"
    player: str
    line: float
    multiplier: float | None = None  # flat Pick'em payout multiplier (Over side)
    round: int | None = None

    def dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


def get_json(
    url: str,
    headers: dict[str, str] | None = None,
    *,
    tries: int = 4,
    timeout: int = 30,
    params: dict[str, Any] | None = None,
) -> Any | None:
    """GET with retries; returns parsed JSON or None (never raises)."""
    for attempt in range(tries):
        try:
            r = requests.get(url, headers=headers or {}, params=params, timeout=timeout)
            if r.status_code == 200:
                return r.json()
        except (requests.RequestException, ValueError):
            pass
        time.sleep(0.6 * (attempt + 1))
    return None


def sleep(ms: int) -> None:
    time.sleep(ms / 1000.0)


def normalize_name(name: str) -> str:
    """Fold a player name to a comparable key regardless of order/diacritics.

    Handles both "Griffin, Ben" (last-first) and "Ben Griffin" (book) forms, strips
    accents, suffixes, and punctuation. Returns a sorted-token key so the two
    orderings collide.
    """
    if not name:
        return ""
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace(".", " ").replace("-", " ").replace("'", "")
    if "," in s:
        last, _, first = s.partition(",")
        s = f"{first} {last}"
    drop = {"jr", "sr", "ii", "iii", "iv", "v"}
    tokens = [t for t in s.split() if t and t not in drop]
    return " ".join(sorted(tokens))
