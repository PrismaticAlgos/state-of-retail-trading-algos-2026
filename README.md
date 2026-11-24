# State of Retail Trading Algorithms 2026

Aggregate statistics from **Prismatic Algos'** review of **16,277 publicly documented retail trading algorithms** (expert advisors, bots, indicators-turned-strategies and scripts), distilled from 129,520 crawled public documents. Snapshot: **2026-11-14**.

The review measures what public documentation actually specifies: which strategy families dominate, which indicators are most crowded, how often basic risk controls are written down, and how often the evidence behind a strategy meets basic standards of statistical rigor.

This repository publishes **aggregate counts and percentages only**. It contains no strategy source code, no vendor text, no names or URLs of individual products, and no proprietary Prismatic Algos trading logic.

> **Cite as:** Prismatic Algos (2026). *State of Retail Trading Algorithms 2026* [Data set], snapshot 2026-11-14. https://prismaticalgos.com. Licensed CC BY 4.0. Machine-readable citation: [`CITATION.cff`](CITATION.cff).

## Headline findings

| Finding | Value |
|---|---|
| Strategies analysed | **16,277** |
| No hard stop-loss documented | **32.8%** (5,342) |
| No take-profit documented | **42.3%** |
| No position-sizing rule documented | **34.4%** |
| Grid or martingale mechanics | **14.1%** |
| Grid/martingale with **no** stop-loss and no documented cap (unbounded) | **5.4%** of all; **38.3%** of the grid/martingale family |
| Evidence is a bare claim (no backtest, code or forward results) | **40.0%** |
| States a profit factor / max drawdown | 20.5% / 21.6% |
| States a trade count | 18.3%, and 15.3% of those report **fewer than 100 trades** |
| Mentions out-of-sample, walk-forward or forward testing | **14.9%** |
| Reports a Sharpe ratio | **0.05%** (8 strategies) |
| Fully specified (completeness score ≥ 80/100) | **8.3%**; median score 50 |
| Most crowded indicators | EMA (20.6%), RSI (16.0%), ATR (15.7%), ADX (7.6%), Bollinger Bands (7.5%) |
| Largest families | Trend Following 27.7%, Mean Reversion 21.2%, Trade & Execution Management 9.8% |

All figures are percentages of all 16,277 strategies unless stated otherwise. Source tables are in [`data/`](data/).

## Files

| File | Contents |
|---|---|
| [`data/summary_metrics.json`](data/summary_metrics.json) | Headline KPIs: sample size, risk controls, evidence, specification quality, family shares |
| [`data/family_distribution.csv`](data/family_distribution.csv) | Count and share for each of the 12 strategy families plus Unclassified |
| [`data/indicator_crowding.csv`](data/indicator_crowding.csv) | Top 20 technical indicators by number of strategies using them |
| [`data/risk_control_gaps.csv`](data/risk_control_gaps.csv) | Stop-loss, take-profit, position-sizing and grid/martingale flags, overall and per family |
| [`data/timeframe_asset_matrix.csv`](data/timeframe_asset_matrix.csv) | Strategy counts by primary timeframe × asset class |
| [`data/schema_sample.csv`](data/schema_sample.csv) | 50 anonymised rows of classification flags only (hashed IDs, no text) showing how records are scored |
| [`scripts/generate_aggregates.py`](scripts/generate_aggregates.py) | The exact classification and aggregation code (Python standard library only) |
| [`datapackage.json`](datapackage.json) | [Frictionless Data](https://frictionlessdata.io/) descriptor with column schemas |

## Methodology

**Corpus.** A continuously running pipeline collects public strategy documentation (marketplace listings, public code repositories, video transcripts, forums and quantitative-finance sites). It classifies each document against a 12-family taxonomy and uses a local language model to turn the prose into a structured specification: indicators, entry and exit rules, stop-loss, take-profit, position sizing, timeframes, symbols and any claimed performance metrics. This release aggregates the 2026-11-14 snapshot: 16,277 distilled strategies from 129,520 crawled documents. The underlying documents are third-party content and are not redistributed.

**Families.** Each strategy has one primary family: Trend Following & Directional, Mean Reversion & Counter-Trend, Grid/Martingale & Averaging, Scalping & Short-Horizon, Price Action & Market Structure, Time/Session & Seasonality, Volatility-Based, Carry/Swap & Fundamental, Statistical/Quantitative & ML, Risk/Money Management & Portfolio Overlays, Trade & Execution Management, and Confluence & Multi-Timeframe. Strategies the classifier could not place are Unclassified (10.2%).

**Risk controls.** A control counts as *documented* when the specification field holds a real value (for example "50 pips", "ATR-based" or "previous swing low"). Placeholders such as "not specified", "n/a" or "none" count as missing. A strategy is flagged *unbounded grid/martingale* when it uses grid or martingale mechanics, documents no stop-loss, and mentions no cap (maximum orders, basket stop or equity stop).

**Evidence.** The evidence type is the strongest kind of support the source offers: a bare claim, a backtest shown, source code, or forward/live results. Profit factor, drawdown and trade count come from the extracted claimed-metrics fields. Sharpe, Sortino, out-of-sample and real-tick mentions come from the full specification text. **All performance figures are the sources' own unverified claims.** Nothing in this dataset was independently backtested for this release.

**Indicators.** Indicator names are normalised (for example "Exponential Moving Average" becomes EMA) and counted once per strategy. A strategy can use several.

**Limitations.**
- These are measurements of *documentation*, not of trading performance. A stop-loss that exists in code but is never described counts as missing.
- Specifications are machine-extracted. Extraction can miss details that the source states, so the evidence-rigor percentages (Sharpe especially) are best read as lower bounds.
- The corpus is weighted toward MetaTrader-style retail products and grows with every crawl, so later snapshots will differ.
- Timeframe is the first one a strategy lists. "Multiple" means several distinct timeframes are listed.

## Reproducing

```bash
# Place the corpus at raw/strategies.json (gitignored; never committed), then:
python scripts/generate_aggregates.py --snapshot-date 2026-11-14
python scripts/generate_aggregates.py --help
```

The script reads the structured corpus format described above. For any other JSON list of strategy descriptions it falls back to keyword classification.

## License

Data and documentation: [CC BY 4.0](LICENSE). Reuse is free, including commercially, **with attribution and a link to [PrismaticAlgos.com](https://prismaticalgos.com)**.
