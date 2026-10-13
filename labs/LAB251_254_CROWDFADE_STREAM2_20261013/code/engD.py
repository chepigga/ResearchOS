"""LAB254 — Stream-2 engine D. Frozen before run:
signal at M5 close i: |z6| crosses >=2 (prev <2), sign(z24)==sign(z6) & |z24|>=1, H4 trend (last closed, EMA50 rule) == side, side=-sign(z6).
One entry per episode (re-arm after |z6|<1). Entry open of bar i+1+delay. Exits: SL2/48h, SL3/48h, SL3/24h time exits.
Portfolio rules inside engine: max 2, 2nd same side & MTM>=0. Cost 7.5bps. Risk: D 0.10%, v157 0.25% (canonical LOCK2_LOCK025)."""
import os
os.environ["LAB_CACHE"]="/home/claude/lab251/cache_full.pkl"
import numpy as np, pandas as pd
import zwin as Wm, lab251 as L
BT,BO,BH,BL,BC,BA,N=L.BT,L.BO,L.BH,L.BL,L.BC,L.BA,L.N
TE=pd.Timestamp("2025-01-01",tz="UTC"); COST=7.5
z6=Wm.Z["6 год (поточне)"]; z24=Wm.Z["24 год"]
s=pd.Series(BC,index=BT); h4=s.resample("4h").last().dropna(); e50=h4.ewm(span=50,adjust=False).mean()
tr4=pd.Series(np.where((h4>e50)&(e50>e50.shift(6)),1,np.where((h4<e50)&(e50<e50.shift(6)),-1,0)),index=h4.index)
x=tr4.copy(); x.index=x.index+pd.Timedelta("4h"); TR4=x.reindex(BT,method="ffill").to_numpy()
def signals():
    out=[]; armed=True
    for i in range(1,N-1000):
        if not np.isfinite(z6[i]): continue
        if abs(z6[i])<1: armed=True; continue
        if armed and abs(z6[i])>=2 and abs(z6[i-1])<2:
            sd=-int(np.sign(z6[i]))
            if np.isfinite(z24[i]) and np.sign(z24[i])==np.sign(z6[i]) and abs(z24[i])>=1 and TR4[i]==sd:
                out.append((i,sd)); armed=False
    return out
SIG=signals()
def sim(delay,k,H):
    sig={}
    for i,sd in SIG:
        e=i+1+delay; sig.setdefault(e,[]).append(sd)
    idx=sorted(sig); act=[]; done=[]; eq=[]; real=0.0; p=0; i=idx[0]
    def mtm(q,px): return q["s"]*(px-q["e"])/q["R"]-q["c"]
    while i<N:
        for sd in sig.get(i,[]):
            if len(act)==0 or (len(act)==1 and act[0]["s"]==sd and mtm(act[0],BO[i])>=0):
                e=BO[i]; R=k*BA[i]; act.append(dict(s=sd,e=e,R=R,c=COST/1e4*e/R,end=min(i+H*12-1,N-1),i0=i))
        keep=[]
        for q in act:
            sp=q["e"]-q["s"]*q["R"]; res=None
            if (BL[i]<=sp) if q["s"]>0 else (BH[i]>=sp): res=-1.0
            elif i>=q["end"]: res=q["s"]*(BC[i]-q["e"])/q["R"]
            if res is None: keep.append(q)
            else: net=res-q["c"]; real+=net; done.append(dict(entry_time=BT[q["i0"]],exit_time=BT[i],net_r=net,side=q["s"]))
        act=keep; eq.append((BT[i],real+sum(mtm(q,BC[i]) for q in act)))
        if act: i+=1
        else:
            while p<len(idx) and idx[p]<=i: p+=1
            if p>=len(idx): break
            i=idx[p]
    t=pd.DataFrame(done); e=pd.Series([v for _,v in eq],index=pd.DatetimeIndex([a for a,_ in eq]))
    return t,e
def seg_stats(t,e,seg,risk):
    m=(t.entry_time<TE) if seg=="TRAIN" else (t.entry_time>=TE); tt=t[m]
    em=(e.index<TE) if seg=="TRAIN" else (e.index>=TE); ee=e[em]; ee=ee-ee.iloc[0]
    mo=48 if seg=="TRAIN" else 19.3
    dd=float((ee.cummax()-ee).max())
    return dict(trades_mo=len(tt)/mo,ev=tt.net_r.mean(),wr=(tt.net_r>0).mean(),r_mo=tt.net_r.sum()/mo,dd_r=dd,dd_pct=dd*risk,r_dd=tt.net_r.sum()/dd if dd>0 else np.nan,pct_mo=tt.net_r.sum()/mo*risk)
print("signals:",len(SIG),"| TRAIN/mo",round(sum(BT[i]<TE for i,_ in SIG)/48,1),"OOS/mo",round(sum(BT[i]>=TE for i,_ in SIG)/19.3,1))
rows=[]; store={}
for delay in [0,1,2]:
    for k,H in [(2,48),(3,48),(3,24)]:
        t,e=sim(delay,k,H); store[(delay,k,H)]=(t,e)
        for sg in ["TRAIN","OOS"]:
            d=seg_stats(t,e,sg,0.10); d.update(delay=delay,exit=f"SL{k} {H}h",seg=sg); rows.append(d)
R=pd.DataFrame(rows); pd.set_option("display.width",260)
print(R.pivot_table(index=["delay","exit"],columns="seg",values=["trades_mo","ev","wr","r_mo","dd_r","r_dd"]).round(2).to_string())
# choose exit on TRAIN (delay 0) by r_dd
tr=R[(R.delay==0)&(R.seg=="TRAIN")].sort_values("r_dd",ascending=False); best=tr.iloc[0]["exit"]; print("\nCHOSEN on TRAIN:",best)
k,H=int(best[2]),int(best.split()[1][:-1])
# portfolio with v157 canonical
tv,ev,_,_=L.replay(7.5,{},dict(mtr=np.zeros(N,int),ci=np.zeros(N,int),swl=None,swh=None,catr=None))
evs=pd.Series(ev.equity_r.to_numpy(),index=pd.DatetimeIndex(ev.time))
def daily(e): return e.groupby(e.index.floor("D")).last()
out=[]
for delay in [0,1,2]:
    td,ed=store[(delay,k,H)]
    for sg in ["TRAIN","OOS"]:
        def cut(e): 
            e=daily(e); e=e[(e.index<TE) if sg=="TRAIN" else (e.index>=TE)]; return e-e.iloc[0]
        V=cut(evs)*0.25; D=cut(ed)*0.10
        idx=V.index.union(D.index); V=V.reindex(idx).ffill().fillna(0); D=D.reindex(idx).ffill().fillna(0); P=V+D
        mo=48 if sg=="TRAIN" else 19.3
        for nm,ser in [("v157 0.25%",V),("D 0.10%",D),("v157+D",P)]:
            dd=float((ser.cummax()-ser).max()); out.append(dict(delay=delay,seg=sg,book=nm,pct_mo=ser.iloc[-1]/mo,dd_pct=dd,ret_dd=ser.iloc[-1]/dd if dd>0 else np.nan))
O=pd.DataFrame(out)
print(O.pivot_table(index=["delay","book"],columns="seg",values=["pct_mo","dd_pct","ret_dd"],sort=False).round(2).to_string())
td,_=store[(0,k,H)]; td.to_csv("out_oos/ENGINE_D_TRADES.csv",index=False); R.to_csv("out_oos/ENGINE_D_GRID.csv",index=False); O.to_csv("out_oos/ENGINE_D_PORTFOLIO.csv",index=False)
print(td.groupby(td.entry_time.dt.year).net_r.agg(["count","mean","sum"]).round(2))
