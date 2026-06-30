"""Bookmaker odds scrapers.

fetch_all_odds() returns:
  - odds rows: per (book, market, player) decimal prices for finishing markets,
    from the multi-book feed plus the AU books (Sportsbet/TAB/Ladbrokes).
  - pickem lines: Dabble PGA Pick'em finish + round-strokes lines.
"""
from __future__ import annotations

from .au_books import fetch_ladbrokes, fetch_sportsbet, fetch_tab
from .common import OddsRow, PickemLine, normalize_name
from .dabble import fetch_dabble
from .feed_books import fetch_book_odds

__all__ = [
    "OddsRow", "PickemLine", "normalize_name", "fetch_all_odds",
    "fetch_book_odds", "fetch_dabble",
]


def fetch_all_odds(tour: str = "pga", **cache_kw) -> tuple[list[OddsRow], list[PickemLine]]:
    rows: list[OddsRow] = []
    # Reliable multi-book spine (cached feed).
    try:
        feed_rows = fetch_book_odds(tour=tour, **cache_kw)
        print(f"  [book-odds] {len(feed_rows)} rows")
        rows += feed_rows
    except Exception as e:  # never let one source kill the run
        print(f"  [book-odds] failed: {e}")

    # AU books not in the feed (best-effort; need a live event id).
    for fn in (fetch_sportsbet, fetch_tab, fetch_ladbrokes):
        try:
            rows += fn()
        except Exception as e:
            print(f"  [{fn.__name__}] failed: {e}")

    pickem: list[PickemLine] = []
    try:
        pickem = fetch_dabble()
        print(f"  [dabble] {len(pickem)} pick'em lines")
    except Exception as e:
        print(f"  [dabble] failed: {e}")

    return rows, pickem
