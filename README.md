# Strava Training Analyzer

> 🇧🇷 [Leia em Português](README.pt-BR.md)

A local Python CLI tool that connects to the Strava API, collects your running data, and generates a structured Markdown report — designed to be consumed by an AI agent that helps runners understand their progress and answer questions about their training.

## What it does

- Authenticates with your Strava account via OAuth 2.0 (automatic browser flow)
- Collects runs from the last N days (default: 30)
- Calculates aggregated statistics, pace and power trends
- Projects race times using a hybrid system: **direct Best Efforts** (when available) or **Riegel Formula** as fallback
- Identifies **treadmill vs outdoor** runs
- Shows **shoes used** with km for the period and accumulated totals
- Displays **per-km splits** (pace + HR) for each run
- Consolidates your **historical best times** by standard distance (400m, 1K, 5K, 10K, Half, Marathon)
- Lists **Strava segments with PR** from outdoor runs
- Generates `report.md` ready to be pasted into an AI agent (Claude, ChatGPT, etc.)
- Local cache avoids re-calling the API on repeated runs

## Architecture

The project applies **Layered Architecture** — dependencies flow in one direction only:

```
main.py           → CLI entry point (argparse)
application/      → single use case: orchestrates the layers
domain/           → pure logic (calculators, models) — zero external dependencies
infra/            → external systems (Strava API, files)
```

The golden rule: `domain/` can be tested without internet and without creating files.

## Prerequisites

- Python 3.12+
- A Strava account
- App created at [strava.com/settings/api](https://www.strava.com/settings/api)
  - **Authorization Callback Domain:** `localhost`

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/alvespedro/strava-analyzer.git
cd strava-analyzer

# 2. Create and activate the virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up credentials
cp .env.example .env
# Edit .env with your STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET
```

## Usage

```bash
# Default analysis (last 30 days)
python3 main.py

# Custom time window
python3 main.py --days 60

# Force API refresh (ignore cache)
python3 main.py --refresh

# Custom report name
python3 main.py --output my_report.md

# Combining options
python3 main.py --days 90 --refresh --output q1_report.md
```

On the **first run**, the browser will open automatically for you to authorize Strava access. After that, the token is saved locally and refreshed silently.

## Output

The command generates `report.md` with 14 sections:

| # | Section | Content |
|---|---------|---------|
| 1 | General Statistics | Total km, time, average pace, HR, power, calories, achievements and PRs |
| 2 | Pace Trend | Direction (improving/regressing/stable) with linear regression |
| 3 | Treadmill vs Outdoor | Run distribution by surface |
| 4 | Shoes Used | Km per shoe in the period and accumulated total |
| 5 | Race Projections | 5K, 10K, Half Marathon and Marathon — direct Best Effort or Riegel as fallback |
| 6 | Running Power | Average watts and trend (requires compatible sensor) |
| 7 | Run Log | Detailed table with all activities in the period |
| 8 | Weekly Breakdown | Volume and metrics grouped by week |
| 9 | Notable Runs | Longest, fastest, highest elevation, highest HR |
| 10 | Training Load | km/week and consistency |
| 11 | Personal Best Efforts | Historical best times by standard distance, with PR flag |
| 12 | Notable Segments | PRs on Strava segments from outdoor runs |
| 13 | Per-km Splits | Pace + HR for each kilometer of each run |
| 14 | Notes & Limitations | Count of activities missing HR, cadence, splits |

### Hybrid projection system

Section 5 uses two methods depending on available data:

- **✅ Best Effort (direct)** — real time recorded by Strava for that distance. Appears when you ran that distance continuously (e.g. a complete 10K race). This is the most accurate data.
- **📐 Riegel (estimated)** — projection using the formula `T2 = T1 × (D2/D1)^1.06`, calculated from your longest run. Used as fallback for distances without an available Best Effort.

### How to use the report with an AI agent

1. Run `python3 main.py` to generate `report.md`
2. Open the file and copy all the content
3. Paste it into a conversation with Claude, ChatGPT, or another agent
4. Ask questions like:
   - *"How is my pace trending?"*
   - *"When should I replace my shoes?"*
   - *"Is my weekly volume adequate for a half marathon?"*
   - *"At which km does my pace drop the most in long runs?"*
   - *"What was my best 5K this month?"*

## File structure

```
strava-analyzer/
├── main.py                  # CLI entry point
├── application/
│   └── analyzer.py          # Main use case
├── domain/
│   ├── models.py            # Dataclasses (Activity, Stats, Report...)
│   └── calculators.py       # Riegel, trends, statistics
├── infra/
│   ├── strava_auth.py       # OAuth 2.0
│   ├── strava_fetcher.py    # Strava API calls
│   ├── cache_repository.py  # Local cache (token.json)
│   └── report_writer.py     # Markdown generation
├── requirements.txt
├── .env.example
└── .gitignore
```

## Generated files (not versioned)

| File | Description |
|------|-------------|
| `.env` | Your Strava credentials — **never commit this file** |
| `token.json` | OAuth token and activity cache — regenerated automatically |
| `report.md` | Generated report — contains personal data (HR, location, real pace); not versioned by default |

> If you want to version your reports, remove `report.md` from `.gitignore` and use dated names: `--output report_2025-01.md`.

## Dependencies

| Package | Version | Use |
|---------|---------|-----|
| `stravalib` | 1.6.0 | Strava API wrapper |
| `python-dotenv` | 1.0.0 | `.env` file loading |
| `requests` | 2.31.0 | HTTP requests for OAuth |

Everything else (argparse, http.server, statistics, datetime) is from the Python stdlib.

## Strava rate limits

The Strava API allows 100 requests/15min and 1,000/day. A typical run uses:

| Operation | Calls |
|-----------|-------|
| Activity list | 1 |
| Per-activity details (splits + best efforts + segments) | ~20–60 (1 per run) |
| Shoe resolution | 2–5 (unique IDs) |
| **Total** | **< 70** |

The local cache avoids re-calling the API — use `--refresh` only when you want updated data.
