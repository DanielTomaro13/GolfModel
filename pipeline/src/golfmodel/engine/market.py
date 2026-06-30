"""Odds <-> probability helpers and overround removal.

Golf win markets carry a bookmaker margin (overround). We strip it by simple
proportional normalisation so the implied win probabilities sum to 1.
"""
from __future__ import annotations

from collections.abc import Iterable


def implied(odds: float) -> float:
    """Decimal odds -> raw implied probability (still includes margin)."""
    if odds is None or odds <= 1.0:
        return 0.0
    return 1.0 / odds


def to_price(prob: float, *, max_price: float = 1001.0) -> float:
    """Probability -> fair decimal price (no margin)."""
    if prob <= 0:
        return max_price
    if prob >= 1:
        return 1.01
    return round(min(max_price, 1.0 / prob), 2)


def devig_proportional(odds: Iterable[float]) -> list[float]:
    """Remove overround by proportional (linear) normalisation.

    Returns probabilities that sum to 1. This matches the golf engine's
    convention of simple proportional scaling rather than a power-law devig.
    """
    raw = [implied(o) for o in odds]
    total = sum(raw)
    if total <= 0:
        return [0.0 for _ in raw]
    return [r / total for r in raw]


def consensus_win_prob(book_odds_by_player: dict[int, list[float]]) -> dict[int, float]:
    """Build a devigged consensus win probability per player from many books.

    ``book_odds_by_player`` maps a player id -> list of decimal win odds across
    books. We take each player's median odds, then devig across the field.
    """
    import statistics

    med: dict[int, float] = {}
    for pid, odds_list in book_odds_by_player.items():
        clean = [o for o in odds_list if o and o > 1.0]
        if clean:
            med[pid] = statistics.median(clean)

    if not med:
        return {}
    pids = list(med)
    probs = devig_proportional([med[p] for p in pids])
    return dict(zip(pids, probs))
