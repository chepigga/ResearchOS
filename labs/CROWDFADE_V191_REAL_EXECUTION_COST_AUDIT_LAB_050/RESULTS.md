# LAB050 — V191 REAL EXECUTION COST AUDIT — RESULTS

Status: **DONE — TWO-BROKER OBSERVATIONAL AUDIT**

Source reports:
- GetLeveraged Ltd., account 227622 report dated 2026-09-22
- IC Markets / Raw Trading Ltd, account 53049472 report dated 2026-09-22

Primary sample:
only current V191 entries marked `CF191...`.

Excluded:
- `CF200...`
- older generic `CrowdFade`
- unmarked/manual trades

See `AUDIT_METHOD.md` for formulas and source limitations.

## Executive result

The reports do not contain entry bid/ask snapshots or requested market prices, so **true all-in spread + entry slippage cannot be reconstructed exactly**.

The measurable lower-bound cost is:
- explicit commission/swap
- plus realized slippage on exits explicitly filled through stop orders.

Converted into the same flat-bps cost parameter used by LAB049:

- **GetLeveraged observed floor: 0.68 bps**
- **IC Markets observed floor: 2.24 bps**

Sensitivity after removing each broker's single worst stop-slippage trade:
- GetLeveraged: **0.54 bps**
- IC Markets: **1.23 bps**

Therefore the full-sample IC result is heavily influenced by one ETH tail event, but even after removing it IC remains materially more expensive than GetLeveraged in this sample.

## Sample size

### GetLeveraged

Period:
2026-09-18 01:55 through 2026-09-22 20:20 report time.

- CF191 entries: 58
- closed: 56
- still open at report: 2
- BTCUSD closed: 32
- ETHUSD closed: 6
- SOLUSD closed: 18
- explicit stop exits: 46

### IC Markets

Period:
2026-09-21 21:05 through 2026-09-22 19:10 report time.

- CF191 entries: 20
- closed: 19
- still open at report: 1
- BTCUSD closed: 7
- ETHUSD closed: 7
- SOLUSD closed: 5
- explicit stop exits: 16

IC is therefore a much smaller sample and its tail estimates are less stable.

## Commission / swap

Current CF191 commissions in both reports:
**0**

GetLeveraged:
- total explicit commission/swap cost: **$2.05**
- this is one overnight BTC swap, not trading commission.

IC Markets:
- explicit commission/swap cost: **$0.00**

Thus LAB049's cost sensitivity cannot be explained by commission in these reports.
The practical concern is spread/slippage.

## Market-order fill latency

Report resolution is one second.

### GetLeveraged
- median order-to-fill: 0s
- p95: 1s
- maximum: 1s

### IC Markets
- median: 0s
- p95: 1s
- maximum: 1s

At MT5 history-report resolution there is **no evidence of a multi-second market-order fill delay** at either broker.

This does not distinguish sub-second latency such as 50ms vs 700ms.

## Stop-fill slippage

Positive = adverse slippage relative to the final requested stop.
Negative = favorable fill.

### GetLeveraged — 46 stop exits
- median: **0.51 bps**
- p90: **1.98 bps**
- p95: **2.57 bps**
- worst: **16.63 bps**
- stops worse than 2bps: 5 / 46 = **10.9%**
- stops worse than 5bps: 2 / 46 = **4.3%**

Mean observable execution drag across all closed trades:
**~0.0168R per trade**

### IC Markets — 16 stop exits
- median: **0.62 bps**
- p90: **4.92 bps**
- p95: **9.08 bps**
- worst: **20.81 bps**
- stops worse than 2bps: 6 / 16 = **37.5%**
- stops worse than 5bps: 2 / 16 = **12.5%**

Mean observable execution drag across all closed trades:
**~0.0360R per trade**

The medians are similar, but IC has a much heavier adverse tail in this small sample.

## Equivalent LAB049 cost floor by symbol

### GetLeveraged
- BTCUSD: **0.53 bps** — N32 closed / 27 stops
- SOLUSD: **0.61 bps** — N18 / 13 stops
- ETHUSD: **3.27 bps** — N6 / 6 stops

### IC Markets
- BTCUSD: **1.73 bps** — N7 / 6 stops
- SOLUSD: **0.63 bps** — N5 / 4 stops
- ETHUSD: **4.15 bps** — N7 / 6 stops

The clearest symbol-level pattern is:

- SOL is similar at both brokers and comfortably below the LAB049 historical break-even area.
- BTC is materially cleaner at GetLeveraged in this sample.
- ETH shows severe tail slippage at both brokers and is the weakest execution symbol.

Because ETH N is only 6–7 closed trades per broker, this is a warning signal, not yet a stable distribution estimate.

## Worst events

### GetLeveraged
Worst observed stop:
- ETHUSD
- CF191B1789925700
- stop slippage: **16.63 bps**
- execution loss: **0.199R**

Second notable event:
- BTCUSD CF191B1790039100
- **5.06 bps**
- **0.117R**

### IC Markets
Worst observed stop:
- ETHUSD
- CF191B1790021700
- stop slippage: **20.81 bps**
- execution loss: **0.329R**

Other important events:
- BTCUSD CF191B1790039100: **5.17 bps / 0.112R**
- BTCUSD CF191S1790076300: **4.67 bps / 0.085R**

## Comparison with LAB049 cost envelope

LAB049 approximate historical cost-only aggregate break-even:
- trail 2.5/0.5 control: ~1.48 bps
- trail 3.5/0.5 balanced: ~1.75 bps
- trail 5.0/0.5 aggressive: ~1.85 bps

### GetLeveraged

Observed lower-bound equivalent:
**0.68 bps**

This leaves approximately:
- **1.07 bps** margin to the 3.5 historical break-even
- **1.17 bps** margin to the 5.0 historical break-even

But that remaining margin still has to absorb the costs not visible in the report:
- entry spread
- entry market slippage
- spread/slippage on non-stop exits.

Interpretation:
**GetLeveraged remains plausibly compatible with V191, especially BTC/SOL, but the report alone cannot prove the true all-in total is below break-even.**

### IC Markets

Observed lower-bound equivalent:
**2.24 bps**

This is already above the historical break-even envelope for both 3.5 and 5.0 **before adding unobserved entry spread**.

However the sample is small and one ETH outlier is influential.

Removing the single worst IC trade:
observed floor falls to **1.23 bps**.

Interpretation:
**IC cannot be rejected from only 19 closed trades, but its current sample does not provide enough execution margin for comfortable V191 deployment.**

By symbol:
- IC SOL looks acceptable.
- IC BTC at 1.73 bps lower-bound is already approximately at the 3.5 historical break-even before entry spread.
- IC ETH is currently incompatible with the LAB049 cost envelope.

## Exact cross-broker matched fills

Only three exact CF191 comment + symbol entry matches exist in these reports.

GetLeveraged relative entry-price advantage:
- BTC buy CF191B1790039100: GetLeveraged **2.77 bps worse**
- SOL sell CF191S1790028300: GetLeveraged **4.87 bps better**
- BTC sell CF191S1790056500: GetLeveraged **0.39 bps better**

N=3 is too small and quote feeds differ.
Do not use this as the primary broker ranking.

## LAB050 conclusion

### GetLeveraged
Current V191 execution is the cleaner sample.

Strengths:
- larger sample;
- BTC/SOL observable cost floor around 0.5–0.6 bps;
- stop-slippage p90 below 2 bps overall;
- 0–1s report-level market-fill latency;
- no commission drag.

Risk:
- ETH tail slippage;
- unobserved market-entry spread remains unknown.

### IC Markets
Current sample has materially more tail execution risk.

Strengths:
- no commission;
- SOL execution looks similar to GetLeveraged;
- report-level market-fill latency is also 0–1s.

Risk:
- full-sample lower-bound cost already 2.24 bps;
- BTC lower bound ~1.73 bps before entry spread;
- ETH lower bound ~4.15 bps;
- stop-slippage tail much wider.

## Decision

Do **not** retune V191 based on these reports.

For the next live/shadow step:

1. **GetLeveraged** is the better current venue candidate for frozen V191 3.5/0.5 shadow/demo validation.
2. Keep **5.0/0.5** as the aggressive comparison arm, not the primary configuration.
3. IC Markets needs a larger execution sample before promotion; ETH should not be treated as validated there.
4. Add direct quote/execution telemetry to V191 so the next audit can measure true all-in cost:
   - bid/ask at decision;
   - bid/ask immediately before OrderSend;
   - requested price / order type;
   - actual fill;
   - entry spread bps;
   - entry slippage bps;
   - exit requested price;
   - exit fill;
   - commission/swap;
   - latency in milliseconds.

Only with those fields can LAB050 move from a lower-bound audit to a true all-in execution-cost measurement.
