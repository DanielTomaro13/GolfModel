"""Price individual markets off a completed Monte Carlo simulation.

The board markets (win / top-X / make-cut) are already empirical frequencies on
``SimResult``. This module adds the markets that need a line or a pairing:
  - player round / tournament total over-under at a given line
  - player-vs-player matchups (tournament and single-round)
All return a fair probability; convert to a price with ``market.to_price``.
"""
from __future__ import annotations

import numpy as np

from .simulate import SimResult


def _scores_for(res: SimResult, kind: str) -> np.ndarray:
    if kind == "r1":
        return res.r1_scores
    if kind == "r2":
        return res.r2_scores
    raise ValueError(f"per-round O/U only stored for r1/r2, got {kind!r}")


def round_over_under(res: SimResult, pid: int, line: float, kind: str = "r1") -> dict:
    """P(player's round score over / under a half-line)."""
    i = res.idx(pid)
    if i is None:
        return {}
    s = _scores_for(res, kind)[:, i]
    over = float(np.mean(s > line))
    under = float(np.mean(s < line))
    return {"over": over, "under": under, "push": 1.0 - over - under}


def total_over_under(res: SimResult, pid: int, line: float) -> dict:
    """P(player's 72-hole total over/under), conditional on making the cut.

    Books void total-strokes bets on missed-cut players, so we condition on the
    made-cut sims via the stored total mean/sd (normal approximation).
    """
    i = res.idx(pid)
    if i is None:
        return {}
    mu, sd = float(res.total_mean[i]), float(res.total_sd[i])
    if sd <= 0:
        return {}
    from math import erf, sqrt

    z = (line - mu) / (sd * sqrt(2.0))
    under = 0.5 * (1.0 + erf(z))
    return {"over": 1.0 - under, "under": under, "mean": mu, "sd": sd}


def matchup(res: SimResult, pid_a: int, pid_b: int) -> dict:
    """P(A finishes ahead of B); ties split. Tournament-long, using positions."""
    a, b = res.idx(pid_a), res.idx(pid_b)
    if a is None or b is None:
        return {}
    pa = res.positions[:, a].astype(np.int32)
    pb = res.positions[:, b].astype(np.int32)
    a_ahead = float(np.mean(pa < pb))
    tie = float(np.mean(pa == pb))
    return {
        "a": a_ahead + tie / 2.0,
        "b": (1.0 - a_ahead - tie) + tie / 2.0,
        "tie": tie,
    }


def round_matchup(res: SimResult, pid_a: int, pid_b: int, kind: str = "r1") -> dict:
    """P(A scores lower than B) in a single round; ties split."""
    a, b = res.idx(pid_a), res.idx(pid_b)
    if a is None or b is None:
        return {}
    s = _scores_for(res, kind)
    sa, sb = s[:, a].astype(np.int32), s[:, b].astype(np.int32)
    a_low = float(np.mean(sa < sb))
    tie = float(np.mean(sa == sb))
    return {"a": a_low + tie / 2.0, "b": (1.0 - a_low - tie) + tie / 2.0, "tie": tie}


def position_quantiles(res: SimResult, pid: int, qs=(0.1, 0.25, 0.5, 0.75, 0.9)) -> dict:
    """Finishing-position quantiles, for the player page Pick'em judgement."""
    i = res.idx(pid)
    if i is None:
        return {}
    p = res.positions[:, i]
    return {str(q): int(np.quantile(p, q)) for q in qs}
