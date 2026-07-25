# AK47-V19-ORACLE-001 — 42-month oracle and challenge-window control

**Date:** 2026-07-25  
**Frozen specification:** `AK47_V19_ORACLE_TZ-2026-07-25.md`  
**Operational verdict:** **REGIME / NO SCALE**  
**Research status:** **EDGE POSITIVE, FINAL GO/REGIME LABEL BLOCKED BY EXECUTION PARITY**

## 1. Provenance

- Frozen TZ SHA256: `7698c1279942a0b3890d16f550725aaedf797343e911b6854a3bb887f298bbc8`
- M5 tester-stream SHA256: `40175d5d73fbbe01d26fd1813d1bc299854ef535c328fa1fdd1b883f90509ae4`
- Oracle SHA256: `1bafba47831fac92a28d9edab1ba0f4791e0a0f25b1676baba5ae89950a58cb7`
- M5 rows: `290,893`
- Coverage: `2022-06-01 01:05 .. 2026-07-23 23:40`
- Commission: `$5.00 round-turn per lot`
- Starting balance: `$100,000`

The exact `AK-47_V19_FILTER.mq5` source was not present in the available files or ResearchOS.
The frozen TZ extraction is therefore the canonical engine description. M15 and H1 were run separately as required.

## 2. Execution-integrity limitation

The strategy uses trailing after only `10` points with a `5`-point step, but the fixture contains M5 OHLC, not tick order.
The frozen TZ does not specify the intrabar OHLC path needed to reproduce this trailing exactly.

Two deterministic integrity paths were therefore run without changing any trading parameter:

- `primary`: bullish `O-L-H-C`, bearish `O-H-L-C`
- `mirror`: bullish `O-H-L-C`, bearish `O-L-H-C`

A single formal GO/REGIME label is not robust because the challenge permutation gate changes across these two valid M5 paths.

## 3. Main results

| TF | Path | N | Full-risk N | EV base-R | PF | Final balance | Reduced-risk share | 14d pass-rate | Permutation p95 | Rule label |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| M15 | primary | 1071 | 1009 | +0.150R | 4.55 | $495,667 | 5.79% | 5.52% | 4.85% | REGIME |
| M15 | mirror | 1064 | 1001 | +0.143R | 4.38 | $456,040 | 5.92% | 4.31% | 4.37% | GO |
| H1 | primary | 990 | 946 | +0.105R | 4.51 | $280,872 | 4.44% | 0.40% | 0.00% | REGIME |
| H1 | mirror | 989 | 943 | +0.100R | 4.17 | $268,381 | 4.65% | 0.00% | 0.00% | GO |

## 4. Stable conclusions

1. **HOT-STREAK-ARTIFACT is rejected as the primary explanation.**  
   EV is positive under both TFs and both path conventions:
   - M15: `+0.143R .. +0.150R`
   - H1: `+0.100R .. +0.105R`

2. **Survivor mode does not create an illusory profit through microscopic risk.**  
   Full-risk trades:
   - M15: `1,001 .. 1,009`
   - H1: `943 .. 946`

   Only about `4.4% .. 5.9%` of entries use reduced risk.

3. **The passed two-week challenge is plausible mainly under M15.**
   - M15 pass-rate: `4.31% .. 5.52%`, approximately one passing window per `18–23` rolling windows.
   - H1 pass-rate: `0.00% .. 0.40%`.

4. **The strongest M15 challenge cluster is 2026-01-22 through 2026-02-16.**
   Individual overlapping windows reached roughly `+28% .. +38%` in the primary path and `+31% .. +35%` in the mirror path.

5. **H1 passing windows exist only in the primary path and cluster around 2026-03-31 through 2026-04-20.**
   They disappear under the mirror path, showing execution sensitivity.

## 5. Why the specific challenge could pass

If the original EA was attached to **M15** and the challenge occurred in late January or early February 2026,
the passed challenge falls directly inside the strongest 14-day cluster in the full sample.
That is consistent with a real positive edge plus an unusually favorable volatility sequence.

If the original EA was attached to **H1**, a two-week pass is much harder to reproduce:
only `6/1,489` primary-path windows pass, and `0/1,489` mirror-path windows pass.

Without the exact chart TF, challenge dates and original V19 source, the specific historical pass cannot be matched one-to-one.

## 6. Decision

- Do not classify the bot as NO-GO.
- Do not classify it as pure HOT-STREAK-ARTIFACT.
- Do not authorize live scaling from this bar-level oracle.
- Operational classification: **REGIME / NO SCALE** until exact MT5 parity resolves trailing and confirms the original timeframe.
- The next valid parity input is the exact `AK-47_V19_FILTER.mq5` source plus the approximate passed-challenge dates.
