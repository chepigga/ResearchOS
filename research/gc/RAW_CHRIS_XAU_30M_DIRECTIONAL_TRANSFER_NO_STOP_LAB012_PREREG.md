# RAW CHRIS XAU 30M DIRECTIONAL TRANSFER NO STOP — LAB012 PREREG

Purpose: test whether frozen Chris SHORT direction itself transfers from GC to executable FTMO-Demo XAUUSD over a fixed 30-minute horizon, independent of stop/target geometry.

Frozen source signal:
- source ledger: `GC_SHORT_CHRIS_AEIF_BUY_FAILURE_LAB_003_EVENTS.csv`
- feed: `AMP_CQG_RAW_EXCLUSIVE`
- all events in the Aug-Sep 2026 GC/XAU overlap
- no POST10 Q50 gate
- no new filter/score/session/spread condition

Frozen XAU execution:
- clock mapping: GC UTC -> FTMO broker clock `+180 min`, inherited from LAB007
- entry: first executable XAU tick at GC `entry_time`, SHORT at Bid
- exit: first executable XAU tick at exactly `entry_time + 30m`, cover at Ask
- no SL
- no TP
- no limit entry
- no early exit
- no trailing/BE
- spread embedded by Bid-entry / Ask-exit
- entry/exit tick tolerance: 5 seconds
- XAU ATR14 from previous completed broker M1 is used only to normalize return, not for execution

Primary metrics:
- N executable
- EV in XAU ATR units
- EV bps
- median
- WR
- Sum ATR
- monthly EV
- event bootstrap P(EV>0), 95% CI

Frozen decision gates:
1. signals >=20
2. executable >=20
3. gross EV ATR >0
4. gross EV bps >0
5. WR >=50%
6. both Aug and Sep monthly EV ATR >=0
7. bootstrap P(EV>0) >=0.80

Interpretation:
- PASS means the raw directional Chris effect transfers to executable XAU on this overlap, while LAB011 failure can be attributed at least partly to stop/target geometry.
- FAIL means the raw 30m directional transfer itself is not supported on this executable-XAU overlap.

This is a small historical overlap and not independent OOS. No post-hoc rescue tuning is allowed inside LAB012.