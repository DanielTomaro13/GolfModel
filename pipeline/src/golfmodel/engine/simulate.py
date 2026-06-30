"""Monte Carlo tournament simulator.

Once ratings are calibrated, this plays the event ``num_sims`` times. Each round
is an independent normal draw around a player's rating; the field is ranked, the
halfway cut applied, and finishing positions assigned. Every market probability is
then read off the empirical frequencies of the simulated outcomes.

The simulation is deterministic for a given ``seed`` (reproducible across machines)
and vectorised with numpy, batched to bound memory.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .calibrate import N_ROUNDS, PER_ROUND_SD
from .field import Field

DEFAULT_SIMS = 20_000
DEFAULT_CUT_LINE = 65        # top N (and ties) make the cut
CUT_AFTER_ROUND = 2         # halfway cut
_BIG = 1_000.0              # pushes missed-cut players below all made-cut finishers


@dataclass
class SimResult:
    names: list[str]
    pids: list[int]
    num_sims: int
    cut_line: int
    win: np.ndarray            # [n] playoff-resolved win probability
    top5: np.ndarray
    top10: np.ndarray
    top20: np.ndarray
    top30: np.ndarray
    make_cut: np.ndarray
    round_mean: np.ndarray     # [n, rounds]
    round_sd: np.ndarray       # [n, rounds]
    total_mean: np.ndarray     # [n] 72-hole total, conditional on making cut
    total_sd: np.ndarray       # [n]
    positions: np.ndarray      # [sims, n] int16 final competition rank (ties shared)
    round_scores: np.ndarray   # [sims, n, 4] int16 per-round strokes (all rounds)

    def idx(self, pid: int) -> int | None:
        try:
            return self.pids.index(pid)
        except ValueError:
            return None


def _competition_rank(sort_key: np.ndarray) -> np.ndarray:
    """Per-sim 1-based competition rank (ties share the best rank).

    sort_key: [sims, n]. Returns int positions where tied players get the same
    (minimum) position — i.e. "top X including ties" semantics.
    """
    order = np.argsort(sort_key, axis=1, kind="stable")
    ordered = np.take_along_axis(sort_key, order, axis=1)
    sims, n = sort_key.shape
    # position along the sorted axis: 1 + count of strictly-smaller keys.
    is_new = np.empty_like(ordered, dtype=bool)
    is_new[:, 0] = True
    is_new[:, 1:] = ordered[:, 1:] > ordered[:, :-1]
    sorted_pos = np.cumsum(is_new, axis=1)            # dense rank
    # convert dense rank to competition rank: position = index of first equal +1.
    # Use running max of (index+1) where is_new, broadcast forward.
    idx_plus = np.where(is_new, np.arange(1, n + 1)[None, :], 0)
    comp_sorted = np.maximum.accumulate(idx_plus, axis=1)
    pos = np.empty_like(comp_sorted)
    np.put_along_axis(pos, order, comp_sorted, axis=1)
    return pos.astype(np.int16)


def simulate(
    field: Field,
    *,
    num_sims: int = DEFAULT_SIMS,
    cut_line: int = DEFAULT_CUT_LINE,
    seed: int = 1,
    batch: int = 4_000,
) -> SimResult:
    ratings = np.array([p.rating for p in field.players], dtype=np.float64)
    n = len(ratings)
    rng = np.random.default_rng(seed)

    # Accumulators
    win = np.zeros(n)
    top5 = np.zeros(n); top10 = np.zeros(n); top20 = np.zeros(n); top30 = np.zeros(n)
    made = np.zeros(n)
    round_sum = np.zeros((n, N_ROUNDS)); round_sumsq = np.zeros((n, N_ROUNDS))
    total_sum = np.zeros(n); total_sumsq = np.zeros(n); made_count = np.zeros(n)

    positions_all = np.empty((num_sims, n), dtype=np.int16)
    round_all = np.empty((num_sims, n, N_ROUNDS), dtype=np.int16)

    cut_rank = min(cut_line, n)
    done = 0
    while done < num_sims:
        b = min(batch, num_sims - done)
        # Round scores: [b, n, rounds]
        z = rng.standard_normal((b, n, N_ROUNDS))
        scores = ratings[None, :, None] + PER_ROUND_SD * z
        scores = np.rint(scores)  # whole strokes

        r2_total = scores[:, :, :CUT_AFTER_ROUND].sum(axis=2)   # [b, n]
        full_total = scores.sum(axis=2)                          # [b, n]

        # Cut: top `cut_rank` and ties on the halfway total make it.
        r2_rank = _competition_rank(r2_total)                    # [b, n]
        made_cut = r2_rank <= cut_rank                           # [b, n] bool

        # Finishing sort key: 72-hole total for made cut; pushed below otherwise.
        sort_key = np.where(made_cut, full_total, _BIG + r2_total)
        pos = _competition_rank(sort_key)                        # [b, n]

        # Win with playoff: unique argmin via tiny jitter among lowest totals.
        jitter = rng.uniform(0, 1e-3, size=(b, n))
        win_idx = np.argmin(sort_key + jitter, axis=1)           # [b]
        np.add.at(win, win_idx, 1)

        top5 += (pos <= 5).sum(axis=0)
        top10 += (pos <= 10).sum(axis=0)
        top20 += (pos <= 20).sum(axis=0)
        top30 += (pos <= 30).sum(axis=0)
        made += made_cut.sum(axis=0)

        round_sum += scores.sum(axis=0)                          # [n, rounds]
        round_sumsq += (scores ** 2).sum(axis=0)
        mc = made_cut.astype(float)
        total_sum += (full_total * mc).sum(axis=0)
        total_sumsq += ((full_total ** 2) * mc).sum(axis=0)
        made_count += made_cut.sum(axis=0)

        positions_all[done:done + b] = pos
        round_all[done:done + b] = scores.astype(np.int16)
        done += b

    s = float(num_sims)
    round_mean = round_sum / s
    round_var = np.maximum(round_sumsq / s - round_mean ** 2, 1e-9)
    mc_n = np.maximum(made_count, 1.0)
    total_mean = total_sum / mc_n
    total_var = np.maximum(total_sumsq / mc_n - total_mean ** 2, 1e-9)

    return SimResult(
        names=[p.name for p in field.players],
        pids=[p.pid for p in field.players],
        num_sims=num_sims,
        cut_line=cut_line,
        win=win / s,
        top5=top5 / s, top10=top10 / s, top20=top20 / s, top30=top30 / s,
        make_cut=made / s,
        round_mean=round_mean, round_sd=np.sqrt(round_var),
        total_mean=total_mean, total_sd=np.sqrt(total_var),
        positions=positions_all, round_scores=round_all,
    )
