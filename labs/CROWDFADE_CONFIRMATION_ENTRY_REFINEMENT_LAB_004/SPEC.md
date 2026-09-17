# CROWDFADE_CONFIRMATION_ENTRY_REFINEMENT_LAB_004

Status: PREREGISTERED DISCOVERY-ONLY. No fresh OOS is consumed here.

Parent frozen candidate from LAB002:
- ConfirmATR = 0.35
- StopATR = 1.25
- TTL = 3h
- Pause = 3h
- Hold = 6h
- BE = arm +0.50 ATR, lock +0.15 ATR
- Trail = arm +2.50 ATR, distance 0.50 ATR
- Entry = first causal market confirmation

Data discipline:
- Use only already-consumed Mar-Aug 2026 research data.
- No September/fresh data.
- No promotion from LAB004; winner, if any, is frozen for a later fresh OOS lab.

Primary objective:
Reduce same-bar / immediate-stop entries without materially destroying utilization or right-tail expectancy.

A. ENTRY TIMING ABLATION
A0: tick-touch entry (parent control)
A1: enter at close of the M5 bar that first confirms
A2: require that confirm survives to next M5 close; enter there
A3: wait exactly one completed M5 bar after confirm, then enter at next bar open if direction has not invalidated

B. ANTI-IMPULSE VETO
Measured causally at entry decision using completed M5 bars only.
For side s (+1 long, -1 short), crowd-direction impulse is adverse when signed return against trade direction is large.
Lookbacks: 2, 3, 4 completed M5 bars.
Thresholds: 0.75, 1.00, 1.25 ATR.
Veto only if cumulative move is in the crowd direction / against contrarian trade and exceeds threshold.
No RSI/ADX/extra indicators.

C. SPREAD SENSITIVITY
Do not optimize a hard cutoff yet. Log entry spread/ATR and report bins:
<=0.005, 0.005-0.010, 0.010-0.015, >0.015.
A later risk-sizing lab may test 0.5x size in wide-spread states.

D. REQUIRED LOGGING PER TRADE
signal_ts, confirm_touch_ts, confirm_bar_close_ts, entry_ts, exit_ts,
side, z, frozen_signal_ATR, entry_price, spread_atr,
entry_delay_seconds, entry_delay_bars,
preentry_impulse_2bar_atr, preentry_impulse_3bar_atr, preentry_impulse_4bar_atr,
MAE_ATR_15m, MAE_ATR_30m, MAE_ATR_60m,
MFE_ATR_15m, MFE_ATR_30m, MFE_ATR_60m,
final_MAE_ATR, final_MFE_ATR, exit_reason, R.

PRIMARY COMPARISONS
1. A0 vs A1 vs A2 vs A3 with no anti-impulse veto.
2. Best timing state by predeclared stability rule vs same state + each anti-impulse veto.
3. Do not combine timing + veto + exit changes in this lab.

SELECTION RULE
A timing candidate survives only if:
- aggregate EV >= parent EV,
- MaxDD <= parent MaxDD,
- stop rate decreases by >=10% relative,
- retained trades >=60%,
- at least 4/6 months positive,
- no single month contributes >40% of total SumR.

An anti-impulse veto survives only if, relative to chosen timing state:
- EV improves by >=0.02R OR MaxDD falls >=20%,
- retained trades >=70%,
- stop rate falls,
- result sign is consistent in at least 4/6 months.

SECONDARY DIAGNOSTICS ONLY
- session/hour decomposition
- spread bins
- signal->confirm->entry latency
- MAE/MFE survival curves
These cannot select the winner in LAB004.

OUT OF SCOPE
- Stop 1.50/1.75
- ExitZ changes
- BE/trailing changes
- 3-4h hold
- fail-fast MFE exit
- multi-symbol correlation sizing
These move to separate labs after entry refinement is frozen.

Prior evidence guardrail:
LAB027 found acceptance/adverse-veto concept economically plausible but not robust in pooled recent data; LAB028 found post-confirm failure states highly discriminative but execution policies not robust enough for promotion. Therefore LAB004 treats these as hypotheses, not inherited wins.

Live allocation: 0%. Frozen live CrowdFade unchanged.
