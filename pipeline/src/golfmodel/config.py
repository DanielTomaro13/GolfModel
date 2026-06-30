"""Shared paths and environment loading for the pipeline."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# repo_root/pipeline/src/golfmodel/config.py  ->  repo_root
REPO_ROOT = Path(__file__).resolve().parents[3]
PIPELINE_DIR = REPO_ROOT / "pipeline"
DATA_DIR = PIPELINE_DIR / "data"
FEED_CACHE = DATA_DIR / "feed"
WEB_DATA_DIR = REPO_ROOT / "web" / "public" / "data"

# Load .env from repo root (git-ignored). CI provides these as real env vars.
load_dotenv(REPO_ROOT / ".env")


def feed_key() -> str:
    key = os.environ.get("FEED_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "FEED_API_KEY is not set. Copy .env.example to .env and fill it in, "
            "or set it as an environment variable / CI secret."
        )
    return key


def feed_base() -> str:
    base = os.environ.get("FEED_BASE_URL", "").strip().rstrip("/")
    if not base:
        raise RuntimeError(
            "FEED_BASE_URL is not set. Set it in .env or as a CI secret."
        )
    return base


def ensure_dirs() -> None:
    for d in (DATA_DIR, FEED_CACHE, WEB_DATA_DIR):
        d.mkdir(parents=True, exist_ok=True)
