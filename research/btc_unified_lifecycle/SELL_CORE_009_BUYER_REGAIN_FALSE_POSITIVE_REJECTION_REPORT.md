# SELL_CORE_009 — BUYER_REGAIN_FALSE_POSITIVE_REJECTION

**Preregistered after 008; same-history confirmation, not independent OOS. Primary horizon = 60m.**

## Primary verdict

**REJECT as tradable SELL veto.**

At 60m the buyer-regain veto classified future lifecycle resolution reasonably well:
- eligible N=40; future structure-break winners=12; others=28;
- winners kept 9/12 = 75%; winners vetoed 3/12 = 25%;
- losers vetoed 20/28 = 71.4%; losers kept 8/28 = 28.6%.

But the retained SELL population was not profitable:
- SELL_KEEP_60M: N=17, EV48=-0.0626R, PF48=0.929, EV_price48=-0.3823%;
- EV72=-0.5060R, PF72=0.448, EV_price72=-0.7220%.

Cluster bootstrap for SELL_KEEP_60M:
- 48h EV=-0.0626R, CI [-1.0377,+1.6056], P(EV>0)=33.5%; price EV=-0.3823%, P>0=21.8%;
- 72h EV=-0.5060R, price EV=-0.7220% with price CI entirely negative.

Yearly 60m SELL_KEEP:
- 2024: N8, EV48=-0.963R, PF=0;
- 2025: N6, EV48=-0.685R, PF=0.204;
- 2026: N3, EV48=+3.584R, PF=6.16.
Thus the apparent benefit is carried by 2026 and does not transfer backward.

Waiting 60m also reduced value versus immediate failed-attack entry on the same 17 kept events:
- 48h delta=-0.0389R, CI [-0.0761,-0.00011], P(delta>0)=1.9%;
- price delta=-0.06725 percentage points, P(delta>0)=2.2%.

## Interpretation

The veto is useful as a **lifecycle classifier**, but not as a sufficient **P/L classifier**. Absence of buyer regain by a fixed 60m horizon does not prove the seller has tradable control.

A second important clue is timing: among future failures later invalidated by buyers, 8/28 still had no buyer-regain veto by 60m. Their eventual regain happened later. Conversely, 3/12 eventual seller winners showed transient buyer-regain evidence by 60m and would have been falsely vetoed.

Therefore fixed-time `NO_BUYER_REGAIN -> SELL` is rejected. The next clean research object should be an **event race**, not another fixed-time threshold: after a failed attack, compare the first causal seller-acceptance event against the first buyer-reclaim event using structural levels rather than waiting 15/30/60 minutes.
