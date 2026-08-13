# SELL_CORE_002 — B3 × M15 FAILED_BULL_RESPONSE × FVG LOCATION

## Verdict

**PARTIAL / MECHANISM FOUND, FVG REJECTED.**

Frozen common outcome: SELL, SL = 1.5 × completed H1 ATR14, no TP, 48h time exit, $27.5/BTC cost proxy. SELL_B3 = canonical H4 Supertrend age 27–50.

Failed-response events were taken from the already frozen `BTC_LAB015_FAILED_RECOVERY_BREAKDOWN_SELL` ledger. No new failure detector was invented. FVG location was a mature classical bearish M15 FVG first-touch (age 11–60) during the LAB015 recovery leg from breakdown to trigger.

## Main layering

| Branch | N | EV_R | PF | EV_pct | P(EV>0) |
|---|---:|---:|---:|---:|---:|
| B3 onset | 85 | +0.258R | 1.31 | +0.216% | 76.4% |
| B3 + mature bearish FVG | 74 | -0.115R | 0.87 | -0.042% | 31.5% |
| B3 + failed response | 80 | +0.305R | 1.38 | +0.312% | 81.4% |
| B3 + failed response + FVG | 10 | -0.426R | 0.49 | -0.185% | 12.3% |

### FVG conclusion

The FVG overlay is rejected in this architecture. It is negative by itself and turns the failed-response subset negative. Do not require a mature bearish FVG as an AND-gate for SELL_B3.

### Failed-response timing conclusion

For the same 80 B3 episodes selected by a failed response:

- entry at the failed-response event: +0.305R;
- entry at B3 onset in those same episodes: +0.339R;
- timing delta: **-0.034R**.

Therefore the failed-response timestamp itself has no demonstrated timing alpha. At most, the occurrence/mechanics can be an episode/phase marker.

## Regime migration

`B3_FAILED_RESPONSE` by year:
- 2024: N31, -0.450R, PF 0.51;
- 2025: N31, +0.263R, PF 1.34;
- 2026: N18, +1.680R, PF 3.63.

Thus the aggregate positive result is not stationary 3/3. It strengthens sharply in the recent regime.

## Existing LAB015 components — descriptive only

The selected first B3 failed-response events carry overlapping LAB015 tags:

- F1 `LEVEL_REJECTION_BREAKDOWN`: N9, +0.258R, PF 1.36;
- F2 `CLOSE_RECLAIM_FAILURE`: N58, +0.499R, PF 1.63;
- F3 `LOWER_HIGH_BREAKDOWN`: N60, +0.573R, PF 1.76.

Year audit:
- F2: 2024 -0.497R; 2025 +0.298R; 2026 +2.858R.
- F3: 2024 -0.277R; 2025 +0.678R; 2026 +1.866R.

F2 and F3 overlap heavily (44 events contain both). Their intersection has aggregate EV +0.742R, but 2024 remains negative, so this is **post-hoc descriptive evidence only**, not a frozen rule.

## Practical architecture implication

Current evidence does **not** support:

`B3 + failed response + bearish FVG -> SELL`

The evidence supports a narrower next question:

> Is the **occurrence** of a specific failed-recovery component (`F2` or `F3`) a causal selector of better B3 SELL episodes, even if its exact timestamp is not special?

That requires a separately preregistered same-state/risk-set occurrence test before any component enters the BTC core.
