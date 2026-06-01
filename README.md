# BustRadar 🏈

A pre-season fantasy football bust predictor for the 2026 NFL season. BustRadar assigns every relevant skill position player (WR, RB, TE) a composite bust risk score using five data-driven inputs, helping fantasy managers avoid costly draft mistakes before the season starts.

## What It Does

BustRadar pulls 2025 NFL season data and 2026 ADP data, runs each player through a weighted scoring model, and surfaces the players most likely to underperform their draft position. Players are ranked by bust score with color-coded risk levels (High / Medium / Low), hover tooltips breaking down each scoring input, and headshots pulled dynamically from the nflverse public dataset.

Rookies are handled separately — since they have no 2025 NFL data, they're scored manually using draft capital and landing spot as opportunity proxies.

## Scoring Model

Each veteran player receives a bust score from 0–100 based on six weighted inputs:

| Input | Weight | Logic |
|---|---|---|
| Age vs Decline Curve | 25% | WR 29+, RB 28+, TE 30+ flagged |
| FPPG (Fantasy Points Per Game) | 25% | Injury-resistant per-game output |
| Role Share | 20% | Targets (WR/TE) + Carries (RB), efficiency-adjusted |
| Injury History | 10% | Games played % — capped at 60 to avoid overpenalizing injured stars |
| TD Regression | 10% | High TD rate relative to opportunities signals regression |
| ADP vs 2025 Finish | 10% | Gap between 2026 draft price and 2025 actual finish |

Higher score = higher bust risk.

## Tech Stack

**Backend**
- Python / Flask — REST API serving scored player data as JSON
- pandas — data loading, cleaning, and merging across four sources
- Flask-CORS — enables frontend/backend communication across ports

**Frontend**
- Vanilla HTML / CSS / JavaScript — no frameworks
- Fetch API — pulls player data from the Flask backend
- Live filtering by position, sorting by bust score/ADP/name, and player search

**Data Sources**
- [Pro Football Reference](https://www.pro-football-reference.com) — 2025 season stats (fantasy, receiving, rushing)
- [FantasyPros](https://www.fantasypros.com) — 2026 ADP data
- [nflverse](https://github.com/nflverse/nflverse-data) — player headshot URLs

## Project Structure
bust-predictor/
│
├── backend/
│   ├── app.py              # Flask API
│   ├── data_loader.py      # Data pipeline — loads, cleans, merges all sources
│   ├── scorer.py           # Bust scoring model
│   ├── rookies.py          # Manually curated 2026 rookie data
│   └── data/
│       ├── fantasy.csv     # 2026 ADP from FantasyPros
│       ├── fantasy_2025.csv
│       ├── receiving_2025.csv
│       └── rushing_2025.csv
│
├── frontend/
│   ├── index.html
│   ├── style.css
│   ├── app.js
│   └── silhouette.png
│
└── requirements.txt
## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run the backend
python app.py

# Open frontend via Live Server in VSCode
# Navigate to localhost:5500
```

## Limitations

- Scores are based on 2025 performance data only
- Offseason role changes, trades, and injuries are not reflected
- Use as a draft guide, not a guarantee — context always matters
