"""Assemble the tournament field from the normalised data feed.

Merges three feed sources into one player list:
  - field probabilities  -> baseline finishing-position numbers
  - rankings             -> skill estimate (strokes-gained units)
  - outright odds        -> book win odds (consensus target for calibration)

The calibration target is the devigged book-consensus win probability where a
player is priced; otherwise it falls back to the feed's own win baseline.
"""
from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any

from . import market


@dataclass
class Player:
    pid: int
    name: str
    country: str = ""
    amateur: bool = False
    skill: float | None = None          # strokes-gained skill (higher = better)
    ref_win: float = 0.0                # baseline finishing fractions 0..1
    ref_top5: float = 0.0
    ref_top10: float = 0.0
    ref_top20: float = 0.0
    ref_make_cut: float = 0.0
    book_win_prob: float | None = None  # devigged consensus, fraction 0..1
    target_win_prob: float = 0.0        # what calibration aims to reproduce
    rating: float = 0.0                 # strokes-per-round (filled by calibration)
    meta: dict[str, Any] = dc_field(default_factory=dict)


@dataclass
class Field:
    event_name: str
    tour: str
    players: list[Player]
    source_win: str  # "book_consensus" | "model" | "mixed"


def build_field(
    field_probs: dict[str, Any],
    rankings: dict[int, float],
    outright_odds: dict[str, Any] | None,
    tour: str = "pga",
) -> Field:
    event_name = (field_probs or {}).get("event_name", "Unknown Event")
    baseline = (field_probs or {}).get("players", [])

    book_odds: dict[int, list[float]] = {}
    for row in (outright_odds or {}).get("odds", []):
        pid = row.get("pid")
        prices = [p for p in row.get("prices", {}).values() if p and p > 1.0]
        if pid is not None and prices:
            book_odds[pid] = prices

    consensus = market.consensus_win_prob(book_odds)

    players: list[Player] = []
    used_book = used_model = 0
    for row in baseline:
        pid = row.get("pid")
        if pid is None:
            continue
        bw = consensus.get(pid)
        model_win = float(row.get("win", 0.0))
        if bw is not None and bw > 0:
            target = bw
            used_book += 1
        else:
            target = model_win
            used_model += 1
        players.append(
            Player(
                pid=pid, name=row.get("name", str(pid)),
                country=row.get("country", ""), amateur=bool(row.get("amateur")),
                skill=rankings.get(pid),
                ref_win=model_win, ref_top5=float(row.get("top5", 0.0)),
                ref_top10=float(row.get("top10", 0.0)), ref_top20=float(row.get("top20", 0.0)),
                ref_make_cut=float(row.get("make_cut", 0.0)),
                book_win_prob=bw, target_win_prob=target,
            )
        )

    tot = sum(p.target_win_prob for p in players)
    if tot > 0:
        for p in players:
            p.target_win_prob /= tot

    source = "mixed" if used_book and used_model else ("book_consensus" if used_book else "model")
    return Field(event_name=event_name, tour=tour, players=players, source_win=source)
