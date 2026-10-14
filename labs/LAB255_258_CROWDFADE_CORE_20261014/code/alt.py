"""LAB257 — engine D on ETH/SOL (frozen BTC rules, no retuning).
Price proxy: Binance futures OI value / OI at each 5-min snapshot (BTC check: median 1.4 bps vs real open).
Bars: open=px[t], close=px[t+5m], high/low=max/min(open,close) (no intrabar extremes) -> stops checked on closes, filled at close (conservative).
ATR: H1 Wilder ATR14 from proxy H1 bars, last closed hour."""
import numpy as np,pandas as pd
def load(path):
    f=pd.read_csv(path); f["t"]=pd.to_datetime(f.create_time,utc=True); f=f.drop_duplicates("t").set_index("t").sort_index()
    px=(f.sum_open_interest_value.astype(float)/f.sum_open_interest.astype(float))
    px=px.where(np.isfinite(px)&(px>0))
    for _ in range(3):  # remove one/two-bar spikes in proxy (bad OI snapshots)
        p=px.dropna(); lr=np.log(p).diff(); nx=lr.shift(-1)
        spike=(lr.abs()>0.03)&(lr*nx<0)&((lr+nx).abs()<0.3*lr.abs())
        px.loc[spike[spike].index]=np.nan
    px=px.dropna()
    grid=pd.date_range(f.index[0],f.index[-1],freq="5min")
    have=pd.Series(1.0,index=px.index).reindex(grid).fillna(0).to_numpy(); px=px.reindex(grid).ffill(); r=f.count_long_short_ratio.astype(float).reindex(grid).ffill()
    o=px.to_numpy(); c=np.r_[o[1:],o[-1]]
    T=grid; H=np.maximum(o,c); L=np.minimum(o,c)
    d=pd.DataFrame({"h":H,"l":L,"c":c},index=T); h1=d.resample("1h").agg({"h":"max","l":"min","c":"last"}).dropna()
    tr=np.maximum(h1.h-h1.l,np.maximum((h1.h-h1.c.shift()).abs(),(h1.l-h1.c.shift()).abs()))
    atr=tr.ewm(alpha=1/14,adjust=False).mean(); atr.index=atr.index+pd.Timedelta("1h")
    A=atr.reindex(T,method="ffill").to_numpy()/0.769  # calibrated on BTC: proxy ATR = 0.769 x real H1 ATR
    def z(w): m=r.rolling(w).mean(); s=r.rolling(w).std(ddof=0); return ((r-m)/s).to_numpy()
    s=pd.Series(c,index=T); h4=s.resample("4h").last().dropna(); e=h4.ewm(span=50,adjust=False).mean()
    t4=pd.Series(np.where((h4>e)&(e>e.shift(6)),1,np.where((h4<e)&(e<e.shift(6)),-1,0)),index=h4.index); t4.index=t4.index+pd.Timedelta("4h")
    miss=pd.Series(1-have); run=miss.groupby((miss==0).cumsum()).cumsum(); big=(run>=6).astype(float)  # gap >=30 min
    gap=big.rolling(864,min_periods=1).max().to_numpy()  # stale data in last 72h
    bad=np.maximum(gap,big[::-1].reset_index(drop=True).rolling(600,min_periods=1).max().to_numpy()[::-1])  # or within next ~50h
    return dict(BAD=bad,T=T,O=o,H=H,L=L,C=c,A=A,z6=z(72),z24=z(288),TR4=t4.reindex(T,method="ffill").fillna(0).to_numpy())
def signals(M,x=2.0,zmin=1.0,trend=True):
    z6,z24,TR4=M["z6"],M["z24"],M["TR4"]; N=len(z6); out=[]; armed=True; ep=None; used=set()
    for i in range(300,N-2):
        v=z6[i]
        if not np.isfinite(v): continue
        if abs(v)<1: ep=None; continue
        if ep is None or np.sign(v)!=np.sign(z6[ep]): ep=i
        if ep in used or not(abs(v)>=x and abs(z6[i-1])<x): continue
        sd=-int(np.sign(v))
        if not(np.isfinite(z24[i]) and -np.sign(z24[i])==sd and abs(z24[i])>=zmin): continue
        if trend and M["TR4"][i]!=sd: continue
        if M["BAD"][i]>0: continue
        out.append((i,sd)); used.add(ep)
    return out
def sim(M,SIG,cost=7.5,fill="close"):
    O,H,L,C,A,T=M["O"],M["H"],M["L"],M["C"],M["A"],M["T"]; N=len(C)
    sig={}
    for i,sd in SIG: sig.setdefault(i+1,[]).append(sd)
    idx=sorted(sig); act=[]; done=[]; eq=[]; real=0.0; p=0; i=idx[0]
    mt=lambda q,px: q["s"]*(px-q["e"])/q["R"]-q["c"]
    while i<N:
        for sd in sig.get(i,[]):
            if not np.isfinite(A[i]) or A[i]<=0: continue
            if len(act)==0 or (len(act)==1 and act[0]["s"]==sd and mt(act[0],O[i])>=0):
                e=O[i]; R=3*A[i]; act.append(dict(s=sd,e=e,R=R,c=cost/1e4*e/R,end=min(i+575,N-1),i0=i,st=-1.0,pk=0.0))
        keep=[]
        for q in act:
            s_,e,R=q["s"],q["e"],q["R"]; sp=e+s_*q["st"]*R; res=None
            if (L[i]<=sp) if s_>0 else (H[i]>=sp): res=q["st"] if fill=="stop" else s_*(C[i]-e)/R
            else:
                q["pk"]=max(q["pk"],((H[i]-e) if s_>0 else (e-L[i]))/R)
                if q["pk"]>=2: q["st"]=max(q["st"],q["pk"]-3)
                if i>=q["end"]: res=s_*(C[i]-e)/R
            if res is None: keep.append(q)
            else: real+=res-q["c"]; done.append(dict(entry_i=q["i0"],t=T[q["i0"]],net_r=res-q["c"]))
        act=keep; eq.append((T[i],real+sum(mt(q,C[i]) for q in act)))
        if act: i+=1
        else:
            while p<len(idx) and idx[p]<=i: p+=1
            if p>=len(idx): break
            i=idx[p]
    return pd.DataFrame(done),pd.Series([v for _,v in eq],index=pd.DatetimeIndex([a for a,_ in eq]))
