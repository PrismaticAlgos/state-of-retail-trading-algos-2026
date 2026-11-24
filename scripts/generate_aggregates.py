#!/usr/bin/env python3
"""Generate the aggregate tables in data/ from a local, gitignored corpus.

Input : raw/strategies.json  (a JSON list, {"strategies": [...]}, or JSON Lines)
Output: data/summary_metrics.json
        data/family_distribution.csv
        data/indicator_crowding.csv
        data/risk_control_gaps.csv
        data/timeframe_asset_matrix.csv
        data/schema_sample.csv        (optional, --sample N; flags only, no text)

Only counts and percentages leave this script. No strategy text, names, URLs,
authors, or source code are written to data/. The raw file is excluded by
.gitignore and must never be committed.

Each record is classified from its documented text (every string field is
concatenated) plus any structured fields that happen to exist. Explicit
fields win over keyword detection:
    family, timeframe, asset_class / symbol, sharpe, trade_count,
    stop_loss, take_profit, position_sizing, out_of_sample
Standard library only. Python 3.9+.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_IN = ROOT / "raw" / "strategies.json"
OUT = ROOT / "data"

# ---------------------------------------------------------------- taxonomy
# Order matters: first match wins for the primary family.
FAMILIES = [
    ("Risk/Portfolio Overlays", r"\b(equity (protector|guard)|drawdown (limit|guard)|portfolio|risk manager|daily loss limit|hedg(e|ing) overlay|basket close)\b"),
    ("Trade/Execution Management", r"\b(trade manager|trailing stop manager|break.?even manager|order manager|copier|trade copier|partial close|execution|utility)\b"),
    ("Time/Session", r"\b(session|london open|new york open|asian (range|session)|opening range|time.?based|day of week|news (trading|straddle)|killzone)\b"),
    ("Volatility", r"\b(volatility|atr breakout|squeeze|bollinger (squeeze|breakout)|keltner|range expansion|vix)\b"),
    ("Mean Reversion", r"\b(mean reversion|revert|oversold|overbought|reversal|counter.?trend|fade|grid|martingale)\b"),
    ("Trend Following", r"\b(trend|moving average cross|ma cross|ema cross|breakout|momentum|donchian|turtle|supertrend|ichimoku)\b"),
    ("Price Action/Structure", r"\b(price action|support|resistance|supply|demand|order block|fair value gap|fvg|smart money|smc|candlestick|pin bar|engulfing|pivot|fibonacci|market structure|liquidity sweep)\b"),
]
# Corpus taxonomy (12 families). Used when records carry a family code.
FAMILY_CODES = {
    "A": "Trend Following & Directional", "B": "Mean Reversion & Counter-Trend",
    "C": "Grid, Martingale & Averaging", "D": "Scalping & Short-Horizon",
    "E": "Price Action & Market Structure", "F": "Time, Session & Seasonality",
    "G": "Volatility-Based", "H": "Carry, Swap & Fundamental",
    "I": "Statistical, Quantitative & ML", "J": "Risk, Money Management & Portfolio Overlays",
    "K": "Trade & Execution Management", "L": "Confluence & Multi-Timeframe",
}
FAMILY_NAMES = list(FAMILY_CODES.values()) + ["Unclassified"]
KEYWORD_FAMILY_NAMES = [f for f, _ in FAMILIES] + ["Unclassified"]
FAMILY_RE = [(f, re.compile(p, re.I)) for f, p in FAMILIES]

INDICATORS = {
    "EMA": r"\b(ema|exponential moving average)\b",
    "SMA": r"\b(sma|simple moving average)\b",
    "Moving Average (unspecified)": r"^\s*(ma|mas|average|moving averages?)\s*$|\bmoving average\b(?!.*\b(exponential|simple|weighted)\b)",
    "WMA/LWMA": r"\b(l?wma|(linear )?weighted moving average)\b",
    "RSI": r"\b(rsi|relative strength index)\b",
    "MACD": r"\bmacd\b",
    "Bollinger Bands": r"\bbollinger\b",
    "ATR": r"\b(atr|average true range)\b",
    "Stochastic": r"\bstoch(astic)?\b",
    "ADX/DMI": r"\b(adx|dmi|directional movement)\b",
    "CCI": r"\b(cci|commodity channel)\b",
    "Ichimoku": r"\bichimoku\b",
    "Parabolic SAR": r"\b(parabolic sar|psar)\b",
    "Fibonacci": r"\bfibonacci\b",
    "Pivot Points": r"\bpivot(s| points?)?\b",
    "Donchian Channel": r"\bdonchian\b",
    "Keltner Channel": r"\bkeltner\b",
    "Supertrend": r"\bsuper ?trend\b",
    "VWAP": r"\bvwap\b",
    "Williams %R": r"\bwilliams ?%?r\b",
    "Momentum": r"\bmomentum indicator\b",
    "Envelopes": r"\benvelopes?\b",
    "Heikin Ashi": r"\bheiken|heikin\b",
    "Volume / OBV": r"\b(obv|on.?balance volume|volume profile)\b",
    "Awesome Oscillator": r"\bawesome oscillator\b",
    "MFI": r"\b(mfi|money flow index)\b",
    "Zigzag": r"\bzig ?zag\b",
    "Fractals": r"\bfractals?\b",
    "Hull MA": r"\bhull\b",
    "Neural net / ML": r"\b(neural network|machine learning|lstm|gpt|chatgpt|ai model)\b",
}
INDICATOR_RE = {k: re.compile(v, re.I) for k, v in INDICATORS.items()}

TIMEFRAMES = [("M1", r"\b(m1|1 ?min(ute)?)\b"), ("M5", r"\b(m5|5 ?min(ute)?)\b"),
              ("M15", r"\b(m15|15 ?min(ute)?)\b"), ("M30", r"\b(m30|30 ?min(ute)?)\b"),
              ("H1", r"\b(h1|1 ?hour|hourly)\b"), ("H4", r"\b(h4|4 ?hours?)\b"),
              ("D1", r"\b(d1|daily chart|daily timeframe)\b"), ("W1+", r"\b(w1|weekly|mn1|monthly)\b")]
TIMEFRAME_RE = [(t, re.compile(p, re.I)) for t, p in TIMEFRAMES]

ASSETS = [("Gold/Metals", r"\b(xau\w*|gold|xag\w*|silver)\b"),
          ("Crypto", r"\b(btc\w*|bitcoin|eth(usd\w*)?|ethereum|crypto\w*)\b"),
          ("Indices", r"\b(us30|dow|nas(daq)?100|us100|ustec|spx|s&p ?500|us500|dax|de40|ger40|nikkei|ftse)\b"),
          ("Energy", r"\b(wti|brent|crude|oil|natgas|usoil|ukoil)\b"),
          ("Stocks", r"\b(stocks?|equit(y|ies)|shares)\b"),
          ("FX", r"\b(forex|fx|(eur|gbp|usd|jpy|aud|nzd|cad|chf){2}|currency pairs?)\b")]
ASSET_RE = [(a, re.compile(p, re.I)) for a, p in ASSETS]

RX = {
    "stop_loss": re.compile(r"\b(stop.?loss|\bsl\b|hard stop|protective stop)\b", re.I),
    "no_stop_loss": re.compile(r"\b(no stop.?loss|without (a )?stop.?loss|does not use (a )?stop.?loss|no sl)\b", re.I),
    "take_profit": re.compile(r"\b(take.?profit|\btp\b|profit target)\b", re.I),
    "position_sizing": re.compile(r"\b(lot siz(e|ing)|position siz(e|ing)|risk per trade|risk %|% risk|money management|fixed fractional|auto ?lot)\b", re.I),
    "grid": re.compile(r"\bgrid\b", re.I),
    "martingale": re.compile(r"\b(martingale|lot multiplier|doubl(e|ing) (the )?lot|averaging down|recovery (mode|lots?))\b", re.I),
    "grid_bounded": re.compile(r"\b(max(imum)? (orders|trades|levels|positions)|basket stop|equity stop|grid limit)\b", re.I),
    "sharpe": re.compile(r"\bsharpe\b", re.I),
    "sortino": re.compile(r"\bsortino\b", re.I),
    "profit_factor": re.compile(r"\bprofit factor\b", re.I),
    "max_drawdown": re.compile(r"\b(max(imum)?|relative|equity) drawdown\b", re.I),
    "oos": re.compile(r"\b(out.of.sample|oos|walk.?forward|forward test|unseen data|hold.?out)\b", re.I),
    "trade_count": re.compile(r"\b(\d[\d,]*)\s+(trades|deals|positions)\b", re.I),
    "real_ticks": re.compile(r"\b(real ticks|every tick based on real|99(\.9)?% (modell?ing )?quality|tick data suite|dukascopy)\b", re.I),
}
NOT_SPECIFIED = re.compile(r"^\s*$|not (explicitly )?(specified|stated|mentioned|provided|given|defined)|^n/?a\b|^none\b|^no(ne)? (stop|sl|tp|take)|unknown|unspecified|^null$|^-$", re.I)
SMALL_SAMPLE = 100  # trade-count warning threshold


# ---------------------------------------------------------------- helpers
def load(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    if isinstance(obj, dict):
        for key in ("strategies", "items", "records", "data"):
            if isinstance(obj.get(key), list):
                return obj[key]
        raise SystemExit(f"Unrecognised top-level keys: {list(obj)[:10]}")
    return obj


def flatten_text(rec, depth=0) -> str:
    if depth > 4:
        return ""
    if isinstance(rec, str):
        return rec
    if isinstance(rec, dict):
        return " ".join(flatten_text(v, depth + 1) for v in rec.values())
    if isinstance(rec, list):
        return " ".join(flatten_text(v, depth + 1) for v in rec)
    return ""


def get(rec: dict, *keys):
    for k in keys:
        if k in rec and rec[k] not in (None, ""):
            return rec[k]
    return None


def truthy(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    return str(v).strip().lower() in {"1", "true", "yes", "y", "present"}


def documented(v) -> bool:
    """True when a structured spec field holds a real value, not a placeholder."""
    if v is None:
        return False
    if isinstance(v, (list, dict)):
        return any(documented(x) for x in (v.values() if isinstance(v, dict) else v))
    if isinstance(v, bool):
        return v
    return not NOT_SPECIFIED.search(str(v).strip())


PLACEHOLDER_NAME = re.compile(r"^\s*(null|none|n/?a|unknown|not specified|-)?\s*$", re.I)


def canon_indicator(name: str) -> str:
    for label, rx in INDICATOR_RE.items():
        if rx.search(name):
            return label
    return name.strip().title()[:40]


def classify(rec: dict) -> dict:
    text = flatten_text({k: v for k, v in rec.items() if k not in ("code_files", "doc_url", "spec_file")})
    structured = "claimed_metrics" in rec or "evidence_type" in rec

    # family: corpus code, else explicit name, else keyword rule
    code = rec.get("family")
    if structured:
        fam = FAMILY_CODES.get(str(code).strip().upper()[:1], "Unclassified") if code else "Unclassified"
    else:
        fam = code if code in KEYWORD_FAMILY_NAMES else next((f for f, rx in FAMILY_RE if rx.search(text)), "Unclassified")

    # indicators: structured list, else keyword scan
    names = [i.get("name") if isinstance(i, dict) else i for i in (rec.get("indicators") or [])]
    names = [n for n in names if isinstance(n, str) and not PLACEHOLDER_NAME.match(n)]
    inds = sorted({canon_indicator(n) for n in names}) if names else sorted(k for k, rx in INDICATOR_RE.items() if rx.search(text))

    tfs = rec.get("timeframes_norm") or rec.get("timeframes") or []
    tfs = [tfs] if isinstance(tfs, str) else tfs
    # primary timeframe = first recognisable entry; "Multiple" when several distinct ones are listed
    found = []
    for t in tfs:
        lab = next((lab for lab, rx in TIMEFRAME_RE if rx.search(str(t))), None)
        if lab and lab not in found:
            found.append(lab)
    if not tfs and not structured:
        found = [next((t for t, rx in TIMEFRAME_RE if rx.search(text)), "Unspecified")]
    tf = "Unspecified" if not found else found[0] if len(found) == 1 else "Multiple"

    syms = " ".join(map(str, rec.get("symbols_norm") or rec.get("symbols") or []))
    asset = (get(rec, "asset_class")
             or next((a for a, rx in ASSET_RE if rx.search(syms)), None)
             or ("Unspecified" if structured else next((a for a, rx in ASSET_RE if rx.search(text)), "Unspecified")))

    if structured:
        sl = documented(rec.get("stop_loss")) and not RX["no_stop_loss"].search(str(rec.get("stop_loss")))
        tp = documented(rec.get("take_profit"))
        ps = documented(rec.get("position_size"))
    else:
        sl = bool(RX["stop_loss"].search(text)) and not RX["no_stop_loss"].search(text)
        tp = bool(RX["take_profit"].search(text))
        ps = bool(RX["position_sizing"].search(text))

    grid = fam.startswith("Grid") or bool(RX["grid"].search(text))
    mart = bool(RX["martingale"].search(text))
    unbounded = (grid or mart) and not sl and not RX["grid_bounded"].search(text)

    cm = rec.get("claimed_metrics") or {}
    cm_keys = " ".join(k for k, v in cm.items() if v not in (None, "")) if isinstance(cm, dict) else ""
    sharpe = bool(re.search(r"sharpe", cm_keys, re.I)) or bool(RX["sharpe"].search(text))
    ev = str(rec.get("evidence_type") or "none")
    oos = bool(rec.get("forward_tested")) or "forward_results" in ev or bool(RX["oos"].search(text))

    n = cm.get("total_trades") if isinstance(cm, dict) else None
    if n is None and not structured:
        m = [int(x.replace(",", "")) for x, _ in RX["trade_count"].findall(text) if x.replace(",", "").isdigit()]
        n = max(m) if m else None
    try:
        n = int(float(n)) if n is not None else None
    except (TypeError, ValueError):
        n = None

    def has(k):
        return isinstance(cm, dict) and cm.get(k) not in (None, "")

    return {
        "family": fam, "indicators": inds, "timeframe": tf, "asset": asset,
        "stop_loss": sl, "take_profit": tp, "position_sizing": ps,
        "grid": grid, "martingale": mart, "unbounded_grid_martingale": unbounded,
        "sharpe": sharpe, "sortino": bool(RX["sortino"].search(text)),
        "profit_factor": has("profit_factor") or bool(RX["profit_factor"].search(text)),
        "max_drawdown": has("max_drawdown") or bool(RX["max_drawdown"].search(text)),
        "oos": oos, "trade_count": n, "real_ticks": bool(RX["real_ticks"].search(text)),
        "evidence_type": ev.split("|")[0], "completeness": rec.get("completeness"),
        "code_captured": bool(rec.get("code_captured")),
        "signal_warning": bool(rec.get("signal_warnings")), "claim_warning": bool(rec.get("claim_warnings")),
    }


MAIN_EVIDENCE = ("claim_only", "backtest_shown", "source_code", "forward_results", "none")


def evidence_buckets(C: list, N: int) -> dict:
    """Corpus evidence_type, with rare free-text labels pooled as 'other'."""
    c = Counter(x["evidence_type"] if x["evidence_type"] in MAIN_EVIDENCE else "other" for x in C)
    return {k: pct(c.get(k, 0), N) for k in MAIN_EVIDENCE + ("other",)}


def pct(k: int, n: int) -> float:
    return round(100.0 * k / n, 2) if n else 0.0


def write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


# ---------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", type=Path, default=DEFAULT_IN)
    ap.add_argument("--sample", type=int, default=50, help="rows in data/schema_sample.csv (0 = skip)")
    ap.add_argument("--snapshot-date", default=date.today().isoformat())
    args = ap.parse_args()

    if not args.input.exists():
        print(f"Input not found: {args.input}\nPlace the corpus at raw/strategies.json (gitignored).", file=sys.stderr)
        return 2

    recs = load(args.input)
    C = [classify(r) for r in recs if isinstance(r, dict)]
    N = len(C)
    if N == 0:
        print("No records.", file=sys.stderr)
        return 2
    OUT.mkdir(exist_ok=True)
    cnt = lambda key: sum(1 for c in C if c[key])

    # family distribution
    fam = Counter(c["family"] for c in C)
    write_csv(OUT / "family_distribution.csv", ["family", "count", "pct"],
              [[f, fam.get(f, 0), pct(fam.get(f, 0), N)] for f in FAMILY_NAMES])

    # indicator crowding (top 20)
    ind = Counter(i for c in C for i in c["indicators"])
    with_any = sum(1 for c in C if c["indicators"])
    write_csv(OUT / "indicator_crowding.csv",
              ["rank", "indicator", "strategies_mentioning", "pct_of_all", "pct_of_indicator_users"],
              [[r, k, v, pct(v, N), pct(v, with_any)] for r, (k, v) in enumerate(ind.most_common(20), 1)])

    # risk-control gaps, overall and by family
    controls = [("hard_stop_loss_documented", "stop_loss"), ("take_profit_documented", "take_profit"),
                ("position_sizing_documented", "position_sizing"), ("grid_mentioned", "grid"),
                ("martingale_mentioned", "martingale"), ("unbounded_grid_martingale_flag", "unbounded_grid_martingale")]
    rows = []
    for group in ["ALL"] + FAMILY_NAMES:
        sub = C if group == "ALL" else [c for c in C if c["family"] == group]
        for label, key in controls:
            k = sum(1 for c in sub if c[key])
            rows.append([group, label, len(sub), k, pct(k, len(sub))])
    write_csv(OUT / "risk_control_gaps.csv", ["family", "control", "n", "count", "pct"], rows)

    # timeframe x asset matrix
    tfs = [t for t, _ in TIMEFRAMES] + ["Multiple", "Unspecified"]
    assets = [a for a, _ in ASSETS] + ["Unspecified"]
    mx = Counter((c["timeframe"], c["asset"]) for c in C)
    write_csv(OUT / "timeframe_asset_matrix.csv", ["timeframe"] + assets + ["total"],
              [[t] + [mx.get((t, a), 0) for a in assets] + [sum(mx.get((t, a), 0) for a in assets)] for t in tfs])

    # headline KPIs
    counted = [c["trade_count"] for c in C if c["trade_count"] is not None]
    summary = {
        "title": "State of Retail Trading Algorithms 2026",
        "publisher": "Prismatic Algos",
        "snapshot_date": args.snapshot_date,
        "n_strategies": N,
        "method": "keyword + structured-field classification of public documentation; see README#methodology",
        "risk_controls_pct": {
            "hard_stop_loss_documented": pct(cnt("stop_loss"), N),
            "hard_stop_loss_missing": pct(N - cnt("stop_loss"), N),
            "take_profit_documented": pct(cnt("take_profit"), N),
            "position_sizing_documented": pct(cnt("position_sizing"), N),
            "grid_or_martingale_mentioned": pct(sum(1 for c in C if c["grid"] or c["martingale"]), N),
            "unbounded_grid_martingale_flag": pct(cnt("unbounded_grid_martingale"), N),
        },
        "evidence_pct": {
            "reports_sharpe": pct(cnt("sharpe"), N),
            "reports_sortino": pct(cnt("sortino"), N),
            "reports_profit_factor": pct(cnt("profit_factor"), N),
            "reports_max_drawdown": pct(cnt("max_drawdown"), N),
            "mentions_out_of_sample_or_walk_forward": pct(cnt("oos"), N),
            "claims_real_tick_backtest": pct(cnt("real_ticks"), N),
            "states_trade_count": pct(len(counted), N),
            f"stated_trade_count_below_{SMALL_SAMPLE}": pct(sum(1 for x in counted if x < SMALL_SAMPLE), N),
            f"stated_trade_count_below_{SMALL_SAMPLE}_pct_of_stated": pct(sum(1 for x in counted if x < SMALL_SAMPLE), len(counted)),
        },
        "evidence_type_pct": evidence_buckets(C, N),
        "specification_pct": {
            "completeness_80_plus": pct(sum(1 for c in C if (c["completeness"] or 0) >= 80), N),
            "completeness_median": sorted((c["completeness"] or 0) for c in C)[N // 2],
            "source_code_captured": pct(cnt("code_captured"), N),
            "entry_signal_warning": pct(cnt("signal_warning"), N),
            "performance_claim_warning": pct(cnt("claim_warning"), N),
        },
        "indicators": {
            "pct_using_any_named_indicator": pct(with_any, N),
            "top_5": [k for k, _ in ind.most_common(5)],
        },
        "families_pct": {f: pct(fam.get(f, 0), N) for f in FAMILY_NAMES},
    }
    (OUT / "summary_metrics.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    # metadata-only schema sample: salted hash id + flags, never text
    if args.sample:
        step = max(1, N // args.sample)
        cols = ["row_id", "family", "timeframe", "asset", "n_indicators", "stop_loss", "take_profit",
                "position_sizing", "unbounded_grid_martingale", "sharpe", "oos", "trade_count_bucket"]
        sample = []
        for i in range(0, N, step)[: args.sample]:
            c = C[i]
            tc = c["trade_count"]
            bucket = "unstated" if tc is None else "<100" if tc < 100 else "100-999" if tc < 1000 else "1000+"
            rid = hashlib.sha256(f"sorta-2026:{i}".encode()).hexdigest()[:12]
            sample.append([rid, c["family"], c["timeframe"], c["asset"], len(c["indicators"]),
                           int(c["stop_loss"]), int(c["take_profit"]), int(c["position_sizing"]),
                           int(c["unbounded_grid_martingale"]), int(c["sharpe"]), int(c["oos"]), bucket])
        write_csv(OUT / "schema_sample.csv", cols, sample)

    print(f"OK: {N} strategies -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
