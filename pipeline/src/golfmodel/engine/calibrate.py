"""Calibrate per-player stroke ratings to reproduce the win market.

The whole engine turns on one number per player: a rating in *strokes per round*
where lower is better. Calibration chooses each rating so that the modelled win
probabilities match the target win market (devigged book consensus, or the feed's
win baseline as a fallback).

We use a fast analytic win-probability evaluator built from order statistics over
a discrete grid of 4-round totals, and nudge each player's rating until the
analytic win probabilities match target. The grid PMF is properly normalised, so
the survival products are genuine tail probabilities.
"""
from __future__ import annotations

import numpy as np

from .field import Field, Player

# Scoring model constants (strokes).
BASELINE = 70.1          # nominal par-relative anchor
FIELD_MEAN_ANCHOR = 71.0  # realistic tournament scoring average (per round)
PER_ROUND_SD = 2.9       # round-to-round scoring dispersion
N_ROUNDS = 4
TOTAL_SD = PER_ROUND_SD * np.sqrt(N_ROUNDS)  # ~5.8 over 72 holes

RATING_MIN = FIELD_MEAN_ANCHOR - 9.0
RATING_MAX = FIELD_MEAN_ANCHOR + 12.0
TARGET_FLOOR = 1e-7


def _seed_rating(p: Player) -> float:
    """Initial rating: anchor off the skill estimate when present, else mid-field."""
    if p.skill is not None:
        # skill is strokes-gained per round (higher = better). Centre the field
        # near FIELD_MEAN_ANCHOR; better skill -> lower (better) rating.
        return float(np.clip(FIELD_MEAN_ANCHOR + (1.0 - p.skill), RATING_MIN, RATING_MAX))
    return FIELD_MEAN_ANCHOR + 2.0


def _score_grid(ratings: np.ndarray) -> np.ndarray:
    lo = int(np.floor(N_ROUNDS * ratings.min() - 5 * TOTAL_SD))
    hi = int(np.ceil(N_ROUNDS * ratings.max() + 5 * TOTAL_SD))
    return np.arange(lo, hi + 1, dtype=float)


def _normal_pmf(grid: np.ndarray, means: np.ndarray, sd: float) -> np.ndarray:
    """Return [n_players, n_grid] normalised PMF of 4-round totals."""
    z = (grid[None, :] - means[:, None]) / sd
    dens = np.exp(-0.5 * z * z)
    dens /= dens.sum(axis=1, keepdims=True)  # proper PMF over the grid
    return dens


def analytic_win_probs(ratings: np.ndarray) -> np.ndarray:
    """P(each player posts the strictly-lowest 4-round total), order statistics.

    win_i = sum_score pmf_i(score) * prod_{j!=i} P(total_j > score)
    """
    grid = _score_grid(ratings)
    means = N_ROUNDS * ratings
    pmf = _normal_pmf(grid, means, TOTAL_SD)               # [n, g]
    # Survival at each grid point: P(total_j > score). Score sits on the grid, so
    # "strictly greater" excludes the point mass at `score` itself.
    cdf_incl = np.cumsum(pmf, axis=1)                       # P(total <= score)
    surv = np.clip(1.0 - cdf_incl, 1e-12, 1.0)             # P(total > score)
    log_surv = np.log(surv)
    total_log_surv = log_surv.sum(axis=0, keepdims=True)   # [1, g]
    # prod_{j!=i} surv_j = exp(total - log_surv_i)
    others = np.exp(total_log_surv - log_surv)             # [n, g]
    win = (pmf * others).sum(axis=1)                       # [n]
    s = win.sum()
    return win / s if s > 0 else win


def calibrate(field: Field, *, iters: int = 80, verbose: bool = False) -> np.ndarray:
    """Solve ratings so analytic win probs match each player's target.

    Returns the rating vector and writes it back onto each Player.
    """
    players = field.players
    ratings = np.array([_seed_rating(p) for p in players], dtype=float)
    target = np.array([max(p.target_win_prob, TARGET_FLOOR) for p in players])
    target /= target.sum()

    lr0 = 6.0
    for it in range(iters):
        win = np.maximum(analytic_win_probs(ratings), 1e-12)
        # log-space error; positive when we under-predict and must improve player.
        err = np.log(target) - np.log(win)
        lr = lr0 * (1.0 - it / iters) ** 1.5 + 0.15
        ratings = ratings - lr * err
        # Win prob is invariant to a global rating shift, so pin the absolute
        # level by re-centring the field mean. This removes the free translation
        # mode (which otherwise drifts everyone to the clamp) and keeps round
        # scores realistic for over/under markets.
        ratings += FIELD_MEAN_ANCHOR - ratings.mean()
        ratings = np.clip(ratings, RATING_MIN, RATING_MAX)
        if verbose and (it % 20 == 0 or it == iters - 1):
            mae = float(np.mean(np.abs(win - target)))
            print(f"  iter {it:3d} lr={lr:5.2f} win-MAE={mae:.5f}")

    for p, r in zip(players, ratings):
        p.rating = float(r)
    return ratings
