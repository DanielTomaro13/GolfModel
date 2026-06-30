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
    odds_rows, pickem_lines, specials = fetch_all_odds(**cache_kw)

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

    print("5/5 judge Pick'em + price matchups/specials + write feeds…")
    pickem = _judge_pickem(pickem_lines, res, name_to_id)
    extras = _price_specials(specials, res, name_to_id)
    players = _player_detail(field, res)
    meta = _meta(event_name, field, res, sched, num_sims, generated)
    print(f"  extras: {len(extras['matchups'])} H2H, {len(extras['three_balls'])} 3-balls, "
          f"{len(extras['leaders'])} leaders, {len(extras['groups'])} groups")

    _write("tournament-latest.json", {"generated": generated, "event": event_name,
            "source_win": field.source_win, "num_sims": num_sims, "players": board})
    _write("compare-latest.json", {"generated": generated, "event": event_name, "rows": compare}, keep_if_empty_key="rows")
    _write("value-latest.json", {"generated": generated, "event": event_name, "rows": value})
    _write("pickem-latest.json", {"generated": generated, "event": event_name, "lines": pickem}, keep_if_empty_key="lines")
    _write("players-latest.json", {"generated": generated, "event": event_name, "players": players})
    _write("extras-latest.json", {"generated": generated, "event": event_name, **extras},
           keep_if_empty_key="matchups")
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
        elif ln.market == "round_strokes" and pid is not None and ln.round in (1, 2, 3, 4):
            ou = markets.round_over_under(res, pid, ln.line, rnd=ln.round)
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


# Hygiene for the relational markets: ignore placeholder prices and noisy tails so
# the "best EV" ranking surfaces real edges, not a 501.0 longshot.
SPECIAL_MAX_PRICE = {"three_ball": 26.0, "leader": 81.0, "group": 19.0}
SPECIAL_FLOOR = {"three_ball": 0.05, "leader": 0.015, "group": 0.05}
EV_CAP = 1.0


def _leg_ev(prob: float, price: float | None, kind: str) -> float | None:
    """EV of backing a selection, or None if the price/prob isn't a real market."""
    if not price or price <= 1.0 or price > SPECIAL_MAX_PRICE[kind]:
        return None
    if prob < SPECIAL_FLOOR[kind]:
        return None
    return min(EV_CAP, prob * price - 1.0)


def _devig(prices: list[float]) -> list[float]:
    inv = [1.0 / p for p in prices if p and p > 1.0]
    s = sum(inv)
    return [(1.0 / p) / s if (p and p > 1.0 and s > 0) else 0.0 for p in prices]


def _price_specials(specials: dict, res, name_to_id) -> dict:
    """Price Dabble's relational markets against the simulation; attach EV.

    EV of backing a selection at decimal price P is model_prob * P - 1.
    """
    def pid(name):
        return name_to_id.get(normalize_name(name))

    matchups = []
    for m in specials.get("matchups", []):
        a, b = pid(m["a"]), pid(m["b"])
        if a is None or b is None:
            continue
        mp = markets.matchup(res, a, b, rnd=m.get("round"))
        if not mp:
            continue
        row = {"a": m["a"], "b": m["b"], "round": m.get("round"),
               "model_a": round(mp["a"], 4), "model_b": round(mp["b"], 4), "model_tie": round(mp["tie"], 4),
               "price_a": m.get("price_a"), "price_b": m.get("price_b"), "price_draw": m.get("price_draw")}
        ev_a = mp["a"] * m["price_a"] - 1 if m.get("price_a") else None
        ev_b = mp["b"] * m["price_b"] - 1 if m.get("price_b") else None
        row["ev_a"] = round(ev_a, 4) if ev_a is not None else None
        row["ev_b"] = round(ev_b, 4) if ev_b is not None else None
        row["best_ev"] = round(max([e for e in (ev_a, ev_b) if e is not None], default=-1), 4)
        matchups.append(row)
    matchups.sort(key=lambda r: r["best_ev"], reverse=True)

    three_balls = []
    for t in specials.get("three_balls", []):
        names = [p["player"] for p in t["players"]]
        pids = [pid(n) for n in names]
        if any(x is None for x in pids):
            continue
        tb = markets.three_ball(res, pids, rnd=t.get("round"))
        if not tb:
            continue
        legs, best = [], None
        for p, x in zip(t["players"], pids):
            prob = tb.get(str(x), 0.0)
            ev = _leg_ev(prob, p.get("price"), "three_ball")
            if ev is not None:
                best = ev if best is None else max(best, ev)
            legs.append({"player": p["player"], "price": p["price"],
                         "model_prob": round(prob, 4), "ev": round(ev, 4) if ev is not None else None})
        three_balls.append({"round": t.get("round"), "players": legs,
                            "best_ev": round(best, 4) if best is not None else None})
    three_balls.sort(key=lambda r: (r["best_ev"] is None, -(r["best_ev"] or -1)))

    leaders = []
    for lp in specials.get("leaders", []):
        rnd = lp["round"]
        legs, best = [], None
        for p in lp["players"]:
            x = pid(p["player"])
            if x is None:
                continue
            prob = markets.round_leader(res, x, rnd) or 0.0
            ev = _leg_ev(prob, p.get("price"), "leader")
            if ev is not None:
                best = ev if best is None else max(best, ev)
            legs.append({"player": p["player"], "price": p["price"],
                         "model_prob": round(prob, 4), "ev": round(ev, 4) if ev is not None else None})
        legs.sort(key=lambda r: -r["model_prob"])  # show by model favourite
        if legs:
            leaders.append({"round": rnd, "players": legs[:20],
                            "best_ev": round(best, 4) if best is not None else None})
    leaders.sort(key=lambda r: (r["best_ev"] is None, -(r["best_ev"] or -1)))

    groups = []
    for g in specials.get("groups", []):
        members = [(p["player"], pid(p["player"]), p["price"]) for p in g["players"]]
        members = [(n, x, pr) for n, x, pr in members if x is not None]
        if len(members) < 2:
            continue
        gw = markets.group_winner(res, [x for _, x, _ in members])
        legs, best = [], None
        for n, x, pr in members:
            prob = gw.get(str(x), 0.0)
            ev = _leg_ev(prob, pr, "group")
            if ev is not None:
                best = ev if best is None else max(best, ev)
            legs.append({"player": n, "price": pr, "model_prob": round(prob, 4),
                         "ev": round(ev, 4) if ev is not None else None})
        legs.sort(key=lambda r: -r["model_prob"])
        groups.append({"group": g["group"], "players": legs,
                       "best_ev": round(best, 4) if best is not None else None})
    groups.sort(key=lambda r: (r["best_ev"] is None, -(r["best_ev"] or -1)))

    return {"matchups": matchups, "three_balls": three_balls, "leaders": leaders, "groups": groups}


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
