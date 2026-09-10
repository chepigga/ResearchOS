# XAU_H1_CONTEXT_ALIGNED_BUY_SELL_FRESH_OOS_AND_EPISODE_INDEPENDENCE_LAB_008 — PREREG

Status: PREREGISTERED BEFORE OUTCOME RUN

## Frozen lineage
No thresholds, directions, stops, targets, costs, or upstream mechanics may be selected from LAB008 outcomes.

- Upstream XAU mechanics: frozen `Projects/XAU_Pool/Code/Python/XAU_POOL_SELECTION_LAB_001/step1_mechanics.py`.
- Context router: frozen LAB001/LAB002 lineage.
- Context score: `(Expansion + Pullback - Reversal - Range) / 200`.
- HIGH threshold: `context_score > 0.55`.
- TF: H1 only.
- Compatibility: ALIGNED only (`BUY` requires BULL context bias; `SELL` requires BEAR context bias).
- Signal availability: H1 candidate becomes available at H1 close; Context must use the last causally closed H4 state.
- Entry/exit model: same as LAB006/LAB007, SL = 1.5 ATR14(H1), TP = 2.25 ATR14(H1), gross RR = 1:1.5, max horizon 120h, same-bar ambiguity = STOP first.
- Primary synthetic all-in cost: 2 bps round-turn. Stress: 1/3/5 bps.
- Position routing: single open position per leg. BUY-only and SELL-only ledgers are built independently.

## Fresh OOS source and cutoff
Discovery history ended at 2026-07-23. The fresh test is sealed to data strictly after that cutoff.

Primary fresh source: GitHub release tag `xau`, asset `CAUSAL_XAU_RAW_XAUUSD_20260825.zip`, published after the frozen discovery work. Release digest observed before outcome run: `sha256:31f9548204fa99c29ce7d09e5b64e01ff75f5e8e3efab6f747cbd410cf34fd2e`.

Fresh window: `2026-07-24 00:00` through the last complete M1 bar available in the asset, capped at `2026-08-25 23:59`.

Historical warm-up before 2026-07-24 is allowed only to calculate causal indicators/router state. No pre-cutoff outcome may enter the fresh metrics.

## Schema-only probe
Archive member names/header discovery is technical only and may be performed after this prereg. It may not calculate signals, returns, or outcomes. Parser-only fixes are allowed before the first valid outcome run.

## Primary questions
Evaluate BUY and SELL separately. Neither leg may be removed or redefined after seeing LAB008 results.

### Fresh OOS metrics per leg
At 2 bps report: N, EV, PF, WR, CumR, MaxDD R, proxy DD at 0.25% risk, Recovery Factor, TP/SL/TIME rates, median hold.
Also report cost stress 1/2/3/5 bps.

Fresh evidence levels per leg:
- `FRESH_DIRECTIONALLY_POSITIVE`: N >= 5, EV > 0, PF > 1.0.
- `FRESH_STATISTICALLY_USABLE`: N >= 20 AND EV > 0 AND PF >= 1.10. (A one-month tail is expected to be underpowered; failure is not retuned.)

### Historical episode-independence diagnostic
Use the frozen LAB007 historical BUY-only and SELL-only ledgers separately.
Define a new episode whenever entry time is more than 72 hours after the previous trade exit for that same leg. This definition is frozen before results.

Report per leg:
- number of episodes;
- positive episode fraction;
- median episode R;
- maximum drawdown in episode-order R;
- largest positive episode share of total positive episode PnL;
- top-3 positive episode share;
- top-10 positive weeks share;
- best positive month share;
- weekly cluster bootstrap EV, 5000 draws.

Episode-independence support requires ALL:
1. >= 20 episodes;
2. largest positive episode share <= 0.35;
3. top-3 positive episode share <= 0.60;
4. weekly bootstrap P(EV > 0) >= 0.90.
This is a concentration diagnostic, not proof of iid independence.

## Fresh BUY-vs-SELL contrast
If both fresh legs have N >= 5, report `EV_BUY - EV_SELL` and a descriptive weekly bootstrap difference. Because the tail is short, this contrast is secondary and cannot override per-leg verdicts.

## Promotion rule
LAB008 by itself cannot authorize production because the fresh window is short and the source may not be native FTMO bid/ask parity. A leg can be marked `FRESH_SUPPORT_FOR_NATIVE_REPLICATION` only if:
- it is `FRESH_DIRECTIONALLY_POSITIVE`,
- historical episode-independence support passes,
- 5 bps stress remains EV > 0 and PF > 1.0,
- proxy DD at 0.25% risk <= 4%.

No production promotion, sizing increase, SELL deletion, BUY-only deployment, or threshold change is authorized in LAB008.
