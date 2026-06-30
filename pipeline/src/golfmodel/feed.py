"""Upstream data feed client with an on-disk weekly cache.

The feed key and base URL come from the environment (never hard-coded), so the
provider is not identifiable from the source. Every endpoint is cached to a
local JSON snapshot under ``pipeline/data/feed/``; we only hit the network when a
snapshot is missing or older than ``max_age_days`` (default 7), or ``force=True``.

The wrapper functions normalise the upstream response into generic records
(``pid``, ``name``, ``skill``, ``win``, ``top5`` …) so nothing downstream carries
the provider's field schema.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from .config import FEED_CACHE, feed_base, feed_key

DEFAULT_MAX_AGE_DAYS = 7
SECONDS_PER_DAY = 86_400

# Bookmakers carried in the outrights payload (used to build a consensus).
_BOOKS = (
    "bet365", "betcris", "betonline", "betmgm", "betway", "bovada", "caesars",
    "draftkings", "fanduel", "pinnacle", "skybet", "pointsbet", "williamhill", "unibet",
)


def _cache_path(name: str) -> Path:
    return FEED_CACHE / f"{name}.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _age_seconds(fetched_at: str) -> float:
    try:
        dt = datetime.strptime(fetched_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return float("inf")
    return (datetime.now(timezone.utc) - dt).total_seconds()


def _read_cache(name: str) -> dict[str, Any] | None:
    path = _cache_path(name)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _write_cache(name: str, payload: Any) -> dict[str, Any]:
    FEED_CACHE.mkdir(parents=True, exist_ok=True)
    wrapped = {"_fetched_at": _now_iso(), "data": payload}
    _cache_path(name).write_text(json.dumps(wrapped, indent=2, sort_keys=True))
    return wrapped


def _http_get(path: str, params: dict[str, str], tries: int = 4) -> Any:
    params = {**params, "file_format": "json", "key": feed_key()}
    url = f"{feed_base()}/{path}"
    last_err: Exception | None = None
    for attempt in range(tries):
        try:
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                return resp.json()
            last_err = RuntimeError(f"HTTP {resp.status_code}")
        except requests.RequestException as exc:
            last_err = exc
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"feed GET {path} failed after {tries} tries: {last_err}")


def _get(name: str, path: str, params: dict[str, str] | None = None, *,
         force: bool = False, max_age_days: float = DEFAULT_MAX_AGE_DAYS) -> Any:
    cached = _read_cache(name)
    if cached is not None and not force:
        if _age_seconds(cached.get("_fetched_at", "")) <= max_age_days * SECONDS_PER_DAY:
            return cached["data"]
    try:
        payload = _http_get(path, params or {})
    except RuntimeError:
        if cached is not None:
            return cached["data"]
        raise
    return _write_cache(name, payload)["data"]


def _f(x: Any) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


# ── Normalised wrappers ────────────────────────────────────────────────────────

def schedule(tour: str = "pga", **kw: Any) -> list[dict[str, Any]]:
    data = _get("schedule", "get-schedule", {"tour": tour}, **kw)
    out = []
    for e in (data.get("schedule", []) if isinstance(data, dict) else []):
        out.append({
            "event_name": e.get("event_name"), "course": e.get("course"),
            "start_date": e.get("start_date"), "location": e.get("location"),
            "status": e.get("status"),
        })
    return out


def rankings(**kw: Any) -> dict[int, float]:
    """Player skill estimate per id (strokes-gained units, higher = better)."""
    data = _get("rankings", "preds/get-dg-rankings", {}, **kw)
    out: dict[int, float] = {}
    for r in (data.get("rankings", []) if isinstance(data, dict) else []):
        pid = r.get("dg_id")
        if pid is not None and r.get("dg_skill_estimate") is not None:
            out[pid] = _f(r.get("dg_skill_estimate"))
    return out


def field_probs(tour: str = "pga", **kw: Any) -> dict[str, Any]:
    """Baseline finishing-position probabilities per player (fractions 0..1)."""
    data = _get("field", "preds/pre-tournament",
                {"tour": tour, "odds_format": "percent"}, **kw)
    players = []
    for r in (data.get("baseline", []) if isinstance(data, dict) else []):
        pid = r.get("dg_id")
        if pid is None:
            continue
        players.append({
            "pid": pid, "name": r.get("player_name", str(pid)),
            "country": r.get("country", ""), "amateur": bool(r.get("am", 0)),
            "win": _f(r.get("win")), "top5": _f(r.get("top_5")),
            "top10": _f(r.get("top_10")), "top20": _f(r.get("top_20")),
            "make_cut": _f(r.get("make_cut")),
        })
    return {"event_name": (data or {}).get("event_name", "Unknown Event"), "players": players}


def outright_odds(tour: str = "pga", market: str = "win", **kw: Any) -> dict[str, Any]:
    """Bookmaker decimal odds for an outright market, keyed by player id."""
    data = _get(f"outrights_{market}", "betting-tools/outrights",
                {"tour": tour, "market": market, "odds_format": "decimal"}, **kw)
    rows = []
    for r in (data.get("odds", []) if isinstance(data, dict) else []):
        pid = r.get("dg_id")
        if pid is None:
            continue
        prices = {b: r[b] for b in _BOOKS if isinstance(r.get(b), (int, float)) and r[b] > 1.0}
        rows.append({"pid": pid, "name": r.get("player_name", ""), "prices": prices})
    return {"event_name": (data or {}).get("event_name", ""), "odds": rows}


def cache_age_days() -> float | None:
    """Age of the oldest cached endpoint, for staleness reporting (no provider info)."""
    ages = []
    for path in FEED_CACHE.glob("*.json"):
        c = _read_cache(path.stem) or {}
        if c.get("_fetched_at"):
            ages.append(_age_seconds(c["_fetched_at"]) / SECONDS_PER_DAY)
    return round(max(ages), 2) if ages else None
