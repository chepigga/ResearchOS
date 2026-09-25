# GC-XAU LAB020/021 — 155 BROAD SIGNAL EXIT GRID + SIGNAL ATTRIBUTION

Date: 2026-09-25
Scope: the same 155 closed Broad XAU trades from FTMO report, with GCZ6 M1 used as a path/regime proxy.
Clock: FTMO report time -> UTC = -180 minutes.
Important: GC path is used only after validation against actual 5m XAU returns; this is descriptive research, not production authorization.

## Proxy validation
Timeout sample N=5; Pearson corr(actual XAU grossR, GC proxy 5m R)=0.8887; MAE=0.2267R; bias=0.0988R.

## Actual current performance by method
- DOM: N=41, netEV=0.1333R, PF=1.537, WR=63.4%, dir-hit 1/3/5m=NaN/NaN/NaN%, MFE5=NaNR, MAE5=NaNR
- BASE: N=54, netEV=0.0019R, PF=1.007, WR=55.6%, dir-hit 1/3/5m=0.0/50.0/0.0%, MFE5=0.166R, MAE5=0.647R
- MIX: N=49, netEV=-0.2091R, PF=0.492, WR=40.8%, dir-hit 1/3/5m=50.0/75.0/100.0%, MFE5=0.774R, MAE5=0.389R
- REV: N=11, netEV=-0.4752R, PF=0.045, WR=18.2%, dir-hit 1/3/5m=NaN/NaN/NaN%, MFE5=NaNR, MAE5=NaNR

## Feature attribution
- 3m impulse aligned: yes EV=0.4250R (N=2) vs no EV=-0.0703R (N=153); delta=0.4953R
- 5m impulse aligned: yes EV=0.1892R (N=3) vs no EV=-0.0689R (N=152); delta=0.2581R
- H1 aligned: yes EV=-0.0551R (N=85) vs no EV=-0.0746R (N=70); delta=0.0195R
- H4 aligned: yes EV=-0.0746R (N=70) vs no EV=-0.0551R (N=85); delta=-0.0195R
- H1&H4 BOTH aligned: yes EV=NaNR (N=0) vs no EV=-0.0639R (N=155); delta=NaNR
- BUY side: yes EV=-0.0551R (N=85) vs no EV=-0.0746R (N=70); delta=0.0195R

## Best exit-grid cells per method (GC path proxy; gross R)
### BASE
- H=5m TP=0.5R: EV=-0.3624R PF=0.000 TP-hit=0.0% SL=0.0%
- H=5m TP=1R: EV=-0.3624R PF=0.000 TP-hit=0.0% SL=0.0%
- H=5m TP=1.5R: EV=-0.3624R PF=0.000 TP-hit=0.0% SL=0.0%
- H=5m TP=2R: EV=-0.3624R PF=0.000 TP-hit=0.0% SL=0.0%
- H=10m TP=0.5R: EV=-1.0000R PF=0.000 TP-hit=0.0% SL=100.0%
### MIX
- H=10m TP=1R: EV=1.0000R PF=INF TP-hit=100.0% SL=0.0%
- H=15m TP=1R: EV=1.0000R PF=INF TP-hit=100.0% SL=0.0%
- H=30m TP=1R: EV=1.0000R PF=INF TP-hit=100.0% SL=0.0%
- H=10m TP=1.5R: EV=0.7000R PF=INF TP-hit=0.0% SL=0.0%
- H=10m TP=2R: EV=0.7000R PF=INF TP-hit=0.0% SL=0.0%

## Interaction: method × HTF trend × 5m pre-signal impulse
- MIX | NOT_BOTH | ALIGNED: N=2, EV=0.4250R, PF=INF, WR=100.0%
- DOM | NOT_BOTH | COUNTER: N=41, EV=0.1333R, PF=1.537, WR=63.4%
- BASE | NOT_BOTH | COUNTER: N=53, EV=0.0073R, PF=1.026, WR=56.6%
- MIX | NOT_BOTH | COUNTER: N=47, EV=-0.2361R, PF=0.450, WR=38.3%
- BASE | NOT_BOTH | ALIGNED: N=1, EV=-0.2824R, PF=0.000, WR=0.0%
- REV | NOT_BOTH | COUNTER: N=11, EV=-0.4752R, PF=0.045, WR=18.2%

## Precision proxy: TP0.5R before SL within 5m
- MIX: TP0.5 hit=75.0%, SL=0.0%, EV=0.4554R
- BASE: TP0.5 hit=0.0%, SL=0.0%, EV=-0.3624R

## Notes
- H1/H4 trend = completed GC bars only; EMA20 + 3-bar EMA slope, aligned to signal side.
- Impulse = signed pre-signal GC price change normalized by causal M1 ATR14.
- Exit grid keeps original 1R stop and varies only TP and max hold.
- Same-minute TP/SL collision is counted as SL first (conservative).
- Commission-only EV is available in calculation; spread/slippage are not reconstructed by GC proxy.
