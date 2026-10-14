"""LAB264 (pre-registered): AlgoSignals-style Supertrend EA on BTC x crowd compass.
Signal: Supertrend(src=ohlc4, ATR period 10 RMA, factor=sens) flip at TF bar close ('Confirmed'); entry next TF bar open.
Optional HTF filter: H1 EMA150 vs EMA250 (long only if 150>250, short only if 150<250), last closed H1.
SL = 2.2 x ATR14(TF, Wilder). TP1/2/3 = 1/2/3R. 50% at TP1 -> SL to BE; 25% at TP2 -> SL to TP1; last 25% at TP3.
Opposite flip closes the open position. One position at a time. Path walked on M5 (stop-first intrabar). Cost 7.5bps round trip.
Compass: D2 side for 48h after signal (primary); z24 sign at |z24|>=1 (secondary). States WITH/AGAINST/NONE at signal.
Grid: TF M5/M15/H1 x sens 1.3/1.8 x HTF off/on. Compare ALL vs ONLY-WITH-COMPASS vs SKIP-AGAINST. Choose on 2021-24."""
import numpy as np,pandas as pd
exec(open("sw260.py").read().split("\nrows=[]")[0])
z24=g["z24"]; COST=7.5
T=pd.DatetimeIndex(BT)
comp=np.zeros(N,int); last=-10**9; cs=0; sigd={i:sd for i,sd in SIG}
for i in range(N):
    if i in sigd: cs=sigd[i]; last=i
    comp[i]=cs if i-last<=576 else 0
c24=np.where(np.isfinite(z24)&(np.abs(z24)>=1),-np.sign(z24),0).astype(int)
df=pd.DataFrame({"o":BO,"h":BH,"l":BL,"c":BC},index=T)
h1=df.resample("1h").agg({"o":"first","h":"max","l":"min","c":"last"}).dropna()
d150=(h1.c.ewm(span=150,adjust=False).mean()>h1.c.ewm(span=250,adjust=False).mean()).astype(int)*2-1
d150.index=d150.index+pd.Timedelta("1h"); HTF=d150.reindex(T,method="ffill").fillna(0).to_numpy()
def rma(x,n): return pd.Series(x).ewm(alpha=1/n,adjust=False).mean().to_numpy()
def signals(tf,sens):
    b=df.resample(tf).agg({"o":"first","h":"max","l":"min","c":"last"}).dropna()
    o,h,l,c=[b[k].to_numpy() for k in "ohlc"]; src=(o+h+l+c)/4
    pc=np.r_[c[0],c[:-1]]; tr=np.maximum(h-l,np.maximum(abs(h-pc),abs(l-pc)))
    a10=rma(tr,10); a14=rma(tr,14)
    up=src-sens*a10; dn=src+sens*a10; fu=up.copy(); fd=dn.copy(); d=np.ones(len(c),int)
    for k in range(1,len(c)):
        fu[k]=max(up[k],fu[k-1]) if c[k-1]>fu[k-1] else up[k]
        fd[k]=min(dn[k],fd[k-1]) if c[k-1]<fd[k-1] else dn[k]
        if d[k-1]==-1 and c[k]>fd[k-1]: d[k]=1
        elif d[k-1]==1 and c[k]<fu[k-1]: d[k]=-1
        else: d[k]=d[k-1]
    close_t=b.index+pd.Timedelta(tf)
    m5=np.searchsorted(T.values,close_t.values)        # first M5 bar at/after TF close = entry bar
    out=[]
    for k in range(30,len(c)):
        if d[k]!=d[k-1] and m5[k]<N-2:
            out.append((m5[k]-1,m5[k],int(d[k]),2.2*a14[k]))
    return out
def sim(sigs,htf,keep):
    """keep(state)->bool decides whether a signal is traded. returns trades df."""
    res=[]; pos=None
    flips=[(si,ei,sd,dist) for si,ei,sd,dist in sigs]
    for n_,(si,ei,sd,dist) in enumerate(flips):
        nxt=flips[n_+1][1] if n_+1<len(flips) else N-1
        if htf and HTF[si]!=sd: continue
        st=comp[si]; state="ЗА" if st==sd else ("ПРОТИ" if st==-sd else "ПОЗА")
        s2=c24[si]; state2="ЗА" if s2==sd else ("ПРОТИ" if s2==-sd else "ПОЗА")
        if not keep(state): continue
        e=BO[ei]; R=dist; c=COST/1e4*e/R
        if R<=0: continue
        stp=e-sd*R; w=1.0; bank=0.0; tp_stage=0; out_r=None
        for i in range(ei,min(nxt,N-1)+1):
            if i==nxt:  # opposite flip: close at that open
                out_r=bank+w*sd*(BO[i]-e)/R; break
            if (BL[i]<=stp) if sd>0 else (BH[i]>=stp): out_r=bank+w*sd*(stp-e)/R; break
            fav=(BH[i]-e)*sd if sd>0 else (e-BL[i])
            if tp_stage==0 and fav>=R: bank+=0.5*1; w=0.5; tp_stage=1; stp=e
            if tp_stage==1 and fav>=2*R: bank+=0.25*2; w=0.25; tp_stage=2; stp=e+sd*R
            if tp_stage==2 and fav>=3*R: bank+=0.25*3; w=0; out_r=bank; break
        if out_r is None: out_r=bank+w*sd*(BC[min(nxt,N-1)]-e)/R
        res.append(dict(si=si,tr=BT[si]<TE,state=state,state2=state2,r=out_r-c,h=(i-ei)/12))
    return pd.DataFrame(res)
def summ(t,mo):
    if len(t)==0: return dict(n=0,ev=np.nan,pf=np.nan,Rmo=0,dd=np.nan,rdd=np.nan)
    cum=t.r.cumsum().to_numpy(); dd=float(np.max(np.maximum.accumulate(np.r_[0,cum])[1:]-cum)); s=t.r.sum()
    return dict(n=len(t)/mo,ev=t.r.mean(),pf=t.r[t.r>0].sum()/max(1e-9,-t.r[t.r<0].sum()),Rmo=s/mo,dd=dd,rdd=s/dd if dd>0 else np.nan)
rows=[]; st_rows=[]
for tf in ("5min","15min","1h"):
    for sens in (1.3,1.8):
        S=signals(tf,sens)
        for htf in (False,True):
            name=f"{ {'5min':'M5','15min':'M15','1h':'H1'}[tf]} sens{sens} HTF{'on' if htf else 'off'}"
            A=sim(S,htf,lambda s:True)
            for seg,m,mo in [("21-24",A.tr,48),("25-26",~A.tr,19.3)]:
                x=A[m]
                for stc in ("state","state2"):
                    for s_,y in x.groupby(stc): st_rows.append(dict(v=name,seg=seg,comp=stc,st=s_,n=len(y)/mo,ev=y.r.mean()))
            for mode,keep in [("усі",lambda s:True),("лише ЗА",lambda s:s=="ЗА"),("без ПРОТИ",lambda s:s!="ПРОТИ")]:
                t=A if mode=="усі" else sim(S,htf,keep)
                r=dict(v=name,mode=mode)
                for seg,m,mo in [("21-24",t.tr,48),("25-26",~t.tr,19.3)]:
                    for k_,v_ in summ(t[m],mo).items(): r[f"{k_} {seg}"]=v_
                rows.append(r)
            print(name,flush=True)
R=pd.DataFrame(rows); S_=pd.DataFrame(st_rows)
R.to_csv("out_oos/LAB264_ST_FILTER.csv",index=False); S_.to_csv("out_oos/LAB264_ST_STATES.csv",index=False)
pd.set_option("display.width",300)
print("\n== EV угоди за станом компаса D2 (2021-24 | 2025-26)")
P=S_[S_.comp=="state"].pivot_table(index="v",columns=["st","seg"],values="ev",sort=False).round(3); print(P.to_string())
print("\n== EV за станом компаса z24")
P=S_[S_.comp=="state2"].pivot_table(index="v",columns=["st","seg"],values="ev",sort=False).round(3); print(P.to_string())
print("\n== фільтр")
print(R[["v","mode","n 21-24","ev 21-24","pf 21-24","Rmo 21-24","rdd 21-24","n 25-26","ev 25-26","pf 25-26","Rmo 25-26","rdd 25-26"]].round(2).to_string(index=False))
