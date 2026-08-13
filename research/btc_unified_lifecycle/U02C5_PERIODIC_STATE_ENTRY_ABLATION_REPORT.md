# U02C5 — PERIODIC STATE ENTRY ABLATION

**Status:** COMPLETED — diagnostic PASS for Tier A state-only periodic entry; FAIL for B3 state-only periodic entry.

## Frozen methodology

- Canonical H4 market clock: Supertrend ATR10 × 3, U05 `BAR_OPEN + lag1`.
- `TIER_A BUY`: H4 ST age > 58, H4 ST opposite to BUY.
- `B3 BUY`: H4 ST age 28–58.
- No v283. No FVG.
- Entry policies: FIRST_ONLY, every 4h / 8h / 12h / 24h from causal state onset while state remains valid.
- Entry: next M1 open.
- SL: 1.5 × completed H1 ATR14.
- No TP; 48h time exit.
- Cost proxy: $27.5/BTC.
- Prop episode budget: max 0.50% initial risk per episode. Cadence-safe allocation: 4h=/12, 8h=/6, 12h=/4, 24h=/2.

## Tier A summary

| Policy | N | /week | EV/trade | PF | positive years | EV prop/episode | sum prop return | realized DD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| FIRST_ONLY | 16 | 0.12 | +0.526R | 1.90 | 2/3 | +0.263% | +4.21% | 3.57% |
| 4h | 318 | 2.35 | +0.599R | 1.99 | 3/3 | +0.496% | +7.94% | 2.01% |
| **8h** | **163** | **1.21** | **+0.689R** | **2.18** | **3/3** | **+0.585%** | **+9.35%** | **2.09%** |
| 12h | 110 | 0.81 | +0.569R | 1.89 | 3/3 | +0.489% | +7.82% | 1.82% |
| 24h | 60 | 0.44 | +0.627R | 2.06 | 2/3 | +0.587% | +9.40% | 3.35% |

Tier A 8h yearly EV: 2024 +0.871R, 2025 +0.548R, 2026 +0.705R.

Episode bootstrap (16 independent episodes): 8h EV episode +0.585%, 95% CI about [+0.343%, +0.834%], P(EV>0) ≈100%. Paired versus FIRST_ONLY: +0.321% episode return, CI crosses zero, P≈90%, so periodic is strongly positive but not yet statistically proven superior to FIRST_ONLY.

## Phase robustness

Tier A 8h: offset 0h +0.689R PF2.18; offset +4h +0.505R PF1.80. Both variants positive in 2024/2025/2026.

Tier A 12h: offsets 0h/+4h/+8h yield +0.569R / +0.707R / +0.520R, all 3/3 positive years.

This supports Tier A as a genuine state edge rather than a narrow timestamp edge.

## B3 BUY summary

| Policy | N | /week | EV/trade | PF | positive years | EV prop/episode |
|---|---:|---:|---:|---:|---:|---:|
| FIRST_ONLY | 83 | 0.61 | +0.078R | 1.10 | 2/3 | +0.039% |
| 4h | 1657 | 12.26 | +0.026R | 1.03 | 2/3 | +0.021% |
| 8h | 858 | 6.35 | +0.018R | 1.02 | 2/3 | +0.016% |
| 12h | 592 | 4.38 | +0.019R | 1.02 | 2/3 | +0.017% |
| 24h | 327 | 2.42 | −0.007R | 0.99 | 1/3 | −0.007% |

2026 B3 deteriorates: FIRST_ONLY −0.073R, 4h −0.204R, 8h −0.148R, 12h −0.228R.

All B3 episode-level bootstrap intervals cross zero and every periodic cadence has negative paired episode-value delta versus FIRST_ONLY.

B3 is phase-sensitive: e.g. 12h offsets 0/+4/+8 give +0.019R / −0.074R / +0.137R. Therefore arbitrary B3 periodic entry is rejected.

## Interpretation

U02C4 random timing inside B3 was conditional on B3 episodes where a v283 event already occurred. U02C5 tests all B3 episodes and shows the full state is not enough.

- Tier A generalizes to state-only periodic trading.
- B3 does not.
- Tier A preferred candidate: deterministic 8h entry with 0.50% episode risk cap.
- 4h raises order count but does not raise episode value enough to justify the extra fragmentation.
- To reach 4–6 economically meaningful setups/week, solve B3 selection rather than counting many tiny Tier-A re-entries as independent setups.

## Next LAB

`U02C6 — B3_V283_OCCURRENCE_SELECTION_ABLATION`

Compare B3 episodes WITH any v283 occurrence versus B3 episodes WITHOUT v283 occurrence, then evaluate deterministic/random entries inside each group without using the v283 timestamp. This tests whether v283's occurrence is a selector of profitable B3 episodes even though exact v283 timing did not prove alpha.
