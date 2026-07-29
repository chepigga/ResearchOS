# XAU_LSAR_FD_EVENT_STUDY_LAB_001

Events: 119,540

## Primary families
- Liquidity sweep: causal rolling-30 level, 0.10 ATR buffer, same-bar reclaim.
- Failed displacement: FD_W3, FD_W5, FD_W10 frozen definitions.
- Deduplication: 15 minutes.
- Discovery: 2022-06 through 2024-06; WF: 2024-07 through 2025-06.
- Sealed OOS from 2025-07 was not opened.

## Results
| split | event_family | N | mean_EV | matched_null_delta | permutation_p | bootstrap_low | bootstrap_high |
|---|---:|---:|---:|---:|---:|---:|---:|
| DISCOVERY | FD_W10 | 13542 | -0.0167R | -0.0190R | 0.5928 | -0.1454R | +0.1136R |
| DISCOVERY | FD_W3 | 26745 | +0.0143R | +0.0143R | 0.4172 | -0.1262R | +0.1553R |
| DISCOVERY | FD_W5 | 25095 | +0.0323R | +0.0311R | 0.3253 | -0.1100R | +0.1681R |
| DISCOVERY | LSAR_ROLLING30_SB10 | 15298 | -0.0079R | -0.0088R | 0.5289 | -0.1423R | +0.1399R |
| WF | FD_W10 | 6758 | -0.0230R | -0.0238R | 0.6427 | -0.1607R | +0.1219R |
| WF | FD_W3 | 12726 | +0.0100R | +0.0113R | 0.4172 | -0.1170R | +0.1311R |
| WF | FD_W5 | 12120 | +0.0189R | +0.0113R | 0.4451 | -0.1126R | +0.1458R |
| WF | LSAR_ROLLING30_SB10 | 7253 | -0.0036R | -0.0052R | 0.5349 | -0.1318R | +0.1285R |

## Verdict

No primary family passed the preregistered Discovery + WF gate.

- Liquidity sweep with same-bar reclaim: NO-GO as a broad unconditional event class.
- Failed displacement W10: NO-GO.
- Failed displacement W3/W5: weak positive drift only; not statistically distinguishable from matched null.
- Sealed OOS remains unopened.
- No entry/exit tournament is authorized from this broad event universe.

## Next research implication

The broad event classes are too heterogeneous. The only defensible continuation is a preregistered conditional study using post-event evidence already defined in the specification: reclaim speed, failed second push, and acceptance inside the pre-impulse range. These conditions must be frozen before any OOS contact.