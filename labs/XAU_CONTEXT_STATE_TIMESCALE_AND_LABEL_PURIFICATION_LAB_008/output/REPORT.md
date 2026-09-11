# XAU_CONTEXT_STATE_TIMESCALE_AND_LABEL_PURIFICATION_LAB_008

**Verdict: CONTEXT_LABELS_REQUIRE_REDESIGN**

> State-meaning diagnostic only. No trading edge, TP/SL, PF/EV or live-risk claim.

- Canonical XAU SHA: `db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b`
- Valid Context H4 bars: **6,216**
- Primary episode onsets: **610**

## Natural timescale by label

| State | Confirmed horizon | Peak observed horizon | Peak effect | Year transfer | Purity |
|---|---:|---:|---:|---|---|
| EXPANSION | NONE | 24h | +0.2049 | TIME_UNSTABLE (0/0) | PURITY_NOT_CONFIRMED |
| PULLBACK | NONE | 48h | +0.0733 | TIME_UNSTABLE (0/0) | PURITY_UNDERPOWERED |
| REVERSAL | NONE | 24h | +0.2646 | TIME_UNSTABLE (0/0) | PURITY_UNDERPOWERED |
| RANGE | NONE | 8h | +0.0989 | TIME_UNSTABLE (0/0) | PURITY_UNDERPOWERED |

## Horizon contrasts

| State | H | Effect | 95% CI | P(>0) | N state | N comparator | Confirmed |
|---|---:|---:|---:|---:|---:|---:|---|
| EXPANSION | 4h | +0.0254 | [-0.1396, +0.1771] | 0.633 | 190 | 79 | NO |
| EXPANSION | 8h | +0.0388 | [-0.1470, +0.2120] | 0.669 | 182 | 78 | NO |
| EXPANSION | 12h | +0.0824 | [-0.1103, +0.2780] | 0.807 | 175 | 77 | NO |
| EXPANSION | 24h | +0.2049 | [-0.0835, +0.4859] | 0.910 | 162 | 71 | NO |
| EXPANSION | 48h | -0.0456 | [-0.4783, +0.3741] | 0.413 | 130 | 60 | NO |
| PULLBACK | 4h | +0.0463 | [-0.0198, +0.1142] | 0.910 | 205 | 0 | NO |
| PULLBACK | 8h | +0.0294 | [-0.0419, +0.1030] | 0.779 | 204 | 0 | NO |
| PULLBACK | 12h | -0.0025 | [-0.0764, +0.0700] | 0.462 | 201 | 0 | NO |
| PULLBACK | 24h | -0.0304 | [-0.1056, +0.0393] | 0.177 | 181 | 0 | NO |
| PULLBACK | 48h | +0.0733 | [-0.0102, +0.1531] | 0.958 | 150 | 0 | NO |
| REVERSAL | 4h | +0.0079 | [-0.4755, +0.4919] | 0.514 | 6 | 126 | NO |
| REVERSAL | 8h | +0.2090 | [-0.2500, +0.5862] | 0.840 | 6 | 118 | NO |
| REVERSAL | 12h | +0.1712 | [-0.2860, +0.5500] | 0.800 | 6 | 111 | NO |
| REVERSAL | 24h | +0.2646 | [-0.1818, +0.5234] | 0.898 | 5 | 99 | NO |
| REVERSAL | 48h | -0.2189 | [-0.6364, +0.4789] | 0.208 | 3 | 67 | NO |
| RANGE | 4h | +0.0775 | [-0.0242, +0.1775] | 0.936 | 79 | 190 | NO |
| RANGE | 8h | +0.0989 | [-0.0296, +0.2235] | 0.936 | 78 | 182 | NO |
| RANGE | 12h | +0.0613 | [-0.0612, +0.1874] | 0.834 | 77 | 175 | NO |
| RANGE | 24h | -0.0029 | [-0.0912, +0.0883] | 0.457 | 71 | 162 | NO |
| RANGE | 48h | -0.0141 | [-0.0560, +0.0328] | 0.266 | 60 | 130 | NO |

## Purity distribution — episode onsets

- **EXPANSION:** INHERITED_CONFLICT=46 (22.9%); STRONG_PURE=127 (63.2%); WEAK_PURE=28 (13.9%)
- **PULLBACK:** INHERITED_CONFLICT=24 (7.5%); STRONG_PURE=282 (88.7%); WEAK_PURE=12 (3.8%)
- **REVERSAL:** INHERITED_CONFLICT=4 (40.0%); STRONG_PURE=6 (60.0%)
- **RANGE:** INHERITED_CONFLICT=18 (22.2%); STRONG_PURE=63 (77.8%)

## Interpretation

- `confirmed_horizon` is the earliest preregistered horizon with positive semantic effect and weekly-bootstrap 95% CI entirely above zero.
- `peak_observed_horizon` is descriptive only and must not be treated as confirmed when its CI fails.
- `STRONG_PURE` means the hysteresis label is also the current raw score winner with >=10 score-point lead.
- If purity helps, the next lab may preregister a redesigned display layer; this lab itself does not change the router.
- Reused history: no live/production promotion is authorized.