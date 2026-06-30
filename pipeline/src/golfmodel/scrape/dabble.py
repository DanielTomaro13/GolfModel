"""Dabble golf scraper (no auth).

Dabble carries a full golf book across two kinds of competition:
  - the per-tournament comp (e.g. "John Deere Classic") with genuine fixed odds:
      tournament_winner, top_5/10/20, tournament_match_bet (H2H), round_3_ball,
      round_leader (lead after round N), tournament_group_winner ("Top European")
  - a separate "PGA Pick'em" comp with flat-multiplier finish props (pickem_top_N)
    and, once rounds are live, round-strokes props.

fetch_dabble() returns a dict of:
  odds         OddsRow list (winner + top-N fixed odds, book="dabble")
  pickem       PickemLine list (flat-multiplier finish / round-strokes)
  matchups     [{event, round, a, b, price_a, price_b, price_draw}]  (round=None = tournament)
  three_balls  [{event, round, players:[{player, price}] }]
  leaders      [{event, round, players:[{player, price}] }]
  groups       [{event, group, players:[{player, price}] }]

Endpoint flow:
  /competitions
  /frontend-api/competitions/{id}/sport-fixtures
  /frontend-api/sport-fixtures/details/{fixtureId}  -> markets / prices / selections
"""
from __future__ import annotations

import os
import re

from .common import OddsRow, PickemLine, get_json, sleep

DAB = "https://api.dabble.com.au"
GOLF_SPORT_ID = "02ffc0b5-aafa-4438-8571-f9a465ad4f10"

HDR = {
    "accept": "application/json",
    "user-agent": os.environ.get(
        "DABBLE_UA", "Dabble/1000041710 CFNetwork/3826.600.41.2.1 Darwin/24.6.0"
    ),
    "x-device-id": os.environ.get("DABBLE_DEVICE_ID", "00000000-0000-0000-0000-000000000000"),
}

PICKEM_FINISH = {"pickem_top_5": "top_5", "pickem_top_10": "top_10",
                 "pickem_top_20": "top_20", "pickem_top_30": "top_30"}
FINISH_FIXED = {"top_5": "top_5", "top_10": "top_10", "top_20": "top_20", "top_30": "top_30"}
_ROUND_NUM = re.compile(r"round\s*(\d+)", re.I)
_PICKEM_ROUND_RT = re.compile(r"pickem_round_(\d+)_strokes", re.I)


def _round_of(*texts: str) -> int | None:
    for t in texts:
        m = _ROUND_NUM.search(t or "")
        if m:
            return int(m.group(1))
    return None


def _golf_competitions() -> list[dict]:
    comps = get_json(f"{DAB}/competitions", HDR)
    items = comps.get("data", comps) if isinstance(comps, dict) else comps
    out = []
    for c in items or []:
        if isinstance(c, dict) and c.get("sportId") == GOLF_SPORT_ID:
            name = str(c.get("name", "")).lower()
            if "sgm" in name or "q-school" in name:
                continue
            out.append(c)
    return out


def _fixtures(comp_id: str) -> list[dict]:
    url = f"{DAB}/frontend-api/competitions/{comp_id}/sport-fixtures?includeInPlay=true&exclude%5B%5D=none"
    fx = get_json(url, HDR)
    return (fx.get("data", fx) if isinstance(fx, dict) else fx) or []


def _num(x) -> float | None:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def fetch_dabble() -> dict:
    out = {"odds": [], "pickem": [], "matchups": [], "three_balls": [], "leaders": [], "groups": []}
    seen_pickem: set = set()

    for comp in _golf_competitions():
        for fixture in _fixtures(comp["id"]):
            fid = fixture.get("id")
            if not fid:
                continue
            detail = get_json(f"{DAB}/frontend-api/sport-fixtures/details/{fid}", HDR)
            sfd = (detail or {}).get("sportFixtureDetail") or {}
            if not sfd.get("markets"):
                continue
            event = sfd.get("name", fixture.get("name", ""))

            sel_name = {s["id"]: s.get("name", "") for s in sfd.get("selections", [])}
            outs: dict[str, list[tuple[str, float]]] = {}
            for p in sfd.get("prices", []):
                outs.setdefault(p.get("marketId"), []).append(
                    (sel_name.get(p.get("selectionId"), ""), p.get("price")))

            for m in sfd.get("markets", []):
                rt = (m.get("resultingType") or "").lower()
                mname = (m.get("name") or "").strip()
                rows = [(nm, _num(pr)) for nm, pr in outs.get(m.get("id"), []) if _num(pr)]
                _route(out, rt, mname, event, rows, seen_pickem)
            sleep(120)
    return out


def _route(out, rt, mname, event, rows, seen_pickem):
    # ── fixed-odds finishing markets → OddsRow (book=dabble) ────────────────
    if rt == "tournament_winner":
        for nm, pr in rows:
            out["odds"].append(OddsRow(book="dabble", event=event, market="win", player=nm, price=pr))
        return
    if rt in FINISH_FIXED:
        for nm, pr in rows:
            out["odds"].append(OddsRow(book="dabble", event=event, market=FINISH_FIXED[rt], player=nm, price=pr))
        return

    # ── head-to-head (A / B / Draw) ─────────────────────────────────────────
    if rt == "tournament_match_bet":
        players = [(nm, pr) for nm, pr in rows if nm.lower() != "draw"]
        draw = next((pr for nm, pr in rows if nm.lower() == "draw"), None)
        if len(players) == 2:
            (a, pa), (b, pb) = players
            out["matchups"].append({"event": event, "round": _round_of(mname),
                                    "a": a, "b": b, "price_a": pa, "price_b": pb, "price_draw": draw})
        return

    # ── 3-ball (single round) ───────────────────────────────────────────────
    if rt == "round_3_ball":
        if len(rows) >= 2:
            out["three_balls"].append({"event": event, "round": _round_of(mname),
                                       "players": [{"player": nm, "price": pr} for nm, pr in rows]})
        return

    # ── round leader (lead after round N) ───────────────────────────────────
    if rt == "round_leader":
        rnd = _round_of(mname)
        if rnd:
            out["leaders"].append({"event": event, "round": rnd,
                                   "players": [{"player": nm, "price": pr} for nm, pr in rows]})
        return

    # ── group winner ("Top European" etc.) ──────────────────────────────────
    if rt == "tournament_group_winner":
        out["groups"].append({"event": event, "group": mname,
                              "players": [{"player": nm, "price": pr} for nm, pr in rows]})
        return

    # ── Pick'em finish props (flat multiplier) ──────────────────────────────
    if rt in PICKEM_FINISH:
        market = PICKEM_FINISH[rt]
        player = re.split(r"\s+Top\s+\d+", mname)[0].strip()
        mult = next((pr for nm, pr in rows if "over" in nm.lower()), None) or (rows[0][1] if rows else None)
        key = (player, market)
        if player and key not in seen_pickem:
            seen_pickem.add(key)
            out["pickem"].append(PickemLine(book="dabble", event=event, market=market,
                                            player=player, line=0.5, multiplier=mult))
        return

    # ── Pick'em round strokes ───────────────────────────────────────────────
    rm = _PICKEM_ROUND_RT.search(rt)
    if rm and rows:
        rnd = int(rm.group(1))
        num = re.search(r"(\d+(?:\.\d+)?)\s*$", mname)
        player = re.split(r"\s+Round\s*\d+", mname)[0].strip()
        mult = next((pr for nm, pr in rows if "over" in nm.lower()), None) or rows[0][1]
        if player and num:
            key = (player, "round_strokes", rnd)
            if key not in seen_pickem:
                seen_pickem.add(key)
                out["pickem"].append(PickemLine(book="dabble", event=event, market="round_strokes",
                                                player=player, line=float(num.group(1)),
                                                multiplier=mult, round=rnd))
