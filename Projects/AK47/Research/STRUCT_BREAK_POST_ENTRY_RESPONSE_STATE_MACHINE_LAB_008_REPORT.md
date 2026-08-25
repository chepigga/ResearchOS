# STRUCT_BREAK_POST_ENTRY_RESPONSE_STATE_MACHINE_LAB_008

Date: 2026-08-25
Status: COMPLETED
Verdict: `POST_ENTRY_STATE_PREDICTIVE__IMMEDIATE_EXIT_NOT_VALIDATED`
Preregistration: `29bee90656df7b54cf50d65fad462366ae04fdb1`

## Objective
Test whether causal post-entry price response can distinguish a real directional move from a stalled/failed break and improve trade management.

## Data
Canonical STRUCT_BREAK v002.
DEV 2019-09..2022-12: N=767.
VAL 2023-01..2025-12: N=698.
2026 excluded from verdict.

Exact reconstruction of entry level, pivot-5 stop and event ATR succeeded for all 1,620 rows including shadow 2026. Stored riskATR/gap reproduce to floating-point tolerance.

Primary lower clock: exact Binance BTCUSDT M5.
M1 replication: 2024-2025.
The bar containing the first limit touch is excluded from post-entry features; observation starts on the next fully closed lower-timeframe bar.

## Main result
A DEV-trained causal response model predicts whether an alive trade not yet at +1R will eventually reach +1R:

- 5m: VAL AUC 0.594, 95% CI [0.549, 0.635]
- 15m: VAL AUC 0.615, CI [0.568, 0.661]
- 30m: VAL AUC 0.642, CI [0.596, 0.687]
- 60m: VAL AUC 0.654, CI [0.601, 0.704]
- 120m: VAL AUC 0.710, CI [0.650, 0.771]

The strongest single feature is current directional NET_R. At 30m oriented VAL AUC is ~0.651. Directional-close fraction (~0.623), closeback fraction (~0.618), MFE (~0.604), and MAE (~0.594) also carry information. Flow/range expansion are weaker.

## 30-minute response states
DEV-frozen score thirds applied unchanged to VAL:

HIGH / IMPULSE: N=143, P(reach +1R)=67.1%, final EV +0.271R, NET +0.420R, MFE +0.579R, MAE 0.060R, path efficiency 0.586, only 8.0% closes back through the broken level.

MID: N=170, P(reach +1R)=53.5%, final EV +0.067R.

LOW / FAILURE-STALL: N=200, P(reach +1R)=37.0%, final EV -0.271R, NET -0.256R, MFE +0.169R, MAE 0.494R, ~75.7% closes back through the broken level.

The same separation exists on DEV: HIGH EV +0.406R versus LOW -0.302R. VAL HIGH-minus-LOW EV difference is ~+0.542R with bootstrap 95% CI approximately [+0.257R,+0.820R].

M1 2024->2025 replication preserves the core result. At 30m AUC 2025=0.624; HIGH P(+1R)=63.5%, EV +0.105R versus LOW P(+1R)=40.6%, EV -0.279R.

## Immediate-exit test
Preregistered grid tested MFE/NET/MAE early-exit rules at 5/15/30/60/120m.

Best DEV rule: 30m `MFE<0.25R AND MAE>=0.25R`.
DEV: affected 139, EV +0.0155R -> +0.0407R, improvement +0.0252R, DD 39.44R -> 30.90R.

Frozen VAL: affected 130, EV -0.0315R -> -0.0458R, improvement -0.0143R, DD 38.78R -> 54.75R.
2023 improvement +0.039R; 2024 -0.039R; 2025 -0.043R.

Therefore `STALL -> MARKET EXIT` is rejected.

## Interpretation
The market does reveal useful information after entry. A real move is characterized mainly by positive net progress, low adverse excursion, little repeated acceptance back through the broken level and a cleaner path.

However, identifying a bad future state is not the same as proving that selling immediately at the current price is optimal. By the time a trade proves weak, many positions are already below entry; enough later recover that immediate exit can crystallize more loss than expected HOLD.

## Formal verdict
`POST_ENTRY_STATE_PREDICTIVE__IMMEDIATE_EXIT_NOT_VALIDATED`

Confirmed: causal adaptive observation is valuable.
Rejected: simplistic immediate market exit for stalled trades.

## Next step
`STRUCT_BREAK_ADAPTIVE_EXIT_REARM_REENTRY_LAB_009`

Compare canonical HOLD against market exit, scratch-on-recovery, exit+re-arm, and re-entry on renewed M1/M5 impulse without changing the original structural signal.
