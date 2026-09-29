# GC-XAU CAUSAL BROAD — RECOVERY / BACKLOG LAB023–LAB037

Updated: 2026-09-29

## Current research candidate

Frozen downstream architecture currently supported by the historical research lineage:

- Confidence gate: BUY >= 0.60; SELL >= 0.75.
- Entry: wait +0.50 ATR favorable response within 10m, then wait 0.50 ATR retracement within next 10m.
- ONE POSITION TOTAL.
- No universal circuit breaker.
- BUY: SL = 1.5 ATR; after +3R activate lock +1R; runner until max hold 120m.
- SELL: SL = 2.0 ATR; after +1.5R activate lock +0.5R; runner until max hold 120m.
- Risk is fixed in money/R; changing ATR stop implies inverse lot-size adjustment.
- Do not fine-tune decimal thresholds on the same sample.

## LAB023 — Circuit-breaker robustness

Frozen 2 consecutive realized losses -> pause 12h:
- Baseline SIDE_SPECIFIC: N=228, PF=2.0210, EV=+0.6819R, Sum=+155.481R, MaxDD=15.961R.
- Breaker: N=183, PF=2.1758, EV=+0.7757R, Sum=+141.952R, MaxDD=12.924R.
- Blocked trades had net +13.529R expectancy; Jan-2025 was harmed heavily.
Decision: REJECT universal 2L->12h breaker.

## LAB024 — Symmetric confidence expansion

Threshold 0.75: N=228, PF=2.021, EV=+0.682R, Sum=+155.48R, DD=15.96R.
0.70: N=350, PF=1.675, EV=+0.468R, Sum=+163.73R, DD=21.85R.
0.65: N=505, PF=1.483, EV=+0.348R, Sum=+175.67R, DD=22.83R.
0.60: N=706, PF=1.385, EV=+0.282R, Sum=+199.08R, DD=34.10R.
SELL degrades strongly when confidence is loosened; lower-confidence BUY remains much stronger.
Decision: do not use symmetric relaxation.

## LAB025 — Asymmetric confidence exact chronology

BUY >=0.60, SELL >=0.75.
N=487, WR=26.9%, PF=1.46, EV=+0.337R, Sum=+164.11R, MaxDD about 27R.
This motivated execution precision rather than further confidence loosening.

## LAB026 — Entry precision

Frozen asymmetric confidence. Coarse execution comparison:
- CONTROL: N487, WR26.9%, PF1.456, EV+0.337R, Sum164.11R, DD27.60R.
- RETEST025: N477, WR28.9%, PF1.579, EV+0.417R, Sum198.72R, DD25.95R.
- RETEST050: N466, WR31.5%, PF1.753, EV+0.522R, Sum243.13R, DD18.87R.
- HOLD2_CONT: reject.
- BREAK1_RETEST025: weaker than RETEST050.
Decision: freeze RETEST050 coarse candidate; no 0.40/0.45/0.55 tuning.

## LAB027–LAB028 — SELL exits

Raw structural SELL target frequently violates production TP>=1.5R requirement.

LAB028 same 90 SELL:
- Fixed 1.5R: WR51.11%, PF1.5085, EV+0.2544R, Sum+22.90R, DD5.69R.
- Fixed 2R: WR43.33%, PF1.4770, EV+0.2766R, Sum+24.90R, DD8.19R.
- Structure >=1.5R: WR43.33%, PF1.7249, EV+0.4204R, Sum+37.83R, DD6.14R.

## LAB029 — Full BUY+SELL portfolio exits

ONE POSITION TOTAL:
- BUY current + SELL fixed1.5: N470, WR35.32%, PF1.6807, EV+0.4467R, Sum+209.93R, DD15.04R.
- BUY current + SELL structure-min1.5: N468, WR33.76%, PF1.7135, EV+0.4795R, Sum+224.41R, DD16.88R.

## LAB030 — BUY exit models

Same 376 BUY entries:
- Current +3R -> lock +1R -> runner120: WR31.38%, PF1.7123, EV+0.4950R, Sum+186.13R.
- Fixed1.5R: WR48.67%, PF1.3733, EV+0.1952R, Sum+73.39R.
- Fixed2R: WR40.96%, PF1.3330, EV+0.2004R, Sum+75.35R.
Large BUY runners are a major expectancy source. +3R is a lock trigger, not TP.

## LAB031 — SELL protected runner

Same 90 SELL:
- TP1.5R: WR51.11%, PF1.5085, EV+0.2544R, Sum+22.90R.
- +1.5R -> BE -> runner: WR23.33%, PF1.9109, EV+0.4617R, Sum+41.55R.
- +1.5R -> lock +0.5R -> runner: WR51.11%, PF1.6835, EV+0.3420R, Sum+30.78R.
Decision: protected SELL runner is preferable candidate to hard TP1.5.

## LAB032 — Combined protected-runner portfolio

BUY 3R->lock1; SELL 1.5R->lock0.5; both SL2 ATR:
- 768 entry candidates; 467 executed; 301 blocked by ONE POSITION TOTAL.
- Portfolio: WR35.33%, PF1.7096, EV+0.4655R, Sum+217.379R, MaxDD14.9345R, max loss streak13.
- BUY: N375, PF1.7190, EV+0.4991R.
- SELL: N92, WR51.09%, PF1.6564, EV+0.3286R.

## LAB033 — Winner concentration stress

LAB032:
- Baseline PF1.7096, EV+0.4655R.
- Remove top1% (5 trades): PF1.3640, EV+0.2414R, Sum+111.50R.
- Remove top5%: PF0.8161, EV-0.1272R.
- Remove top10%: PF0.4635, EV-0.3913R.
- Remove top1 winner: PF1.6224.
- Remove top3: PF1.4681.
- Remove top5: PF1.3640.
- Remove top10: PF1.1886, EV+0.1264R.
Top winner = 5.1% of gross profit; top10 winners = 30.5%; top5% trades = 52.3%.
Interpretation: not dependent on one jackpot, but architecture is intentionally fat-tail/runner-dependent.

## LAB034 — Coarse SL audit

Full portfolio, same architecture, universal SL:
- SL1.5 ATR: N500, WR35.8%, PF1.8942, EV+0.5875R, Sum+293.74R, DD27.15R.
- SL2 ATR: N467, WR35.3%, PF1.7096, EV+0.4655R, Sum+217.38R, DD14.93R.
- SL3 ATR: N435, WR39.8%, PF1.6122, EV+0.3649R, Sum+158.72R, DD16.61R.
Side decomposition indicated BUY prefers 1.5 ATR; SELL prefers 2 ATR.
Do not interpret higher WR at SL3 as higher quality: PF/EV fell.

## LAB035 — Asymmetric SL candidate

BUY SL1.5 ATR; SELL SL2 ATR; frozen protected-runner exits; ONE POSITION TOTAL.
- 768 candidates; 499 executed; 269 blocked.
- Portfolio: WR36.67%, PF1.9302, EV+0.6028R, Sum+300.802R, MaxDD17.7346R, max loss streak13.
- BUY: N406, WR33.25%, PF1.9739, EV+0.6653R, Sum+270.095R.
- SELL: N93, WR51.61%, PF1.6668, EV+0.3302R, Sum+30.707R.
Winner stress:
- remove top1%: PF1.5351, EV+0.3503R, Sum+173.04R.
- remove top5%: PF0.8446, EV-0.1060R.
- remove top10%: PF0.4303, EV-0.4103R.
Current leading historical candidate = LAB035 architecture.

Monthly LAB035:
2025-01 N69 PF1.63 EV+0.499 Sum+34.41
2025-02 N15 PF3.88 EV+1.180 Sum+17.70
2025-03 N66 PF2.42 EV+0.926 Sum+61.12
2025-04 N10 PF0.47 EV-0.323 Sum-3.23
2025-05 N68 PF1.34 EV+0.205 Sum+13.94
2025-06 N1 EV-1.023
2025-07 N93 PF2.54 EV+0.969 Sum+90.12
2025-10 N12 PF2.12 EV+0.766 Sum+9.19
2025-11 N71 PF1.11 EV+0.075 Sum+5.34
2026-02 N10 PF4.20 EV+2.618 Sum+26.18
2026-04 N5 PF2.54 EV+0.943 Sum+4.72
2026-05 N41 PF2.49 EV+0.743 Sum+30.47
2026-06 N7 PF0.08 EV-0.809 Sum-5.66
2026-07 N31 PF1.86 EV+0.566 Sum+17.54

## LAB036 — Weak May/Nov vs strong Mar/Jul

GOOD Mar+Jul: N159, WR37.74%, PF2.4927, EV+0.9512R, Sum+151.23R, mean ATR0.9033, confidence0.7431.
WEAK May+Nov: N139, WR38.13%, PF1.2191, EV+0.1387R, Sum+19.28R, mean ATR1.8853, confidence0.7377.
WR, confidence and SL rate were nearly unchanged; absolute ATR roughly doubled.

Critical side asymmetry:
- GOOD BUY: N142 PF2.7361 EV+1.1136R.
- WEAK BUY: N113 PF1.0456 EV+0.0310R.
- GOOD SELL: N17 PF0.326 EV-0.4057R.
- WEAK SELL: N26 PF2.4017 EV+0.6069R.

Legs GOOD vs WEAK:
- BASE1 PF2.94 -> 0.59 (main degradation).
- DOM2 PF2.34 -> 1.38.
- DOM_CONT PF3.93 -> 1.40.
- MIX2 PF1.18 -> 2.33.
Do NOT install a global MaxATR filter: high-volatility regime can be good for SELL/MIX2.

## LAB037 — BUY ATR regime x SL x LEG

Descriptive audit only. HIGH ATR = upper third of contemporaneous BUY ATR, threshold >1.507619. This threshold is post-hoc and MUST NOT be promoted to production filter without independent validation.

Overall BUY:
HIGH ATR:
- SL1.5: N141 PF1.8246 EV+0.5147R.
- SL2: N125 PF1.7234 EV+0.4592R.
- SL3: N123 PF1.4559 EV+0.2726R.
LOW/NORMAL:
- SL1.5: N265 PF2.0433 EV+0.7454R.
- SL2: N250 PF1.7171 EV+0.5190R.
- SL3: N221 PF1.6979 EV+0.4474R.

HIGH ATR legs:
- BASE1 SL1.5 PF1.203 EV+0.146; SL2 PF1.239 EV+0.168; SL3 PF0.915 EV-0.054.
- DOM2 SL1.5 PF1.890 EV+0.538.
- DOM_CONT SL1.5 PF6.604 EV+2.294 (N10 only).
- MIX2 SL1.5 PF1.750 EV+0.434.

Conclusion:
1. Hypothesis "HIGH ATR requires wider BUY stop" is NOT supported.
2. BUY SL1.5 remains strongest overall in both ATR regimes.
3. HIGH ATR does not kill BUY generally; weakness is concentrated in BASE1.
4. Widening BASE1 to 3 ATR makes it worse, so BASE1 degradation is not simply stop noise.
5. Do not disable BASE1 at ATR>1.508: threshold was discovered post-hoc.
6. Current next research target is causal validation of BASE1 regime degradation without threshold mining.

## Critical methodology / anti-overclaim rules

- LAB008 onward confidence universe originates from v034-opened OOS signals, NOT all 111,172 raw Broad signals.
- Applying confidence directly to all raw Broad signals would be a distribution shift. Final EA must either retain research-lineage upstream selection or confidence must be recomputed/revalidated on raw Broad.
- Historical XAU execution is M1 proxy, not tick chronology. Same-bar intrabar order is unknown; conservative stop precedence was used.
- H1 structural data used UTC-resampled proxy, not guaranteed broker H1 boundaries.
- Costs are proxy/calibrated, not broker-specific live spread/slippage/commission.
- LAB020 onward is not genuinely untouched temporal OOS; many later LABs are discovery/robustness on the same historical universe.
- Winner stress confirms fat-tail dependence. Protecting runners is essential.
- ONE POSITION TOTAL must always be recomputed when exits/stops change.
- Real prop daily DD requires floating equity chronology, not realized-R-only DD.
- No fine decimal tuning on this sample.
- Before final EA code, broker/prop execution specifications are required.

## Backlog / next steps

1. Preserve LAB035 as current historical candidate; do not mutate it silently.
2. Validate BASE1 degradation causally without using the post-hoc ATR 1.508 threshold as a production rule.
3. Run execution stress on frozen LAB035: spread/slippage deterioration, delayed entry, missed signals.
4. Obtain genuinely untouched forward/demo evidence.
5. Resolve confidence lineage before final EA: old v034-selected universe vs recomputation on all raw Broad signals.
6. For final EA: persist causal confidence history across restart; score using prior history before appending current signal.
7. Implement broker-side protective SL modification for BUY +3R->lock1 and SELL +1.5R->lock0.5; M1 research cannot prove exact intrabar live behavior.
8. Keep ONE POSITION TOTAL.
9. No universal loss-streak circuit breaker.
10. Do not add MaxATR or BASE1-high-ATR filters from LAB036/037 without independent validation.
