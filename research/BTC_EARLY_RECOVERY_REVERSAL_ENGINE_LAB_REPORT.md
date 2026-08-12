# BTC_EARLY_RECOVERY_REVERSAL_ENGINE — Research Report

Date: 2026-08-12
Branch: `lab-btc-early-recovery-reversal`
Status: **MECHANICAL EARLY BRANCH FAIL / HYBRID FUSION ARCHITECTURE DISCOVERED**

## 1. Motivation

Manual-vs-engine recall showed that the current LAB020 continuation architecture misses a large fraction of profitable recent manual BTC trades:

- current Tier recall: 0/9
- LAB020 parent recall: 0/9
- raw M15 FVG within ±90m: 7/9 = 77.8%
- manual BTC AI BUY `fin=150`: raw-FVG recall 5/5

The failure therefore occurs mostly after event detection, not at the FVG-location layer.

## 2. Hypothesis tested

A separate early branch was tested instead of weakening LAB020:

- classical M15 first-touch FVG
- young FVG age 2–10 M15 bars
- short-horizon delivery (1h/2h/4h/8h), because recent `fin=150` winners were mostly held for minutes to ~2h rather than 48h
- causal completed-bar state only
- no use of August manual P/L for training or threshold selection

## 3. V2 — naive early shell

Frozen shell:

- BUY: young FVG + H1 6h directional displacement still opposite
- SELL: young FVG + H1 6h directional displacement aligned

2024–2026 OOS combined shell was economically negative at every tested horizon:

- 1h EV ≈ -0.058%, PF ≈ 0.70
- 2h EV ≈ -0.058%, PF ≈ 0.78
- 4h EV ≈ -0.049%, PF ≈ 0.86
- 8h EV ≈ -0.044%, PF ≈ 0.91
- 48h EV ≈ -0.074%, PF ≈ 0.94

Verdict: **FAIL**. Young FVG + simple H1 state is not the missing edge.

## 4. V3b — causal structural router

Universe:

- all young first-touch FVG age 2–10
- no H1 hard gate

Causal feature families were chosen from an independently existing pre-August BTC engine vocabulary:

- HTF EMA bias / distance / slope
- H1/M15 momentum and efficiency
- BOS proxies
- micro break
- liquidity sweep/reclaim proxy
- FVG size
- CHoCH/disagreement proxies
- volatility state

Model:

- separate BUY / SELL Ridge
- alpha = 10 fixed
- expanding OOS: train <2024 -> 2024; train <2025 -> 2025; train <2026 -> 2026
- target = 2h net return after $27.5/BTC spread proxy
- HIGH = top third of train score

### OOS 2024–2026

BUY:

- LOW: N=2476, EV2h=-0.1227%, PF=0.541
- MID: N=2457, EV2h=-0.0526%, PF=0.792
- HIGH: N=3391, EV2h=-0.0192%, PF=0.917

SELL:

- LOW: N=2470, EV2h=-0.1539%, PF=0.462
- MID: N=2460, EV2h=-0.1014%, PF=0.647
- HIGH: N=2826, EV2h=-0.0305%, PF=0.859

Combined:

- LOW: EV2h=-0.1383%, PF=0.500
- MID: EV2h=-0.0770%, PF=0.708
- HIGH: N=6217, ~21.1/week, EV2h=-0.02435%, PF=0.889, WR=45.5%

The ranking is monotonic (LOW < MID < HIGH), so the features contain information, but even HIGH remains negative after spread.

Yearly HIGH combined:

- 2024 EV2h=-0.0429%, PF=0.828
- 2025 EV2h=-0.0205%, PF=0.906
- 2026 EV2h=-0.0084%, PF=0.950

Positive OOS years: 0/3.

Tail removal worsens results; there is no hidden robust positive core under this score.

Verdict: **FAIL** for a pure OHLC/mechanical early-recovery production branch.

## 5. Manual sanity check

For August 2026 `BTC_AI_BUY_FIN150` manual candidates:

- young-FVG ±90m recall: 4/5 = 80%
- V3b HIGH ±90m recall: 3/5 = 60%
- among the four young events that were near the manual entry, 3/4 were HIGH

Thus the mechanical router partially identifies the same locations, but cannot reproduce their economic selectivity over history.

## 6. Critical discovery: `final` is a fusion score

Independent April 2026 execution logs show:

- pre=69, ai=75 -> final=144
- pre=82, ai=73 -> final=150
- pre=100, ai=75 -> final=150
- pre=80, ai=73 -> final=150
- pre=0, ai=81 -> final=81
- pre=52, ai=79 -> final=131

These examples are exactly consistent with:

`final = min(150, pre + ai)`

Therefore `fin=150` is **not a technical price-state label**. It is the output of a two-channel fusion:

1. `pre` — mechanical/structural score
2. `ai` — independent AI / semantic confidence
3. `final` — capped sum

This explains the core research discrepancy: an OHLC-only model can approximate the mechanical ranking but cannot reconstruct the missing AI information channel.

## 7. Architecture decision

Do **not** weaken LAB020 continuation rules and do **not** promote V2/V3b as a trading branch.

Keep:

- LAB020/LAB021 continuation branch
- BUY B4 premium state and H4-direction routing
- SELL phase research as a separate branch

For early recovery, the next valid architecture is:

```text
RAW / YOUNG EVENT SHELL
        |
        +--> MECHANICAL PRE CHANNEL
        |      structure / liquidity / FVG / BOS / EMA / phase
        |
        +--> INDEPENDENT AI CONFIRMATION CHANNEL
               causal context only

FINAL = capped fusion(pre, ai)
```

Historical validation of the full hybrid branch is not possible from OHLC alone. It requires either:

- historical AI/SMART_MOCK decisions aligned to events, or
- a frozen deterministic replacement for the AI channel that can be replayed causally without using future outcomes.

## 8. Research verdict

**MECHANICAL EARLY_RECOVERY_REVERSAL_ENGINE: FAIL.**

**HYBRID PRE + AI EARLY-RECOVERY ARCHITECTURE: DISCOVERED / NOT YET HISTORICALLY CLOSED.**

The most important result is not a new threshold. It is that the recent `fin=150` manual edge cannot be treated as an OHLC/FVG edge; its selection mechanism includes a separate confirmation channel.
