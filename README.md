# State of Retail Trading Algorithms 2026

Aggregate statistics from **Prismatic Algos'** review of **12,715 publicly documented retail trading algorithms** (expert advisors, bots and scripts). The review measures what the public documentation says: which strategy families dominate, which indicators are most crowded, how often basic risk controls are documented, and how often the evidence meets simple standards of statistical rigor.

This repository publishes **aggregate counts and percentages only**. It contains no strategy source code, no vendor text, no names or URLs of individual products, and no proprietary Prismatic Algos trading logic.

> **Cite as:** Prismatic Algos (2026). *State of Retail Trading Algorithms 2026* [Data set]. https://prismaticalgos.com. Licensed CC BY 4.0. A machine-readable citation is in [`CITATION.cff`](CITATION.cff).

## Headline findings

| Metric | Value | Source |
|---|---|---|
| Strategies analysed | `n_strategies` | `data/summary_metrics.json` |
| Hard stop-loss **not** documented | `risk_controls_pct.hard_stop_loss_missing` % | `data/risk_control_gaps.csv` |
| Position sizing documented | `risk_controls_pct.position_sizing_documented` % | `data/risk_control_gaps.csv` |
| Unbounded grid/martingale flag | `risk_controls_pct.unbounded_grid_martingale_flag` % | `data/risk_control_gaps.csv` |
| Reports a Sharpe ratio | `evidence_pct.reports_sharpe` % | `data/summary_metrics.json` |
| Mentions out-of-sample / walk-forward testing | `evidence_pct.mentions_out_of_sample_or_walk_forward` % | `data/summary_metrics.json` |
| Most crowded indicator | `indicators.top_5[0]` | `data/indicator_crowding.csv` |

<!-- Values are filled from data/summary_metrics.json after each regeneration. -->

## Files

| File | Contents |
|---|---|
| [`data/summary_metrics.json`](data/summary_metrics.json) | Headline KPIs: sample size, risk-control and evidence percentages, family shares |
| [`data/family_distribution.csv`](data/family_distribution.csv) | Count and share for each of 8 strategy families |
| [`data/indicator_crowding.csv`](data/indicator_crowding.csv) | Top 20 named technical indicators by number of strategies mentioning them |
| [`data/risk_control_gaps.csv`](data/risk_control_gaps.csv) | Stop-loss, take-profit, position-sizing and grid/martingale flags, overall and by family |
| [`data/timeframe_asset_matrix.csv`](data/timeframe_asset_matrix.csv) | Strategy counts by primary timeframe × asset class |
| [`data/schema_sample.csv`](data/schema_sample.csv) | 50 anonymised rows of flags only (salted-hash IDs, no text) showing how each record is scored |
| [`scripts/generate_aggregates.py`](scripts/generate_aggregates.py) | The exact classification and aggregation code (standard library only) |
| [`datapackage.json`](datapackage.json) | [Frictionless Data](https://frictionlessdata.io/) descriptor with column schemas |

## Methodology

**Corpus.** 12,715 retail trading algorithms whose descriptions are publicly available (marketplace listings, public code repositories and vendor pages), collected in 2026. Each record is the public documentation of one product. The raw corpus is third-party content and is not redistributed.

**Classification.** Each record is scored from its documented text by the transparent rules in `scripts/generate_aggregates.py`. Where a record already carries a structured field (for example an explicit timeframe), that field takes priority over text matching.

- **Strategy family.** One primary family per strategy, assigned by the first matching rule in this order: Risk/Portfolio Overlays, Trade/Execution Management, Time/Session, Volatility, Mean Reversion, Trend Following, Price Action/Structure. Anything else is Unclassified. Grid and martingale systems count as Mean Reversion.
- **Indicators.** About 30 named indicators are matched independently, so one strategy can count toward several. Shares are given both against all strategies and against strategies that name at least one indicator.
- **Risk controls.** *Hard stop-loss documented* requires a stop-loss mention with no explicit denial such as "no stop loss". *Unbounded grid/martingale* means grid or martingale mechanics with no documented cap (maximum orders, basket stop or equity stop).
- **Evidence.** Mentions of a Sharpe, Sortino, profit-factor or maximum-drawdown figure; out-of-sample, walk-forward or forward-test language; a stated trade count, with counts under 100 flagged as small samples.

**Limitations.** These are measurements of *documentation*, not of live performance. A control that exists in code but goes unmentioned counts as missing. Keyword rules produce some false positives and false negatives; the 50-row schema sample lets readers check how records are scored. Percentages are of the full sample unless a column says otherwise.

## Reproducing

```bash
# Put the corpus at raw/strategies.json (gitignored, never committed), then:
python scripts/generate_aggregates.py            # writes data/*
python scripts/generate_aggregates.py --help     # options
```

The script accepts a JSON list, `{"strategies": [...]}`, or JSON Lines.

## License

Data and documentation are released under [CC BY 4.0](LICENSE). Reuse is free, including commercial reuse, **with attribution and a link to [PrismaticAlgos.com](https://prismaticalgos.com)**.
