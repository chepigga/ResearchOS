# XAU_CONTEXT_TEMPORAL_ROLE_AND_STATE_AGE_REDESIGN_LAB_009

**Verdict: PARTIAL_TEMPORAL_ROLE_SUPPORT**

> Human-readable Context display-layer diagnostic only. No trading edge or execution claim.

- Canonical XAU SHA: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`
- Valid Context H4 bars: **6,216**
- Frozen state episodes: **610**
- Eligible primary hypotheses: **5/6**
- Primary bootstrap passes: **3/5 eligible**
- 3/4-year transfer passes (H2-H6): **4/5**

## Frozen redesigned display roles

| Role | Bars | Episodes | Share |
|---|---:|---:|---:|
| PULLBACK_MATURE | 3,094 | 276 | 49.8% |
| PULLBACK_FORMING | 931 | 318 | 15.0% |
| EXPANSION_MATURE | 914 | 135 | 14.7% |
| EXPANSION_FORMING | 556 | 201 | 8.9% |
| RANGE_STALE | 522 | 74 | 8.4% |
| RANGE_SHORT | 159 | 81 | 2.6% |
| REVERSAL_AFTERGLOW | 30 | 10 | 0.5% |
| REVERSAL_EVENT | 10 | 10 | 0.2% |

## Primary preregistered hypotheses

| Hypothesis | Metric | Role A | Role B/null | Effect | 95% CI | N A | N B | Status |
|---|---|---|---|---:|---:|---:|---:|---|
| H1_REVERSAL_ONSET_EVENT | momentum_flip_24h | REVERSAL_EVENT | REVERSAL_AFTERGLOW | +0.3833 | [+0.0977, +0.6875] | 5 | 24 | UNDERPOWERED |
| H2_RANGE_SHORT_CONTAINMENT | contained_1atr_8h | RANGE_SHORT | RANGE_STALE | +0.0242 | [-0.0769, +0.1238] | 154 | 487 | FAIL |
| H3_PULLBACK_MATURITY_CONTINUATION | bias_follow_24h | PULLBACK_MATURE | PULLBACK_FORMING | +0.0763 | [+0.0095, +0.1453] | 1619 | 519 | PASS |
| H4_EXPANSION_MATURITY_MOVEMENT | range_atr_24h | EXPANSION_MATURE | EXPANSION_FORMING | +0.2193 | [-0.0407, +0.5036] | 738 | 449 | FAIL |
| H5_PULLBACK_MATURE_ABSOLUTE_BIAS | bias_follow_24h | PULLBACK_MATURE | 0.50 | +0.0849 | [+0.0399, +0.1278] | 1619 | 0 | PASS |
| H6_MATURE_EXPANSION_VS_SHORT_RANGE | range_atr_24h | EXPANSION_MATURE | RANGE_SHORT | +0.4122 | [+0.1097, +0.7227] | 738 | 139 | PASS |

## Year transfer

| Hypothesis | Positive / eligible years | Transfer |
|---|---:|---|
| H2_RANGE_SHORT_CONTAINMENT | 2/4 | FAIL/UNDERPOWERED |
| H3_PULLBACK_MATURITY_CONTINUATION | 3/4 | PASS |
| H4_EXPANSION_MATURITY_MOVEMENT | 4/4 | PASS |
| H5_PULLBACK_MATURE_ABSOLUTE_BIAS | 4/4 | PASS |
| H6_MATURE_EXPANSION_VS_SHORT_RANGE | 4/4 | PASS |

## Interpretation rules

- A pass validates the temporal **display role**, not a trading setup.
- `REVERSAL_EVENT` is intentionally tested only at episode onset; later reversal bars are retained as `REVERSAL_AFTERGLOW`.
- `RANGE_SHORT` is age 1–2 only; later range bars remain visible as `RANGE_STALE` for diagnostics.
- `PULLBACK_MATURE` / `EXPANSION_MATURE` begin at age 4 H4 bars; no age-boundary search is allowed.
- Secondary 4/8/12/24/48h shape tables cannot override the preregistered primary horizons.
- Reused history: even a full pass remains discovery-only until fresh post-freeze replication.