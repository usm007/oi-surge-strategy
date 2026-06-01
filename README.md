# OI Surge Strategy

Daily Nifty options signal based on Open Interest surge analysis.

## How It Works

1. **GitHub Actions** runs Mon–Fri at 3:30 PM IST (10:00 UTC)
2. **`generate_signal.py`** fetches NSE OI Spurts CSV → picks highest |OI%| strike
3. Injects signal data into **`docs/index.html`** → commits + pushes
4. **GitHub Pages** serves `docs/index.html` as the live dashboard

## Results (Backtest: Sep 2024 – Mar 2026)

| Metric | Value |
|---|---|
| Total Trades | 260 |
| Net P&L | +₹4,00,114 |
| Win Rate | 70.4% |
| Profit Factor | 17.12 |
| Max Loss | -₹6,742 |
| Profitable Months | 19 / 19 |

## Enabling Pages

1. Go to repo → Settings → Pages
2. Source: **Deploy from branch**
3. Branch: `main` / folder: `docs`
4. Save → your dashboard is live at `https://<user>.github.io/<repo>`

## Files

- `generate_signal.py` — fetches NSE data, computes signal, updates `docs/index.html`
- `docs/index.html` — the live dashboard (auto-generated)
- `.github/workflows/oi_surge.yml` — daily workflow definition
