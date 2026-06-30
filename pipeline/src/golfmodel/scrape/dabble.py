"""Dabble golf scraper (no auth).

Dabble runs a PGA Pick'em product: per-player "Top N" finish props and, once
rounds are underway, round-strokes props. These are flat-multiplier Pick'em lines
(Over side only), not two-way fixed odds, so they go to the Pick'em feed where the
model judges each line against its simulated probability.

Endpoint flow (same as the AFL scraper):
  /competitions
  /frontend-api/competitions/{id}/sport-fixtures
  /frontend-api/sport-fixtures/details/{fixtureId}   -> markets / prices / selections
"""
from __future__ import annotations

import os
import re

from .common import PickemLine, get_json, sleep

DAB = "https://api.dabble.com.au"
GOLF_SPORT_ID = "02ffc0b5-aafa-4438-8571-f9a465ad4f10"

HDR = {
    "accept": "application/json",
    "user-agent": os.environ.get(
        "DABBLE_UA", "Dabble/1000041710 CFNetwork/3826.600.41.2.1 Darwin/24.6.0"
    ),
    "x-device-id": os.environ.get("DABBLE_DEVICE_ID", "00000000-0000-0000-0000-000000000000"),
}

# resultingType -> canonical finish market.
PICKEM_FINISH = {
    "pickem_top_5": "top_5",
    "pickem_top_10": "top_10",
    "pickem_top_20": "top_20",
    "pickem_top_30": "top_30",
}
# Round-strokes pick'em (appears once a round is live). Market name carries the line.
PICKEM_ROUND_RT = re.compile(r"pickem_round_(\d+)_strokes", re.I)
ROUND_NAME = re.compile(r"Round\s*(\d+).*?Strokes", re.I)


def _golf_competitions() -> list[dict]:
    comps = get_json(f"{DAB}/competitions", HDR)
    items = comps.get("data", comps) if isinstance(comps, dict) else comps
    out = []
    for c in items or []:
        if not isinstance(c, dict):
            continue
        if c.get("sportId") == GOLF_SPORT_ID:
            name = str(c.get("name", "")).lower()
            if "sgm" in name or "futures" in name:
                continue
            out.append(c)
    return out


def _fixtures(comp_id: str) -> list[dict]:
    url = f"{DAB}/frontend-api/competitions/{comp_id}/sport-fixtures?includeInPlay=false&exclude%5B%5D=none"
    fx = get_json(url, HDR)
    return (fx.get("data", fx) if isinstance(fx, dict) else fx) or []


def fetch_dabble() -> list[PickemLine]:
    lines: list[PickemLine] = []
    seen: set[tuple] = set()
    for comp in _golf_competitions():
        for fixture in _fixtures(comp["id"]):
            fid = fixture.get("id")
            if not fid:
                continue
            detail = get_json(f"{DAB}/frontend-api/sport-fixtures/details/{fid}", HDR)
            sfd = (detail or {}).get("sportFixtureDetail") or (detail or {}).get("data", {}).get(
                "sportFixtureDetail"
            ) or {}
            event = sfd.get("name", fixture.get("name", ""))

            sel_name = {s["id"]: s.get("name", "") for s in sfd.get("selections", [])}
            price_by_mkt: dict[str, list[tuple[str, float]]] = {}
            for p in sfd.get("prices", []):
                price_by_mkt.setdefault(p.get("marketId"), []).append(
                    (sel_name.get(p.get("selectionId"), ""), p.get("price"))
                )

            for m in sfd.get("markets", []):
                rt = (m.get("resultingType") or "").lower()
                mname = (m.get("name") or "").strip()
                outs = price_by_mkt.get(m.get("id"), [])
                # Over-side multiplier for this player's prop.
                mult = next((pr for snm, pr in outs if pr and "over" in snm.lower()), None)
                if mult is None:
                    mult = next((pr for _, pr in outs if pr), None)

                if rt in PICKEM_FINISH:
                    market = PICKEM_FINISH[rt]
                    # market name: "<Player> Top N 0.5" -> player is everything before "Top".
                    player = re.split(r"\s+Top\s+\d+", mname)[0].strip()
                    key = (player, market)
                    if player and key not in seen:
                        seen.add(key)
                        lines.append(PickemLine(book="dabble", event=event, market=market,
                                                player=player, line=0.5, multiplier=_num(mult)))
                    continue

                rm = PICKEM_ROUND_RT.search(rt) or ROUND_NAME.search(mname)
                if rm and "strokes" in (rt + mname).lower():
                    rnd = int(rm.group(1))
                    # line is the strokes number in the market name.
                    num = re.search(r"(\d+(?:\.\d+)?)\s*(?:strokes)?\s*$", mname)
                    player = re.split(r"\s+Round\s*\d+", mname)[0].strip()
                    if player and num:
                        key = (player, "round_strokes", rnd)
                        if key not in seen:
                            seen.add(key)
                            lines.append(PickemLine(book="dabble", event=event,
                                                    market="round_strokes", player=player,
                                                    line=float(num.group(1)),
                                                    multiplier=_num(mult), round=rnd))
            sleep(150)
    return lines


def _num(x) -> float | None:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None
