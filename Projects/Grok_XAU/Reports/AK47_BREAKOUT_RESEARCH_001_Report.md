# AK47_BREAKOUT_RESEARCH_001 — Formal Report

**Date:** 2026-07-25  
**Status:** FORMAL COMPLETED  
**Verdict:** **NO-GO**  
**Scope:** non-tight AK47 OCO breakout geometry using `SL/TP/padding/session` with `OFF` or `BE-only`; tight trailing was excluded by specification.

## 1. Data provenance

- Dataset: `XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv`
- CSV SHA256: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`
- ZIP SHA256: `556aa47fc3daaf47b678226a9564106989db9fd4579698bf38d4429ab547b1d0`
- Metadata SHA256: `5cc2870a648fcac9bfb7b7180364bb26552620034e478bb3d90d2e5c17620720`
- Rows: `1,454,538`
- Coverage: `2022-06-01 01:05` through `2026-07-23 23:49`
- Duplicate timestamps: `0`
- Invalid Bid/Ask OHLC: `0`
- Non-positive spreads: `0`
- Median spread: `18 points`
- Spread p95: `51.91 points`
- Commission: `$5 round-turn per lot`
- Risk: fixed `$500` per trade, no compounding

The M1 feed was aggregated directly from tester Bid/Ask ticks. M5 reconstruction was not used.

## 2. Frozen search family

The original estimated 756 combinations did not include the chart timeframe axis. The preregistration therefore evaluated:

- `756` configurations on M15;
- `756` configurations on H1;
- **1,512 total candidates**.

Axes:

- SL: `1500, 2000, 2500, 3000, 3700, 4500, 6000 points`;
- RR: `1.0, 1.5, 2.0, 2.6, 3.5, 5.0`;
- padding: `2, 5, 8 points`;
- exit: `OFF` or `BE-only 125/30`;
- session: `08–18`, `10–14`, `00–24`;
- OCO enabled;
- no trailing;
- no streak scaling.

## 3. Walk-forward results

Exactly one candidate was selected from each rolling 12-month train window and tested on the following unseen six months.

| Split | Config | TF | SL | RR | Pad | Exit | Session | Test N | Test EV | Test MaxDD |
|---|---|---|---:|---:|---:|---|---|---:|---:|---:|
| WF1 | AKBRK_1373 | H1 | 4500 | 3.5 | 2 | BE_V19_125_30 | 10-14 | 75 | -0.0283R | 2.86% |
| WF2 | AKBRK_0883 | H1 | 2000 | 1.5 | 2 | OFF | 08-18 | 65 | +0.2401R | 3.52% |
| WF3 | AKBRK_0676 | M15 | 6000 | 1.5 | 5 | BE_V19_125_30 | 08-18 | 238 | +0.0181R | 0.90% |
| WF4 | AKBRK_0837 | H1 | 1500 | 3.5 | 5 | OFF | 00-24 | 170 | +0.1486R | 10.76% |
| WF5 | AKBRK_0932 | H1 | 2000 | 2.6 | 8 | OFF | 10-14 | 99 | +0.1611R | 3.83% |
| WF6 | AKBRK_1488 | H1 | 6000 | 3.5 | 5 | BE_V19_125_30 | 00-24 | 1020 | -0.0057R | 7.48% |

Aggregate selected OOS:

- N: **1,667**
- EV net: **+0.03191R**
- total: **+53.188R / $26,594.00**
- PF: **1.199**
- MaxDD: **10.76%**
- positive test splits: **4/6**
- negative test splits: **2/6**
- unique selected configurations: **6/6**

The six train windows selected six different geometries. This is strong parameter-instability evidence.

## 4. Economic gates

| Gate | Result |
|---|---|
| Aggregate N ≥90 | PASS — `1667` |
| Aggregate EV >0 | PASS — `+0.03191R` |
| ≤1 negative test split | **FAIL — `2`** |
| MaxDD ≤10% | **FAIL — `10.76%`** |
| Family-wise permutation | **FAIL** |

Even before the permutation verdict, the system does not satisfy the preregistered stability and prop-compatible drawdown gates.

## 5. Family-wise multiple-comparisons control

The complete 1,512-candidate family was rerun on shuffled trading-day price blocks.

### WF1

- real best Calmar-like: `54.6051`
- permutation mean: `14.6557`
- permutation p95: `44.6338`
- permutations ≥ real: `3/250`
- empirical p: `0.0159`
- result: **PASS**

### WF2

- real best Calmar-like: `4.9348`
- permutation mean: `14.1484`
- permutation median: `8.8527`
- permutation p95: `41.8556`
- permutations ≥ real: `228/250`
- empirical p: `0.9124`
- result: **FAIL**

The real WF2 winner is weaker than the typical best configuration found after shuffling. It is therefore consistent with “best of 1,512” selection noise.

The preregistered execution lock states that failure of any train split stops the family. Permutations for WF3–WF6 were therefore not run after the decisive WF2 failure.

## 6. Descriptive diagnostics

These are descriptive only and do not reopen the verdict:

- BUY OOS EV: `+0.06793R`
- SELL OOS EV: `-0.01433R`
- negative OOS months: `13`
- 2026 OOS EV: `-0.00481R`

SELL cannot be removed post-hoc. A BUY-only hypothesis would require a new specification and independent data.

## 7. Sealed tail

The WF6-selected geometry was evaluated on `2026-06-01..2026-07-23`:

- N: `254`
- EV: `-0.02430R`
- PF: `0.403`
- return: `-3.09%`
- MaxDD: `3.10%`

The sealed tail is negative and supports the NO-GO decision, but it was not used to create the verdict.

## 8. Regime and ML stages

The manual regime stage and ML addendum were **not run**.

Reason: the addendum explicitly permits ML only after the base geometry returns GO or REGIME. The family-wise failure produces base **NO-GO**, so ML is not allowed to rescue the entry class.

## 9. Final interpretation

### Verdict: **NO-GO**

The broad non-tight breakout class tested here does not demonstrate a robust, portable edge after:

- real Bid/Ask spread;
- commission;
- chronological walk-forward;
- drawdown gates;
- family-wise multiple-comparisons control.

This does **not** falsify the separate V15 tight-trailing hypothesis. V15's 3-point trailing was excluded from this specification because it requires exact tick-native execution testing. The result falsifies the economically wider `SL/TP/padding/session + OFF/BE-only` geometry as a standalone foundation for ML or further parameter tuning.

No EA implementation, risk increase, regime filter, or ONNX model is authorized from this research.
