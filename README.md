# T0AE (Tier-0 Alpha Engine)

Automated pipeline that watches fresh FDA approval/advisory data (via the openFDA Drugs@FDA API), asks OpenAI to translate them into actionable XBI ETF trading signals, and pushes strong alerts to your phone via [ntfy.sh](https://ntfy.sh/).

## What it does
1. Scrapes the FDA approvals feed (openFDA Drugs@FDA API, sorted by latest submissions) for the last N hours and skips anything already processed.
2. Normalizes each item into an internal `FDAEvent` model.
3. Sends each event to OpenAI with a strict JSON schema to extract sentiment, affected companies, expected XBI move, confidence, and a concise narrative.
4. Filters out low-confidence or low-magnitude signals.
5. Publishes strong signals to your ntfy topic so your phone receives a push.
6. Runs hourly via GitHub Actions or locally via `python -m src.main`.

## Project layout
```
src/
  config.py            # environment-driven settings
  models.py            # dataclasses for FDAEvent and XBISignal
  fda_scraper.py       # openFDA fetch + RSS parser fallback + deduped FDA events
  xbi_signal_engine.py # OpenAI analysis and filtering
  notify.py            # ntfy push helper
  main.py              # orchestration entrypoint
.github/workflows/t0ae-cron.yml # hourly GitHub Actions runner
tests/                # pytest coverage for parsing and filtering
```

## Setup & running locally
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Export required environment variables (example values):
   ```bash
   export OPENAI_API_KEY="sk-..."
   export OPENAI_MODEL="gpt-4.1-mini"
   export NTFY_TOPIC_URL="https://ntfy.sh/your-topic"
   export MIN_CONFIDENCE="0.6"
   export MIN_EXPECTED_MOVE="0.7"
   export FDA_LOOKBACK_HOURS="2"
   ```
3. Run the engine:
   ```bash
   python -m src.main
   ```
4. A `.data/seen_fda_ids.json` file tracks which FDA items were already handled to avoid duplicate notifications.

## GitHub Actions (hourly cron)
The workflow `.github/workflows/t0ae-cron.yml` runs hourly. Configure repository secrets:
- `OPENAI_API_KEY`
- `NTFY_TOPIC_URL`

Optional overrides (already given defaults in the workflow):
- `OPENAI_MODEL` (defaults to `gpt-4.1-mini`)
- `MIN_CONFIDENCE`
- `MIN_EXPECTED_MOVE`
- `FDA_LOOKBACK_HOURS`

## ntfy mobile setup
1. Install the ntfy app (iOS/Android).
2. Subscribe to your chosen topic URL (e.g., `https://ntfy.sh/t0ae-rayan-signals-xyz`).
3. When T0AE produces a strong signal, you’ll get a push with direction, expected move, confidence, companies, and a short narrative.

## Testing
Run the unit tests with:
```bash
OPENAI_API_KEY="test" NTFY_TOPIC_URL="https://ntfy.sh/dev" pytest
```

## Notes
- FDA feed parsing is resilient to network failures and will return no events rather than crashing.
- OpenAI errors during analysis are caught so one bad call will not break the entire run.
