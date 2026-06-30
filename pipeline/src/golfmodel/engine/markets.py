"""Price individual markets off a completed Monte Carlo simulation.

The board markets (win / top-X / make-cut) are already empirical frequencies on
``SimResult``. This module prices the markets that need a line, a pairing, or a
group, all read off the stored per-sim round scores and finishing positions:
  - round / tournament total over-under
  - head-to-head and 3-ball matchups (any round, or whole tournament)
  - round leader (lowest cumulative score through round N — e.g. first-round leader)
  - group winner (best finisher among a named set of players)
All return fair probabilities; convert to a price with ``market.to_price``.
"""
from __future__ import annotations

import numpy as np

from .simulate import SimResult


def _round_scores(res: SimResult, rnd: int) -> np.ndarray:
    """[sims, n] strokes for a 1-based round number."""
    return res.round_scores[:, :, rnd - 1]


def _cumulative(res: SimResult, rnd: int) -> np.ndarray:
    """[sims, n] cumulative strokes through round `rnd` (1-based)."""
    return res.round_scores[:, :, :rnd].sum(axis=2)


# ── Totals over/under ─────────────────────────────────────────────────────────

def round_over_under(res: SimResult, pid: int, line: float, rnd: int = 1) -> dict:
    """P(player's single-round score over / under a line)."""
    i = res.idx(pid)
    if i is None:
        return {}
    s = _round_scores(res, rnd)[:, i]
    over = float(np.mean(s > line))
    under = float(np.mean(s < line))
    return {"over": over, "under": under, "push": max(0.0, 1.0 - over - under)}


def total_over_under(res: SimResult, pid: int, line: float) -> dict:
    """P(player's 72-hole total over/under), conditional on making the cut."""
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


# ── Matchups ──────────────────────────────────────────────────────────────────

def matchup(res: SimResult, pid_a: int, pid_b: int, rnd: int | None = None) -> dict:
    """Head-to-head. Tournament-long (rnd=None, by finishing position) or a single
    round (by that round's score). Lower is better; ties reported explicitly."""
    a, b = res.idx(pid_a), res.idx(pid_b)
    if a is None or b is None:
        return {}
    if rnd is None:
        va, vb = res.positions[:, a].astype(np.int32), res.positions[:, b].astype(np.int32)
    else:
        s = _round_scores(res, rnd)
        va, vb = s[:, a].astype(np.int32), s[:, b].astype(np.int32)
    a_better = float(np.mean(va < vb))
    tie = float(np.mean(va == vb))
    return {"a": a_better, "b": 1.0 - a_better - tie, "tie": tie}


def three_ball(res: SimResult, pids: list[int], rnd: int | None = None) -> dict:
    """3-way: P(each player has the lowest score). Single round (rnd) or 72-hole
    total (rnd=None). Ties split evenly among those tied for lowest."""
    idx = [res.idx(p) for p in pids]
    if any(i is None for i in idx):
        return {}
    if rnd is None:
        vals = _cumulative(res, 4)[:, idx].astype(np.int32)
    else:
        vals = _round_scores(res, rnd)[:, idx].astype(np.int32)
    mn = vals.min(axis=1, keepdims=True)
    is_min = (vals == mn).astype(float)
    share = is_min / is_min.sum(axis=1, keepdims=True)  # split ties
    probs = share.mean(axis=0)
    return {str(pids[k]): float(probs[k]) for k in range(len(pids))}


# ── Leaders & groups ──────────────────────────────────────────────────────────

def round_leader(res: SimResult, pid: int, rnd: int = 1) -> float | None:
    """P(player has the lowest cumulative score through round `rnd`; ties shared).
    rnd=1 is the first-round leader market."""
    i = res.idx(pid)
    if i is None:
        return None
    cum = _cumulative(res, rnd)
    mn = cum.min(axis=1, keepdims=True)
    is_min = (cum == mn).astype(float)
    share = is_min / is_min.sum(axis=1, keepdims=True)
    return float(share[:, i].mean())


def group_winner(res: SimResult, pids: list[int]) -> dict:
    """P(each player is the best finisher within the named group; ties split).
    Group members come straight from the market's selections — no nationality
    lookup needed."""
    idx = [res.idx(p) for p in pids]
    keep = [(p, i) for p, i in zip(pids, idx) if i is not None]
    if not keep:
        return {}
    cols = [i for _, i in keep]
    pos = res.positions[:, cols].astype(np.int32)
    mn = pos.min(axis=1, keepdims=True)
    is_min = (pos == mn).astype(float)
    share = is_min / is_min.sum(axis=1, keepdims=True)
    probs = share.mean(axis=0)
    return {str(keep[k][0]): float(probs[k]) for k in range(len(keep))}


def position_quantiles(res: SimResult, pid: int, qs=(0.1, 0.25, 0.5, 0.75, 0.9)) -> dict:
    """Finishing-position quantiles, for the player page."""
    i = res.idx(pid)
    if i is None:
        return {}
    p = res.positions[:, i]
    return {str(q): int(np.quantile(p, q)) for q in qs}
