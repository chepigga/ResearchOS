"""LAB273: all engines on full history, profit and trade counts per period and per year.
$ = R x risk% x $100k (no compounding). Risks: A/B3/R48/EARLY 0.25%, D2/S/L 0.10%.
v157 canonical = A+B3+R48+EARLY, 48h runner. v006 = A+B3 (72h runner) + D2 (crowd exit >=+1R) + S (H2, EMA9/20 exit) + L (OI cascade)."""
import numpy as np,pandas as pd,zipfile
exec(open("ct268.py").read().split("\nrows=[]; EQ={}")[0])
L_,TLD,RAW=g["g"]["L"],g["g"]["TLD"],g["g"]["RAW"]
YRS=pd.DatetimeIndex(BT).year.to_numpy()
# ---- v157 canonical and v006 core replays
cols=["source","entry_time","entry_i","side","atr","pri"]
t157,e157,_,_=L_.replay(7.5,{},TLD,raw=RAW[cols].reset_index(drop=True))
tAB,eAB,_,_=L_.replay(7.5,{"runner_h":72},TLD,raw=RAW[RAW.source.isin(["A","B3_HIGH"])][cols].reset_index(drop=True))
def eqs(e): return al(pd.Series(e.equity_r.to_numpy(),index=pd.DatetimeIndex(e.time)))
E157=eqs(e157); EAB=eqs(eAB)
# ---- D2 with crowd exit, S with EMA exit (LAB268 implementations)
tD=run_D(CMP,"PROFIT"); ED=mtm_eq(tD)
tS=run_S(EMAX,"ALWAYS"); ES=mtm_eq(tS)
# ---- L engine (LAB272 chosen)
with zipfile.ZipFile("/home/claude/data/BTCUSDT_flow_2021-01-2026-08.csv.zip") as zf:
    nm=[x for x in zf.namelist() if x.endswith(".csv")][0]; f=pd.read_csv(zf.open(nm))
f["time"]=pd.to_datetime(f.create_time,utc=True); f=f.sort_values("time").drop_duplicates("time").set_index("time")
OI=f.sum_open_interest.astype(float).where(lambda x:x>0).resample("5min").last().reindex(BT,method="ffill").ffill().to_numpy()
oich3=np.r_[np.full(3,np.nan),OI[3:]/OI[:-3]-1]; pch3=np.r_[np.full(3,np.nan),BC[3:]-BC[:-3]]/BA
z6=g["z6"]
state=np.where((np.abs(z6)>=1)&np.isfinite(z24)&(np.sign(z24)==np.sign(z6))&(np.abs(z24)>=0.5),-np.sign(z6),0).astype(int)
SL_=[]; cur=0; used=False
for i in range(400,N-600):
    s=state[i]
    if s!=cur: cur=s; used=False
    if s==0 or used: continue
    if oich3[i]<=-0.01 and s*pch3[i]>=0.3: SL_.append((i,s)); used=True
rowsL=[]; eqL=np.zeros(N); addL=np.zeros(N+1); busy=-1
for i,sd in SL_:
    ei=i+1
    if ei<=busy: continue
    e=BO[ei]; R=2*BA[ei]; c=COST/1e4*e/R; stp=e-sd*R; pk=0.0; x=None
    for j in range(ei,min(ei+144,N-1)):
        if (BL[j]<=stp) if sd>0 else (BH[j]>=stp): r=sd*(stp-e)/R; x=j; break
        pk=max(pk,((BH[j]-e) if sd>0 else (e-BL[j]))/R)
        if pk>=1.5:
            ns=e+sd*(pk-1.5)*R; stp=max(stp,ns) if sd>0 else min(stp,ns)
        eqL[j]+=sd*(BC[j]-e)/R-c
    if x is None: x=min(ei+144,N-1); r=sd*(BC[x]-e)/R
    addL[x]+=r-c; busy=x; rowsL.append(dict(i=ei,r=r-c))
tL=pd.DataFrame(rowsL); EL=pd.Series(np.cumsum(addL[:N])+eqL,index=pd.DatetimeIndex(BT))
# ---- unified trade table
def mk(df,eng,risk,ic,rc): return pd.DataFrame({"eng":eng,"i":df[ic].to_numpy(int),"r":df[rc].to_numpy(float),"risk":risk})
srcmap={"A":"A","B3_HIGH":"B3","R48_HIGH":"R48","EARLY_EPISODE":"EARLY"}
T157=pd.DataFrame({"eng":t157.source.map(srcmap),"i":t157.entry_i.astype(int),"r":t157.net_r,"risk":0.25})
TAB=pd.DataFrame({"eng":tAB.source.map(srcmap),"i":tAB.entry_i.astype(int),"r":tAB.net_r,"risk":0.25})
T6=pd.concat([TAB,mk(tD,"D2",0.10,"i","r"),mk(tS,"S",0.10,"i","r"),mk(tL,"L",0.10,"i","r")])
def per(tt):
    tt=tt.copy(); tt["usd"]=tt.r*tt.risk*1000; tt["seg"]=np.where(BT[tt.i]<TE,"2021-24","2025-26"); tt["yr"]=YRS[tt.i]; return tt
T157=per(T157); T6=per(T6)
MO={"2021-24":48,"2025-26":19.3}
def table(tt,title):
    g_=tt.groupby(["eng","seg"]).agg(угод=("r","size"),WR=("r",lambda x:(x>0).mean()),EV_R=("r","mean"),R=("r","sum"),USD=("usd","sum")).reset_index()
    g_["угод/міс"]=g_.apply(lambda r:r.угод/MO[r.seg],axis=1); g_["$/міс"]=g_.apply(lambda r:r.USD/MO[r.seg],axis=1)
    tot=tt.groupby("seg").agg(угод=("r","size"),USD=("usd","sum")).reset_index(); tot["eng"]="РАЗОМ"; tot["угод/міс"]=tot.apply(lambda r:r.угод/MO[r.seg],axis=1); tot["$/міс"]=tot.apply(lambda r:r.USD/MO[r.seg],axis=1)
    out=pd.concat([g_,tot]); print(f"\n===== {title} ====="); print(out[["eng","seg","угод","угод/міс","WR","EV_R","R","USD","$/міс"]].round(2).to_string(index=False))
    y=tt.pivot_table(index="yr",columns="eng",values="usd",aggfunc="sum").fillna(0); y["РАЗОМ"]=y.sum(axis=1)
    n=tt.pivot_table(index="yr",columns="eng",values="r",aggfunc="size").fillna(0).astype(int); n["РАЗОМ"]=n.sum(axis=1)
    print("\n$ по роках (2026 = 7 міс):"); print(y.round(0).to_string()); print("\nугод по роках:"); print(n.to_string())
table(T157,"v157 канонічна (A+B3+R48+EARLY, 48 год), $100k")
table(T6,"v006 (A+B3 72 год + D2 + S + L), $100k")
# drawdown of portfolios (MTM, % of $100k)
P157=E157*0.25; P6=EAB*0.25+ED*0.10+ES*0.10+EL*0.10
for nm_,P in [("v157",P157),("v006",P6)]:
    for seg,m in [("2021-24",pd.DatetimeIndex(BT)<TE),("2025-26",pd.DatetimeIndex(BT)>=TE)]:
        x=P[m]-P[m].iloc[0]; print(f"{nm_} {seg}: прибуток {x.iloc[-1]:.1f}% , макс. просадка {float((x.cummax()-x).max()):.2f}% (MTM)")
T6.to_csv("out_oos/LAB273_ALL_TRADES_v006.csv",index=False); T157.to_csv("out_oos/LAB273_ALL_TRADES_v157.csv",index=False)
