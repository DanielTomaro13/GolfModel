"""Flatten the feed's outright odds (many books) into OddsRow records.

The data feed returns, per market, every player's decimal price at each book. We
pull the finishing markets (win / top-5/10/20 / make-cut) and emit one OddsRow per
(book, market, player). This is the robust multi-book spine for the Compare and
Value pages; it is cached weekly like all feed data.
"""
from __future__ import annotations

from .. import feed
from .common import OddsRow

# Feed market id -> our canonical key.
FEED_MARKETS = {
    "win": "win", "top_5": "top_5", "top_10": "top_10", "top_20": "top_20", "mc": "make_cut",
}


def fetch_book_odds(tour: str = "pga", **cache_kw) -> list[OddsRow]:
    rows: list[OddsRow] = []
    for feed_market, key in FEED_MARKETS.items():
        try:
            payload = feed.outright_odds(tour=tour, market=feed_market, **cache_kw)
        except Exception:
            continue
        event = payload.get("event_name", "")
        for r in payload.get("odds", []):
            pid, name = r.get("pid"), r.get("name", "")
            for book, price in r.get("prices", {}).items():
                rows.append(OddsRow(book=book, event=event, market=key,
                                    player=name, price=float(price), pid=pid))
    return rows
