# GolfModel

A Monte Carlo stroke-simulation engine that prices a whole golf tournament — winner,
top-5/10/20, make-cut, round and tournament totals, player matchups, and Dabble
Pick'em — and flags value against the bookmakers. Static site deploys to GitHub Pages.

**Live:** https://danieltomaro13.github.io/GolfModel/

## How it works

The engine turns on one number per player: a **rating in strokes per round** (lower is
better). Calibration solves each rating so the simulated win frequencies reproduce the
bookmaker win market. With ratings fixed, the engine plays the tournament ~20,000 times —
each round an independent normal draw around the rating, the field ranked, the halfway cut
applied, ties broken by playoff — and reads every market straight off the empirical
frequencies.

## Layout

```
pipeline/                 Python engine + scrapers
  src/golfmodel/
    feed.py               upstream data client (weekly on-disk cache)
    engine/               field -> calibrate -> simulate -> markets
    scrape/               multi-book odds + Dabble Pick'em + AU books
    build.py              orchestrates everything -> web/public/data/*.json
web/                      Next.js static site (reads the JSON at build time)
.github/workflows/        deploy.yml (site) + update.yml (manual data refresh)
```

## Updating the data — manual only

Nothing runs on a schedule. When you want fresh numbers:

1. Go to the repo's **Actions** tab → **Update data** → **Run workflow**.
2. It re-prices the model, refreshes odds, commits the JSON, and the site redeploys.

Configuration lives in repository **secrets** (`FEED_API_KEY`, `FEED_BASE_URL`); they are
never stored in the code or the committed data.

## Running locally

```bash
python3 -m venv .venv && ./.venv/bin/pip install -r pipeline/requirements.txt
cp .env.example .env            # fill in FEED_API_KEY and FEED_BASE_URL
PYTHONPATH=pipeline/src ./.venv/bin/python -m golfmodel.build --sims=20000 --refresh
cd web && npm install && NEXT_PUBLIC_BASE_PATH=/GolfModel npm run build
```

## Notes

- For research and entertainment only. Not financial advice. 18+.
- The four extra AU books (Sportsbet/TAB/Ladbrokes) activate once their live event id is
  set via env (`SB_GOLF_EVENT_ID`, `TAB_GOLF_COMP`, `LAD_GOLF_EVENT_ID`).
