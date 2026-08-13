# SELL_CORE_006 — CORRECTION_EPISODE → FAILED_ATTACK → STRUCTURE_BREAK

## Canonical run
Use **006B lifecycle-safe**. 006A is invalid because accepted H1 attack highs could be immediately reused and pivots formed before the current H4-bear episode could leak into the correction state.

006B fixes only lifecycle/causality; no thresholds or hypothesis changed.

## Census
- correction episodes started: 371
- failed attack events: 42
- completed failed-attack → later structure-break sequences: 13
- attack attempts: 153
- accepted attacks: 111
- invalidated failed attacks: 29
- unarmed support breaks: 71
- one SELL maximum per correction episode

This is a major compression versus SELL_CORE_004/005 and is evidence that the sequence state-machine is modeling a rarer episode rather than repeated snapshot signals.

## Primary structure-break execution
Common SELL outcome: next M1 open, SL 1.5×completed H1 ATR14, no TP, 48h primary / 72h sensitivity, $27.5/BTC cost proxy.

- 48h: N=13, EV +0.810R, PF 2.01, EV price +0.234%; cluster CI [-1.037,+3.388], P(EV_R>0)=75.6%.
- 72h: N=13, EV +0.134R, PF 1.17, EV price -0.176%; cluster CI [-1.037,+1.770], P(EV_R>0)=61.8%.

Yearly 48h:
- 2024: N3, -1.039R
- 2025: N8, +0.225R
- 2026: N2, +5.923R

Therefore the preregistered primary does **NOT PASS**: sample is tiny, transfer is not stable, price-space 72h is negative, and the result is carried heavily by two 2026 observations.

## Does waiting for structure break improve timing?
On the exact same 13 completed sequences:
- 48h: structure break +0.810R vs failed attack +0.822R, delta -0.012R; no improvement.
- 72h: structure break +0.134R vs failed attack +0.336R, delta -0.202R; CI [-0.562,-0.0005], P(delta>0)=1.7%.

Price-space timing is also worse after waiting for the break.

Thus **the structure break is not timing alpha**. It is too late in this formulation.

Important: the failed-attack +0.822R number above is conditional on episodes that later completed a structure break, so it contains future conditioning and cannot be promoted as a standalone tradable rule. The correct next causal question is to test all 42 failed-attack occurrences, without knowing whether a later structure break will happen.

## Market-clock diagnostics only
At structure break, tiny post-hoc cells:
- B1 N1: -1.039R
- B2 N5: -1.044R
- B3 N4: +2.871R
- B4 N3: +1.769R

Do not promote B3/B4 from these Ns.

## Verdict
**SELL_CORE_006 = FAIL as a final entry rule, PASS as a representation upgrade.**

The sequence/state-machine successfully collapses hundreds of snapshot rejections into a small number of coherent correction episodes, which is much closer to the visual concept. But the final `break last HL` confirmation arrives too late and does not improve timing. The next causal test should isolate `FAILED_ATTACK occurrence` across all 42 events and compare it against matched same-correction controls, without conditioning on future structure break.
