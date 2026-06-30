"""Australian-book golf outright scrapers: Sportsbet, TAB, Ladbrokes.

Golf books expose a tournament as a set of *outright* markets (Tournament Winner,
Top 5/10/20 Finish, To Make the Cut) whose selections are players. Unlike the
AFL player-prop scrapers, there is no per-match nav: each book identifies the live
tournament by its own event/competition id, which drifts week to week.

PointsBet golf is already covered by the book feed, so it is not repeated
here. These three are the AU books the feed does not include. Supply the current
event id via env (SB_GOLF_EVENT_ID / TAB_GOLF_COMP / LAD_GOLF_HASH+slug); without
it the scraper logs and returns [] rather than guessing. Market parsing is wired so
that the moment a valid id is present, prices flow.
"""
from __future__ import annotations

import os
import re

from .common import OddsRow, get_json, sleep

# Map a book's outright-market display name to our canonical key.
_WIN = re.compile(r"^(tournament\s+)?(winner|outright|to win)", re.I)
_TOPN = re.compile(r"top\s*(\d+)", re.I)
_CUT_MAKE = re.compile(r"make.*cut|to make the cut", re.I)
_CUT_MISS = re.compile(r"miss.*cut|to miss the cut", re.I)


def market_key(name: str) -> str | None:
    n = (name or "").strip()
    if _WIN.search(n):
        return "win"
    if _CUT_MISS.search(n):
        return "miss_cut"
    if _CUT_MAKE.search(n):
        return "make_cut"
    m = _TOPN.search(n)
    if m and int(m.group(1)) in (5, 10, 20, 30):
        return f"top_{m.group(1)}"
    return None


# ───────────────────────────── Sportsbet ─────────────────────────────
SB = "https://www.sportsbet.com.au/apigw/sportsbook-sports/Sportsbook/Sports"
SB_HDR = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}


def fetch_sportsbet() -> list[OddsRow]:
    event_id = os.environ.get("SB_GOLF_EVENT_ID", "").strip()
    if not event_id:
        print("  [sportsbet] no SB_GOLF_EVENT_ID set — skipping (set to the live tournament event id)")
        return []
    markets = get_json(f"{SB}/Events/{event_id}/Markets", SB_HDR)
    if not isinstance(markets, list):
        print("  [sportsbet] markets fetch failed")
        return []
    rows: list[OddsRow] = []
    event_name = os.environ.get("SB_GOLF_EVENT_NAME", "")
    for m in markets:
        key = market_key(m.get("name", ""))
        if not key:
            continue
        for s in m.get("selections", []):
            price = (s.get("price") or {}).get("winPrice")
            if price and s.get("name"):
                rows.append(OddsRow(book="sportsbet", event=event_name, market=key,
                                    player=s["name"].strip(), price=float(price)))
    print(f"  [sportsbet] {len(rows)} rows")
    return rows


# ───────────────────────────── TAB ─────────────────────────────
TAB_BASE = "https://api.beta.tab.com.au/v1/tab-info-service"
TAB_TOKEN_URL = "https://api.beta.tab.com.au/oauth/token"


def _tab_token() -> str | None:
    cid, sec = os.environ.get("TAB_CLIENT_ID", "").strip(), os.environ.get("TAB_CLIENT_SECRET", "").strip()
    if cid and sec:
        import requests
        try:
            r = requests.post(TAB_TOKEN_URL, data={"grant_type": "client_credentials",
                              "client_id": cid, "client_secret": sec}, timeout=20)
            if r.status_code == 200:
                return r.json().get("access_token")
        except Exception:
            pass
    return os.environ.get("TAB_ACCESS_TOKEN", "").strip() or None


def fetch_tab() -> list[OddsRow]:
    tok = _tab_token()
    if not tok:
        print("  [tab] no TAB creds — skipping")
        return []
    comp = os.environ.get("TAB_GOLF_COMP", "").strip()  # e.g. the tournament competition path
    if not comp:
        print("  [tab] no TAB_GOLF_COMP set — skipping")
        return []
    hdr = {"Authorization": f"Bearer {tok}", "Accept": "application/json", "User-Agent": "Mozilla/5.0"}
    d = get_json(f"{TAB_BASE}/sports/Golf/competitions/{comp}?jurisdiction=NSW&homeState=NSW", hdr)
    if not d:
        print("  [tab] competition fetch failed")
        return []
    rows: list[OddsRow] = []
    event_name = d.get("name", "")
    # TAB nests markets under matches or directly under the competition.
    containers = d.get("matches") or [d]
    for c in containers:
        for mk in c.get("markets", []):
            key = market_key(mk.get("name") or mk.get("betOption") or "")
            if not key:
                continue
            for p in mk.get("propositions", []):
                price = p.get("returnWin")
                if price and p.get("name"):
                    rows.append(OddsRow(book="tab", event=c.get("name", event_name), market=key,
                                        player=p["name"].strip(), price=float(price)))
    print(f"  [tab] {len(rows)} rows")
    return rows


# ───────────────────────────── Ladbrokes ─────────────────────────────
LAD = "https://api.ladbrokes.com.au"
LAD_HDR = {"User-Agent": "Mozilla/5.0", "Origin": "https://www.ladbrokes.com.au",
           "Referer": "https://www.ladbrokes.com.au/", "Content-Type": "application/json"}


def _lad_decimal(p: dict) -> float | None:
    o = (p or {}).get("odds") or {}
    if o.get("decimal"):
        return round(float(o["decimal"]), 2)
    if o.get("numerator") and o.get("denominator"):
        return round(o["numerator"] / o["denominator"] + 1, 2)
    return None


def fetch_ladbrokes() -> list[OddsRow]:
    event_id = os.environ.get("LAD_GOLF_EVENT_ID", "").strip()
    if not event_id:
        print("  [ladbrokes] no LAD_GOLF_EVENT_ID set — skipping")
        return []
    card = get_json(f"{LAD}/v2/sport/event-card?id={event_id}", LAD_HDR)
    if not card:
        print("  [ladbrokes] event-card fetch failed")
        return []
    entrants = card.get("entrants", {})
    prices = card.get("prices", {})
    event_name = (card.get("event") or {}).get("name", os.environ.get("LAD_GOLF_EVENT_NAME", ""))

    def price_of(ent_id: str) -> float | None:
        for k, v in prices.items():
            if k.startswith(ent_id + ":"):
                return _lad_decimal(v)
        return None

    rows: list[OddsRow] = []
    for market in card.get("markets", {}).values():
        key = market_key(market.get("name", ""))
        if not key:
            continue
        for e in entrants.values():
            if e.get("market_id") != market.get("id"):
                continue
            price = price_of(e.get("id", ""))
            if price:
                rows.append(OddsRow(book="ladbrokes", event=event_name, market=key,
                                    player=(e.get("name") or "").strip(), price=price))
    print(f"  [ladbrokes] {len(rows)} rows")
    return rows
