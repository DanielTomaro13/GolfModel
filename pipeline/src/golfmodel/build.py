"""Main pipeline: build every JSON feed the static site consumes.

  feed      -> field -> calibrate (win market -> ratings) -> Monte Carlo sim -> board
  scrapers  -> book odds + Dabble Pick'em
  join      -> model price vs book price -> value edges

Writes to web/public/data/:
  tournament-latest.json  full model board (win/topX/cut/totals) + meta
  compare-latest.json     model price vs every book, per player+market
  value-latest.json       ranked model edges vs book consensus
  pickem-latest.json      Dabble Pick'em lines judged by the model
  players-latest.json     per-player detail (board + round profile)
  meta-latest.json        event/schedule freshness for the header
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np

from . import feed
from .config import WEB_DATA_DIR, ensure_dirs
from .engine import calibrate, markets
from .engine.field import build_field
from .engine.market import to_price
from .engine.simulate import simulate
from .scrape import fetch_all_odds, normalize_name

# Finishing markets the model prices directly off the board.
BOARD_MARKETS = ("win", "top_5", "top_10", "top_20", "top_30", "make_cut")

# Minimum model probability for a market to be eligible for the value board — the
# Monte Carlo tail is noisy on no-hopers, and books quote placeholder prices on
# them, so a raw edge there is meaningless. Tuned to where the model is reliable.
VALUE_PROB_FLOOR = {
    "win": 0.01, "top_5": 0.03, "top_10": 0.05,
    "top_20": 0.10, "top_30": 0.15, "make_cut": 0.35,
}
VALUE_MIN_EDGE = 0.03
VALUE_MAX_EDGE = 0.60
VALUE_MIN_BOOKS = 3


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write(name: str, payload: dict, *, keep_if_empty_key: str | None = None) -> None:
    """Write a feed. If ``keep_if_empty_key`` names a list field that is empty and
    an existing file already has data, preserve the old file instead — this stops a
    geo-blocked AU scrape (empty Dabble Pick'em from a US runner) from clobbering a
    good feed produced by a local run.
    """
    path = WEB_DATA_DIR / name
    if keep_if_empty_key and not payload.get(keep_if_empty_key) and path.exists():
        try:
            existing = json.loads(path.read_text())
            if existing.get(keep_if_empty_key):
                print(f"  kept {name} (new {keep_if_empty_key} empty; preserved {len(existing[keep_if_empty_key])} rows)")
                return
        except (json.JSONDecodeError, OSError):
            pass
    path.write_text(json.dumps(payload, separators=(",", ":")))
    print(f"  wrote {path.relative_to(WEB_DATA_DIR.parents[2])} ({path.stat().st_size//1024} KB)")


def _board_prob(res, i: int, market: str) -> float:
    return {
        "win": res.win, "top_5": res.top5, "top_10": res.top10,
        "top_20": res.top20, "top_30": res.top30, "make_cut": res.make_cut,
    }[market][i]


def run(num_sims: int = 20_000, force_refresh: bool = False) -> None:
    ensure_dirs()
    cache_kw = {"force": force_refresh}
    print("1/5 data feed…")
    field_probs = feed.field_probs(**cache_kw)
    rank = feed.rankings(**cache_kw)
    outs = feed.outright_odds(**cache_kw)
    sched = feed.schedule(**cache_kw)

    print("2/5 calibrate + simulate…")
    field = build_field(field_probs, rank, outs)
    calibrate.calibrate(field)
    res = simulate(field, num_sims=num_sims)

    print("3/5 scrape book odds + Dabble Pick'em…")
    odds_rows, pickem_lines = fetch_all_odds(**cache_kw)

    name_to_id = {normalize_name(p.name): p.pid for p in field.players}
    book_index: dict[tuple[str, str], dict[str, float]] = {}
    for r in odds_rows:
        nkey = normalize_name(r.player)
        book_index.setdefault((nkey, r.market), {})[r.book] = r.price

    generated = _now()
    event_name = field.event_name

    print("4/5 build board / compare / value…")
    board, compare, value = [], [], []
    for i, p in enumerate(field.players):
        nkey = normalize_name(p.name)
        board.append({
            "pid": p.pid, "player": p.name, "country": p.country,
            "amateur": p.amateur, "rating": round(p.rating, 2),
            "win": round(float(res.win[i]), 5),
            "top_5": round(float(res.top5[i]), 4),
            "top_10": round(float(res.top10[i]), 4),
            "top_20": round(float(res.top20[i]), 4),
            "top_30": round(float(res.top30[i]), 4),
            "make_cut": round(float(res.make_cut[i]), 4),
            "total_mean": round(float(res.total_mean[i]), 1),
            "total_sd": round(float(res.total_sd[i]), 1),
        })

        for market in BOARD_MARKETS:
            prob = float(_board_prob(res, i, market))
            if prob <= 0:
                continue
            model_price = to_price(prob)
            books = book_index.get((nkey, market), {})
            compare.append({
                "pid": p.pid, "player": p.name, "market": market,
                "model_prob": round(prob, 5), "model_price": model_price,
                "books": {b: round(pr, 2) for b, pr in books.items()},
            })
            if prob < VALUE_PROB_FLOOR.get(market, 1.0) or len(books) < VALUE_MIN_BOOKS:
                continue
            consensus_price = float(np.median(sorted(books.values())))
            edge = prob * consensus_price - 1.0
            if not (VALUE_MIN_EDGE <= edge <= VALUE_MAX_EDGE):
                continue
            best_book, best_price = max(books.items(), key=lambda kv: kv[1])
            value.append({
                "pid": p.pid, "player": p.name, "market": market,
                "model_prob": round(prob, 5), "model_price": model_price,
                "consensus_price": round(consensus_price, 2),
                "best_book": best_book, "best_price": round(best_price, 2),
                "edge": round(edge, 4), "n_books": len(books),
            })

    value.sort(key=lambda v: v["edge"], reverse=True)

    print("5/5 judge Pick'em + write feeds…")
    pickem = _judge_pickem(pickem_lines, res, name_to_id)
    players = _player_detail(field, res)
    meta = _meta(event_name, field, res, sched, num_sims, generated)

    _write("tournament-latest.json", {"generated": generated, "event": event_name,
            "source_win": field.source_win, "num_sims": num_sims, "players": board})
    _write("compare-latest.json", {"generated": generated, "event": event_name, "rows": compare}, keep_if_empty_key="rows")
    _write("value-latest.json", {"generated": generated, "event": event_name, "rows": value})
    _write("pickem-latest.json", {"generated": generated, "event": event_name, "lines": pickem}, keep_if_empty_key="lines")
    _write("players-latest.json", {"generated": generated, "event": event_name, "players": players})
    _write("meta-latest.json", meta)
    print(f"Done. {len(field.players)} players, {len(value)} value edges, {len(pickem)} pick'em lines.")


def _judge_pickem(lines, res, name_to_id) -> list[dict]:
    out = []
    market_to_board = {"top_5": res.top5, "top_10": res.top10, "top_20": res.top20, "top_30": res.top30}
    for ln in lines:
        pid = name_to_id.get(normalize_name(ln.player))
        prob = None
        if ln.market in market_to_board and pid is not None:
            i = res.idx(pid)
            if i is not None:
                prob = float(market_to_board[ln.market][i])
        elif ln.market == "round_strokes" and pid is not None and ln.round in (1, 2):
            ou = markets.round_over_under(res, pid, ln.line, kind=f"r{ln.round}")
            prob = ou.get("under")
        rec = {
            "book": ln.book, "player": ln.player, "market": ln.market,
            "line": ln.line, "round": ln.round, "multiplier": ln.multiplier,
            "model_prob": round(prob, 4) if prob is not None else None,
            "matched": pid is not None,
        }
        if prob is not None and ln.multiplier:
            rec["ev"] = round(prob * ln.multiplier - 1.0, 4)
        out.append(rec)
    out.sort(key=lambda r: (r.get("ev") is None, -(r.get("ev") or 0)))
    return out


def _player_detail(field, res) -> list[dict]:
    out = []
    for i, p in enumerate(field.players):
        out.append({
            "pid": p.pid, "player": p.name, "country": p.country, "rating": round(p.rating, 2),
            "win": round(float(res.win[i]), 5), "top_5": round(float(res.top5[i]), 4),
            "top_10": round(float(res.top10[i]), 4), "top_20": round(float(res.top20[i]), 4),
            "make_cut": round(float(res.make_cut[i]), 4),
            "round_mean": [round(float(x), 1) for x in res.round_mean[i]],
            "round_sd": [round(float(x), 1) for x in res.round_sd[i]],
            "total_mean": round(float(res.total_mean[i]), 1),
            "total_sd": round(float(res.total_sd[i]), 1),
            "pos_quantiles": markets.position_quantiles(res, p.pid),
        })
    out.sort(key=lambda r: -r["win"])
    return out


def _meta(event_name, field, res, sched, num_sims, generated) -> dict:
    upcoming = [e for e in sched if e.get("status") != "completed"]
    nxt = upcoming[0] if upcoming else (sched[0] if sched else {})
    return {
        "generated": generated, "event": event_name, "tour": field.tour,
        "num_sims": num_sims, "field_size": len(field.players),
        "source_win": field.source_win, "cut_line": res.cut_line,
        "next_event": {
            "name": nxt.get("event_name"), "course": nxt.get("course"),
            "start_date": nxt.get("start_date"), "location": nxt.get("location"),
        },
        "data_age_days": feed.cache_age_days(),
    }


if __name__ == "__main__":
    import sys
    force = "--force" in sys.argv or "--refresh" in sys.argv
    sims = 20_000
    for a in sys.argv[1:]:
        if a.startswith("--sims="):
            sims = int(a.split("=", 1)[1])
    run(num_sims=sims, force_refresh=force)
