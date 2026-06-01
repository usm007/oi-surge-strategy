"""
OI Surge Strategy — GitHub Actions Signal Generator
Run after market close to produce signal card embedded into index.html.
"""
import csv, os, sys, json, ssl
from datetime import datetime, date, timedelta
from io import StringIO
from urllib.request import urlopen, Request

LOT_SIZE = 65
OI_MIN = 100_000
DAILY_CAPITAL = 20_000
MAX_PREMIUM = DAILY_CAPITAL / LOT_SIZE
BROKERAGE, STT_PCT, TC_PCT, GST_PCT = 20, 0.0005, 0.00053, 0.18

NSE_RISE_URL = (
    "https://www.nseindia.com/api/live-analysis-oi-spurts-contracts"
    "?type=Rise-in-OI-Rise&csv=true"
)
NSE_FALL_URL = (
    "https://www.nseindia.com/api/live-analysis-oi-spurts-contracts"
    "?type=Fall-in-OI-Fall&csv=true"
)


def day_name(d):
    return ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][d.weekday()]


def premium_cat(p):
    if p <= 50:
        return "Deep OTM"
    if p <= MAX_PREMIUM * 0.5:
        return "Mild OTM"
    if p <= MAX_PREMIUM:
        return "ATM/ITM"
    return "Deep ITM"


def signal_strength(oi_pct):
    abspct = abs(oi_pct)
    if abspct > 500:
        return "Extreme"
    if abspct > 300:
        return "Strong"
    if abspct > 100:
        return "Moderate"
    return "Weak"


def compute_costs(entry, exit_):
    brokerage = BROKERAGE * 2
    stt = STT_PCT * exit_ * LOT_SIZE
    turnover = (entry + exit_) * LOT_SIZE
    tc = TC_PCT * turnover
    gst = GST_PCT * (brokerage + tc)
    return round(brokerage + stt + tc + gst, 2)


def fetch_csv(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    }
    req = Request(url, headers=headers)
    ctx = ssl._create_unverified_context()
    resp = urlopen(req, timeout=30, context=ctx)
    return resp.read().decode("utf-8-sig").strip()


def parse_csv(content):
    options = []
    lines = content.split("\n")
    reader = csv.reader(StringIO("\n".join(lines)))
    for i, row in enumerate(reader):
        if i == 0 or len(row) < 15:
            continue
        try:
            expiry = row[2].strip()
            strike = float(row[3])
            opt_type = "CE" if row[4].strip().upper() == "CE" else "PE"
            oi_curr = float(row[5].replace(",", ""))
            oi_prev = float(row[6].replace(",", ""))
            oi_chg = float(row[7].replace(",", ""))
            oi_chg_pct = float(row[8].replace(",", ""))
            ltp = float(row[9].replace(",", ""))
            prev_close = float(row[10].replace(",", ""))
            underlying = float(row[14].replace(",", ""))
        except (ValueError, IndexError):
            continue
        options.append({
            "strike": strike,
            "opt_type": opt_type,
            "expiry": expiry,
            "oi_current": oi_curr,
            "oi_prev": oi_prev,
            "oi_change": oi_chg,
            "oi_change_pct": oi_chg_pct,
            "ltp": ltp,
            "prev_close": prev_close,
            "underlying": underlying,
        })
    return options


def next_trade_date():
    """Return the next trading day (skip weekends)."""
    d = date.today() + timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def build_signal_data(options, capital, sources_used=None):
    """Build the full JSON payload for the HTML template."""
    if sources_used is None:
        sources_used = []
    valid = [o for o in options if o["oi_prev"] >= OI_MIN]
    valid.sort(key=lambda o: abs(o["oi_change_pct"]), reverse=True)

    if not valid:
        return {"status": "no_data",
                "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "message": "No strikes with sufficient OI found."}

    top = valid[0]
    entry_price = top["prev_close"]
    skip1 = entry_price > 300 and abs(top["oi_change_pct"]) > 300
    skip2 = entry_price > 1500 and top["oi_change_pct"] < -90

    reason = ""
    if skip1:
        reason = f"Extreme OI Trap (entry Rs{entry_price:.0f} > Rs300, |OI| {abs(top['oi_change_pct']):.0f}% > 300%)"
    elif skip2:
        reason = f"OI Collapse (entry Rs{entry_price:.0f} > Rs1,500, OI {top['oi_change_pct']:.0f}% < -90%)"

    direction = "Rise" if top["oi_change_pct"] >= 0 else "Fall"
    strength = signal_strength(top["oi_change_pct"])
    premium = premium_cat(entry_price)
    capital_needed = entry_price * LOT_SIZE
    affordable = capital_needed <= capital

    trade_day = next_trade_date()
    trade_day_name = day_name(trade_day)

    # Alternatives: all valid strikes with OI >= min
    alternatives = []
    for o in valid:
        ep = o["prev_close"]
        s1 = ep > 300 and abs(o["oi_change_pct"]) > 300
        s2 = ep > 1500 and o["oi_change_pct"] < -90
        tradeable = (ep * LOT_SIZE <= capital) and not (s1 or s2)
        alternatives.append({
            "strike": o["strike"],
            "opt_type": o["opt_type"],
            "oi_change_pct": o["oi_change_pct"],
            "entry_price": ep,
            "capital_needed": ep * LOT_SIZE,
            "tradeable": tradeable,
        })

    return {
        "status": "ok",
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "trade_date": trade_day.strftime("%Y-%m-%d"),
        "trade_day": trade_day_name,
        "daily_capital": capital,
        "affordable": affordable,
        "underlying": top["underlying"],
        "data_source": sources_used,
        "signal": {
            "strike": top["strike"],
            "opt_type": top["opt_type"],
            "expiry": top["expiry"],
            "entry_price": round(entry_price, 1),
            "prev_close": top["prev_close"],
            "oi_change_pct": top["oi_change_pct"],
            "oi_direction": direction,
            "signal_strength": strength,
            "premium_category": premium,
            "capital_needed": capital_needed,
            "tradeable": not (skip1 or skip2),
            "skip_extreme_trap": skip1,
            "skip_collapse": skip2,
            "skip_reason": reason,
            "estimated_costs": compute_costs(entry_price, entry_price * 1.02),
        },
        "alternatives": alternatives,
    }


def inject_into_html(html_path, json_data):
    js_path = os.path.join(os.path.dirname(html_path), "signal.js")
    json_str = json.dumps(json_data, indent=2)
    with open(js_path, "w", encoding="utf-8") as f:
        f.write(f"const SIGNAL_DATA = {json_str};\n")


def main():
    capital = DAILY_CAPITAL

    print("=" * 48)
    print("  OI SURGE — Signal Generator (GH Actions)")
    print("=" * 48)
    print(f"  Capital: Rs{capital:,.0f}")

    # Fetch data from NSE Rise endpoint (Fall endpoint is deprecated by NSE)
    sources_used = []
    all_options = []
    print(f"  Fetching Rise...", end=" ")
    try:
        content = fetch_csv(NSE_RISE_URL)
        opts = parse_csv(content)
        all_options.extend(opts)
        sources_used.append("Rise")
        print(f"{len(opts)} strikes")
    except Exception as e:
        print(f"FAILED: {e}")

    # Attempt Fall endpoint (may be disabled by NSE)
    print(f"  Fetching Fall...", end=" ")
    try:
        content = fetch_csv(NSE_FALL_URL)
        opts = parse_csv(content)
        all_options.extend(opts)
        sources_used.append("Fall")
        print(f"{len(opts)} strikes")
    except Exception as e:
        print(f"  (unavailable: {e})")

    if not all_options:
        print("  FATAL: No data from NSE.")
        data = {"status": "no_data", "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "message": "Failed to fetch NSE data."}
        inject_into_html("docs/index.html", data)
        sys.exit(1)

    data_source = "+".join(sources_used) if sources_used else "Rise"
    print(f"  Total: {len(all_options)} options (source: {data_source})")

    # Build signal
    data = build_signal_data(all_options, capital, sources_used)
    s = data["signal"]
    print(f"  Top signal: {s['strike']:.0f}{s['opt_type']} (|OI| {abs(s['oi_change_pct']):.1f}%)")
    print(f"  Strength: {s['signal_strength']} | Dir: {s['oi_direction']}")
    print(f"  Tradeable: {s['tradeable']}")
    if not s['tradeable']:
        print(f"  Reason: {s['skip_reason']}")
    if not data['affordable']:
        print(f"  Capital: NEED Rs{s['capital_needed']:,.0f} > HAVE Rs{capital:,.0f}")

    # Inject into signal.js
    script_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(script_dir, "docs", "index.html")
    inject_into_html(html_path, data)
    print(f"  Written to docs/signal.js")
    print("=" * 48)


if __name__ == "__main__":
    main()
