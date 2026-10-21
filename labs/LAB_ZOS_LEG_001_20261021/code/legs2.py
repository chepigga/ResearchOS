"""LAB_ZOS_LEG_002 (pre-registered): candidate legs incl. Oct-2026. XAUUSD 2022-06..2026-10-21, risk 0.27% ($270=1R), cost 1 spread/trade.
DRIFT(lb,k,H): H1 bars, flat-only, dir=sign(D1 close - close lb days ago) if |.|/(ATR_D*sqrt(lb))>=0.5 (yesterday's info), SL k*ATR14(H1), exit SL/H hours. Main = (40,3,48); robustness lb 20/60, k 2/4.
DONCH20: D1 20-day breakout, SL 2 ATR_D, exit 10-day opposite channel.
REV1D: yesterday |move| >= 1 ATR_D -> fade at today's open, SL 1 ATR_D, exit today's close.
ASIA: Asian range 01-08 server; 08-13 M15 close back inside after poking out -> fade, SL extreme+0.1ATR_H1 (min 0.3), TP opposite side of range, exit 20:00.
W1MOM: Monday open, dir=sign(4-week return), SL 1.5*ATR_W8, exit Friday close."""
import pandas as pd,numpy as np
m15=pd.read_pickle("m15.pkl"); h1=pd.read_pickle("h1.pkl"); d1=pd.read_pickle("d1.pkl"); d1=d1[d1.index.dayofweek<5].copy()
d1["atr"]=(d1.high-d1.low).rolling(14).mean().shift(1)
T=pd.read_pickle("/tmp/claude-0/-home-claude/879a62a8-009b-5e46-ab07-25d07c2b7f01/scratchpad/zos2/r1.xlsx.pkl")
Z=T.groupby(T.xt.dt.to_period("M")).net.sum(); RISK=270.0
months=pd.period_range("2022-07","2026-10",freq="M"); z=Z.reindex(months).fillna(0)
def atr(b,n=14):
    pc=b.close.shift(); tr=np.maximum(b.high-b.low,np.maximum((b.high-pc).abs(),(b.low-pc).abs())); return tr.rolling(n).mean().shift(1)
def ddir(idx,lb):
    dd=d1.close; mom=(dd-dd.shift(lb))/(d1.atr*np.sqrt(lb)); s=pd.Series(np.where(mom>=0.5,1,np.where(mom<=-0.5,-1,0)),index=d1.index).shift(1)
    return s.reindex(idx.normalize()).to_numpy()
def drift(lb,k,H):
    b=h1; A=atr(b).to_numpy(); D=ddir(b.index,lb); o,h,l,c=[b[x].to_numpy() for x in "open high low close".split()]; sp=b.spread.to_numpy()*0.01
    out=[]; i=300; n=len(b)
    while i<n-H-1:
        d=D[i]
        if not np.isfinite(d) or d==0 or not np.isfinite(A[i]): i+=1; continue
        e=o[i]; R=k*A[i]; stp=e-d*R; x=None
        for j in range(i,i+H):
            if (l[j]<=stp) if d>0 else (h[j]>=stp): pnl=-R; x=j; break
        if x is None: x=i+H-1; pnl=d*(c[x]-e)
        out.append((b.index[x],(pnl-sp[i])/R)); i=x+1
    return pd.DataFrame(out,columns=["t","R"])
def donch():
    hh=d1.high.rolling(20).max().shift(1); ll=d1.low.rolling(20).min().shift(1); h10=d1.high.rolling(10).max().shift(1); l10=d1.low.rolling(10).min().shift(1)
    out=[]; pos=0; idx=d1.index
    for i in range(30,len(d1)-1):
        c=d1.close.iloc[i]
        if pos!=0:
            if (d1.low.iloc[i]<=stp) if pos>0 else (d1.high.iloc[i]>=stp): out.append((idx[i],-1-0.3/R)); pos=0; continue
            if (pos>0 and c<l10.iloc[i]) or (pos<0 and c>h10.iloc[i]):
                x=d1.open.iloc[i+1]; out.append((idx[i+1],(pos*(x-e)-0.3)/R)); pos=0; continue
        elif c>hh.iloc[i] or c<ll.iloc[i]:
            pos=1 if c>hh.iloc[i] else -1; e=d1.open.iloc[i+1]; R=2*d1.atr.iloc[i+1]; stp=e-pos*R
    return pd.DataFrame(out,columns=["t","R"])
def rev1d():
    out=[]
    for i in range(20,len(d1)):
        p=d1.iloc[i-1]; a=d1.atr.iloc[i]; mv=p.close-p.open
        if not np.isfinite(a) or abs(mv)<a: continue
        d=-np.sign(mv); g=d1.iloc[i]; e=g.open; R=a; stp=e-d*R
        hit=(g.low<=stp) if d>0 else (g.high>=stp)
        pnl=-R if hit else d*(g.close-e); out.append((d1.index[i],(pnl-0.3)/R))
    return pd.DataFrame(out,columns=["t","R"])
def asia():
    b=m15; A=atr(h1).reindex(b.index,method="ffill").to_numpy(); out=[]
    for day,g in b.groupby(b.index.normalize()):
        a=g[(g.index.hour>=1)&(g.index.hour<8)]
        if len(a)<20: continue
        ah,al=a.high.max(),a.low.min(); w=g[(g.index.hour>=8)&(g.index.hour<13)]; done=False
        for k in range(1,len(w)):
            r=w.iloc[k]; ex=w.iloc[:k+1]
            for d,cond,ext,tp in ((-1,ex.high.max()>ah and r.close<ah,ex.high.max(),al),(1,ex.low.min()<al and r.close>al,ex.low.min(),ah)):
                if not cond: continue
                ia=b.index.get_loc(w.index[k]); atrh=A[ia]
                if not np.isfinite(atrh): continue
                e=b.open.iloc[ia+1]; stp=ext-d*0.1*atrh; R=max(d*(e-stp),0.3*atrh); stp=e-d*R
                rest=b.iloc[ia+1:]; rest=rest[rest.index<day+pd.Timedelta("20h")]; pnl=None
                for rr in rest.itertuples():
                    if (rr.low<=stp) if d>0 else (rr.high>=stp): pnl=-R; break
                    if (rr.high>=tp) if d>0 else (rr.low<=tp): pnl=d*(tp-e); break
                if pnl is None: pnl=d*(rest.close.iloc[-1]-e) if len(rest) else 0
                out.append((day,(pnl-b.spread.iloc[ia]*0.01)/R)); done=True; break
            if done: break
    return pd.DataFrame(out,columns=["t","R"])
def w1mom():
    w=d1.resample("W-FRI").agg({"open":"first","high":"max","low":"min","close":"last"}).dropna(); w["atr"]=(w.high-w.low).rolling(8).mean().shift(1)
    out=[]
    for i in range(10,len(w)):
        d=np.sign(w.close.iloc[i-1]-w.close.iloc[i-5]); a=w.atr.iloc[i]
        if d==0 or not np.isfinite(a): continue
        e=w.open.iloc[i]; R=1.5*a; stp=e-d*R; hit=(w.low.iloc[i]<=stp) if d>0 else (w.high.iloc[i]>=stp)
        pnl=-R if hit else d*(w.close.iloc[i]-e); out.append((w.index[i],(pnl-0.3)/R))
    return pd.DataFrame(out,columns=["t","R"])
legs={"ДРЕЙФ H1 40д SL3 48г":drift(40,3,48),"дрейф 20д":drift(20,3,48),"дрейф 60д":drift(60,3,48),"дрейф 40д SL2":drift(40,2,48),"дрейф 40д SL4":drift(40,4,48),
      "Donchian20 D1":donch(),"Розворот після сильного дня":rev1d(),"Азійський діапазон: фейк-пробій":asia(),"Тижневий імпульс W1":w1mom()}
def st(s):
    eq=s.cumsum(); return dict(сума=round(s.sum()),мінус=int((s<0).sum()),гірший=round(s.min()),DD=round((eq.cummax()-eq).max()))
rows=[dict(нога="ZOS сам",**{"разом_"+k:v for k,v in st(z).items()},жовтень26=round(z[pd.Period("2026-10","M")]))]
for nm,t in legs.items():
    mo=(t.groupby(pd.to_datetime(t.t).dt.to_period("M")).R.sum()*RISK).reindex(months).fillna(0); lose=z<0
    h1s=mo[mo.index<pd.Period("2024-09","M")].sum(); h2s=mo[mo.index>=pd.Period("2024-09","M")].sum()
    rows.append(dict(нога=nm,угод_міс=round(len(t)/len(months),1),EV=round(t.R.mean(),3),нога_сума=round(mo.sum()),пол1_пол2=f"{h1s:+.0f}/{h2s:+.0f}",
        кор=round(np.corrcoef(mo,z)[0,1],2),у_мінус_ZOS=round(mo[lose].sum()),жовтень26=round(mo[pd.Period("2026-10","M")]),
        **{"разом_"+k:v for k,v in st(z+mo).items()}))
pd.set_option("display.width",320); print(pd.DataFrame(rows).to_string(index=False))
