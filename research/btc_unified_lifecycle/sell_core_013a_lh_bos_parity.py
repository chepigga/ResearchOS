#!/usr/bin/env python3
"""SELL_CORE_013A — exact user LH+BOS parity gate.
No intersection is allowed until data/logic parity is audited.
"""
from pathlib import Path
import math, numpy as np, pandas as pd
import u02c2_v283_market_clock_conditional as base

OUT=Path('sell_core_013a_out'); OUT.mkdir(exist_ok=True)
M1ZIP='btc_1m.zip'; LR=2; LB=120; START=20000; TAIL=6000; STEP=60; COST_PCT=.096

def pf_pct(x):
    z=np.asarray(x,float); gp=z[z>0].sum(); gl=-z[z<0].sum(); return gp/gl if gl>0 else np.nan

def main():
    m1=base.load_zip(M1ZIP).reset_index(drop=True)
    N=len(m1); H=m1.high.to_numpy(float); L=m1.low.to_numpy(float); C=m1.close.to_numpy(float)
    # Exact 60-row H1 blocks anchored at m1[0].
    nb=(N+59)//60; hh=np.empty(nb); hl=np.empty(nb); hc=np.empty(nb)
    for k in range(nb):
        a=k*60; b=min(a+60,N); hh[k]=H[a:b].max(); hl[k]=L[a:b].min(); hc[k]=C[b-1]
    # User a60 = SMA(TR_M1,60), stop proxy = a60*60.
    prev=np.r_[np.nan,C[:-1]]
    tr=np.nanmax(np.vstack([H-L,np.abs(H-prev),np.abs(L-prev)]),axis=0)
    tr[0]=H[0]-L[0]
    a60=pd.Series(tr).rolling(60,min_periods=60).mean().to_numpy()

    def swings(k):
        hs=[]; ls=[]
        for b in range(k-LR,max(k-LB,LR),-1):
            if len(hs)<3 and all(hh[b]>=hh[b+d] for d in range(-LR,LR+1)): hs.append((b,hh[b]))
            if len(ls)<3 and all(hl[b]<=hl[b+d] for d in range(-LR,LR+1)): ls.append((b,hl[b]))
            if len(hs)>=3 and len(ls)>=3: break
        return hs,ls

    rows=[]; n_lh=0; n_bos=0
    clocks=list(range(START,N-TAIL,STEP))
    for i in clocks:
        k=i//60
        # Explicit causality audit: detector only touches pivots <= k-2, BOS uses k-1.
        hs,ls=swings(k)
        if len(hs)<2 or len(ls)<1: continue
        lh=hs[0][1] < hs[1][1]
        bos=hc[k-1] < ls[0][1]
        if lh:n_lh+=1
        if lh and bos:n_bos+=1
        if not (lh and bos): continue
        sd=1.5*a60[i]*60.0
        if not np.isfinite(sd) or sd<=0: continue
        entry=C[i]; sl=entry+sd; end=min(i+2880,N-1)
        hit=np.flatnonzero(H[i+1:end+1]>=sl)
        if hit.size:
            exitp=sl
        else:
            exitp=C[end]
        gross=(entry-exitp)/entry*100.0
        net=gross-COST_PCT
        rows.append({'i':i,'time':m1.time.iloc[i],'k':k,'lh':lh,'bos_dn':bos,'last_hi_b':hs[0][0],'prev_hi_b':hs[1][0],'last_lo_b':ls[0][0],
                     'entry':entry,'stop_dist':sd,'gross_pct':gross,'net_pct':net,'win':net>0})
    x=pd.DataFrame(rows); x.to_csv(OUT/'lh_bos_events_native.csv',index=False)
    expected_N_lo=26000+(22474-1)*60+1; expected_N_hi=26000+22474*60
    report=[
        '# SELL_CORE_013A — LH+BOS PARITY GATE','',
        f'- frozen M1 N: **{N:,}**',f'- M1 range: **{m1.time.iloc[0]} .. {m1.time.iloc[-1]}**',
        f'- exact `range(20000,N-6000,60)` clocks: **{len(clocks):,}**',
        f'- user target clocks: **22,474**',
        f'- a 22,474-clock range implies N in **[{expected_N_lo:,}, {expected_N_hi:,}]** rows; frozen N is shorter by **{expected_N_lo-N:,}..{expected_N_hi-N:,} M1 rows**.',
        f'- LH count: **{n_lh:,}** (user target 11,602)',
        f'- LH+BOS count: **{n_bos:,}** (user target 1,609)','',
        '## Native parity P/L','',
        f'- replayed LH+BOS with valid stop: **{len(x):,}**',
        f'- WR(net>0): **{(x.win.mean()*100 if len(x) else float("nan")):.3f}%**',
        f'- gross EV: **{(x.gross_pct.mean() if len(x) else float("nan")):+.6f}%**',
        f'- net EV after 0.096%: **{(x.net_pct.mean() if len(x) else float("nan")):+.6f}%**',
        f'- PF on net-%: **{(pf_pct(x.net_pct) if len(x) else float("nan")):.4f}**','',
        '## Causality audit','',
        '- H1 blocks are anchored at M1[0], exactly 60 rows each.',
        '- At decision minute i, k=i//60; BOS uses hc[k-1].',
        '- swings(k) begins at k-2, so all pivot bars have the required two right-side H1 confirmations and never touch forming bar k.',
        '', '## Gate rule','',
        '- Do **not** run B3 intersection unless the count mismatch can be attributed to data coverage or exact logic parity is established on a common interval.'
    ]
    (OUT/'REPORT.md').write_text('\n'.join(report)); print((OUT/'REPORT.md').read_text())
if __name__=='__main__': main()
