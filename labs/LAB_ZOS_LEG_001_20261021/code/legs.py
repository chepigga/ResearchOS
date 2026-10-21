"""LAB-ZOS-LEG-001 (pre-registered): candidate complementary legs for ZOS_Multi (A+D+F), XAUUSD 2022-06..2026-09-08.
Risk 0.27% of $100k per trade ($270 = 1R). Costs: one mean spread per trade (bid data; spread in points*0.01).
L1 DRIFT40: flat-only, at M5 open: dir = sign(close_D[-1] - close_D[-41]) if |.|/(ATR_D14*sqrt(40)) >= 0.5; SL = k*ATR14(M5), k=4|6; exit SL or 24h.
L2 DONCH20: D1 close breaks 20-day high/low -> next D1 open; SL 2*ATR_D14; exit on close beyond 10-day opposite channel; one position.
L3 DRIFT40-H1: as L1 but evaluated only at H1 opens and SL 3*ATR14(H1), 48h.
Report: own EV(R), trades/mo, monthly corr with ZOS, P/L in ZOS losing months, portfolio ZOS+leg: negative months, worst month, maxDD."""
import pandas as pd,numpy as np
m5=pd.read_pickle("m5.pkl"); h1=pd.read_pickle("h1.pkl"); d1=pd.read_pickle("d1.pkl"); d1=d1[d1.index.dayofweek<5]
d1["atr"]=(d1.high-d1.low).rolling(14).mean()
T=pd.read_pickle("/tmp/claude-0/-home-claude/879a62a8-009b-5e46-ab07-25d07c2b7f01/scratchpad/zos2/r1.xlsx.pkl")
Z=T.groupby(T.xt.dt.to_period("M")).net.sum()
RISK=270.0
def atr(b,n=14):
    pc=b.close.shift(); tr=np.maximum(b.high-b.low,np.maximum((b.high-pc).abs(),(b.low-pc).abs())); return tr.rolling(n).mean().shift(1)
def drift_dir(idx):
    # direction known at start of day: uses D1 closes up to previous day
    dd=d1.close; mom=(dd-dd.shift(40))/(d1.atr*np.sqrt(40)); s=np.where(mom>=0.5,1,np.where(mom<=-0.5,-1,0))
    ser=pd.Series(s,index=d1.index).shift(1)   # yesterday's close info for today
    return ser.reindex(idx.normalize()).to_numpy()
def run_drift(b,k,hold_bars):
    A=atr(b).to_numpy(); D=drift_dir(b.index); o=b.open.to_numpy(); h=b.high.to_numpy(); l=b.low.to_numpy(); c=b.close.to_numpy(); sp=b.spread.to_numpy()*0.01
    out=[]; i=200; n=len(b)
    while i<n-hold_bars-1:
        d=D[i]
        if not np.isfinite(d) or d==0 or not np.isfinite(A[i]): i+=1; continue
        e=o[i]; R=k*A[i]; stp=e-d*R; x=None
        for j in range(i,i+hold_bars):
            if (l[j]<=stp) if d>0 else (h[j]>=stp): pnl=-R; x=j; break
        if x is None: x=i+hold_bars-1; pnl=d*(c[x]-e)
        out.append((b.index[x],(pnl-sp[i])/R)); i=x+1
    return pd.DataFrame(out,columns=["t","R"])
def run_donch():
    hh=d1.high.rolling(20).max().shift(1); ll=d1.low.rolling(20).min().shift(1); h10=d1.high.rolling(10).max().shift(1); l10=d1.low.rolling(10).min().shift(1)
    out=[]; pos=0; e=R=stp=0; idx=d1.index
    for i in range(30,len(d1)-1):
        c=d1.close.iloc[i]
        if pos!=0:
            hit=(d1.low.iloc[i]<=stp) if pos>0 else (d1.high.iloc[i]>=stp)
            if hit: out.append((idx[i],-1-0.3/R)); pos=0; continue
            if (pos>0 and c<l10.iloc[i]) or (pos<0 and c>h10.iloc[i]):
                x=d1.open.iloc[i+1]; out.append((idx[i+1],(pos*(x-e)-0.3)/R)); pos=0; continue
        else:
            if c>hh.iloc[i] or c<ll.iloc[i]:
                pos=1 if c>hh.iloc[i] else -1; e=d1.open.iloc[i+1]; R=2*d1.atr.iloc[i]; stp=e-pos*R
    return pd.DataFrame(out,columns=["t","R"])
legs={"L1 дрейф40 M5 SL4 24г":run_drift(m5,4,288),"L1 дрейф40 M5 SL6 24г":run_drift(m5,6,288),
      "L3 дрейф40 H1 SL3 48г":run_drift(h1,3,48),"L2 Donchian20 D1":run_donch()}
months=pd.period_range("2022-06","2026-08",freq="M")
z=Z.reindex(months).fillna(0)
def stats(s):
    eq=s.cumsum(); dd=(eq.cummax()-eq).max(); return dict(сума=round(s.sum()),мінус_міс=int((s<0).sum()),гірший=round(s.min()),макс_DD=round(dd))
rows=[dict(нога="ZOS сам (A+D+F)",угод_міс=np.nan,EV_R=np.nan,**stats(z))]
for nm,t in legs.items():
    mo=(t.groupby(t.t.dt.to_period("M")).R.sum()*RISK).reindex(months).fillna(0)
    lose=z<0
    r=dict(нога=nm,угод_міс=round(len(t)/len(months),1),EV_R=round(t.R.mean(),3),корел=round(np.corrcoef(mo,z)[0,1],2),
           у_мінус_міс_ZOS=round(mo[lose].sum()),у_плюс_міс_ZOS=round(mo[~lose].sum()),**{"нога_"+k:v for k,v in stats(mo).items()})
    p=stats(z+mo); r.update({"разом_"+k:v for k,v in p.items()})
    h1m=mo[mo.index<pd.Period("2024-07","M")].sum(); h2m=mo[mo.index>=pd.Period("2024-07","M")].sum(); r["H1/H2"]=f"{round(h1m)}/{round(h2m)}"
    rows.append(r)
pd.set_option("display.width",300); print(pd.DataFrame(rows).to_string(index=False))
