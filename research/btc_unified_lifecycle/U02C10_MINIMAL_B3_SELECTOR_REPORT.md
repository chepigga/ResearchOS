# U02C10 — MINIMAL B3 SELECTOR

## Verdict: PASS / FREEZE CANDIDATE

Primary rule is fully score-free:

```text
B3 BUY
+ bullish H1 CHoCH
+ HTF bias = BUY
+ distance_to_H1_EMA50 <= 1.5 × H1 ATR14
→ next fixed H4 clock
→ ONE BUY
SL = 1.5 × H1 ATR14
no TP
48h time exit
```

No PRE threshold. No PRE score in primary geometry. No AI. No FVG/OB. No D1 veto. No knife/panic requirement.

## Primary causal result

- selector episodes: 51
- causal treated entries: 50
- treated EV: +0.840R
- matched control EV: -0.259R
- excess: **+1.099R**
- 95% CI: **[+0.035R, +2.261R]**
- P(Δ>0): **97.82%**
- price excess: +0.915%
- median selector delay: 22h

K5 sensitivity:
- excess +0.892R
- CI [-0.046R, +1.954R]
- P(Δ>0)=96.81%

## Year stability, K1

- 2024: treated +0.810R; excess +0.851R
- 2025: treated +0.772R; excess +1.173R
- 2026: treated +0.989R; excess +1.428R

The excess sign is positive 3/3 years.

## Overlap versus accepted v283 occurrence subset

- minimal selector episodes: 51
- v283 episodes: 50
- intersection: 50
- v283 coverage: **100%**
- precision versus v283: **98.04%**
- extra episodes: 1
- missed v283 episodes: 0
- Jaccard: 0.9804

The score-free selector and legacy v283 LateEntry sensitivity produce the same episode population and the same causal P/L in this test.

## Benchmarks

- U02C6B v283: Δ +1.145R, P=97.79%
- U02C9 ladder through LateEntry: Δ +1.071R, P=97.08%
- U02C10 minimal score-free: **Δ +1.099R, P=97.82%**

## Interpretation

The B3 occurrence edge does not require v283 as a system. The economically relevant mechanism is captured by H1 structural transition in BUY HTF context while price is not overextended relative to H1 EMA50/ATR.

PRE/AI can be removed from the B3 selector. The minimal B3 branch is ready to enter the unified BTC-core replay as a frozen research candidate. Final production acceptance still requires unified portfolio/floating-DD/prop-risk replay.
