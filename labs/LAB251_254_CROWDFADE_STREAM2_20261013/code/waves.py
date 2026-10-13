import os, json
os.environ["LAB_CACHE"]="/home/claude/lab251/cache_full.pkl"
import numpy as np, pandas as pd
import lab251 as L
BT,BO,BH,BL,BC,BA,N=L.BT,L.BO,L.BH,L.BL,L.BC,L.BA,L.N; BZ=np.asarray(L.C["BZ"],float)
oi=np.load("oi.npy")
# H1 bars (UTC)
df=pd.DataFrame({"h":BH,"l":BL,"c":BC,"a":BA,"z":BZ,"oi":oi},index=BT)
h1=df.resample("1h").agg({"h":"max","l":"min","c":"last","a":"last","z":"last","oi":"last"}).dropna()
# zigzag on closes with reversal >= K * ATR(at pivot)
K=6.0
piv=[(0,h1.c.iloc[0])]; d=0; ext_i=0; ext_p=h1.c.iloc[0]
C=h1.c.to_numpy(); A=h1.a.to_numpy()
for i in range(1,len(h1)):
    p=C[i]
    if d>=0:
        if p>ext_p: ext_p,ext_i=p,i
        elif ext_p-p>=K*A[ext_i] :
            piv.append((ext_i,ext_p)); d=-1; ext_p,ext_i=p,i; continue
    if d<=0:
        if p<ext_p: ext_p,ext_i=p,i
        elif p-ext_p>=K*A[ext_i]:
            piv.append((ext_i,ext_p)); d=1; ext_p,ext_i=p,i
piv.append((ext_i,ext_p))
W=[]
for (i0,p0),(i1,p1) in zip(piv[:-1],piv[1:]):
    if i1<=i0: continue
    W.append(dict(t0=h1.index[i0],t1=h1.index[i1],p0=p0,p1=p1,dir=int(np.sign(p1-p0)),size_atr=abs(p1-p0)/A[i0],hours=i1-i0,i0=i0,i1=i1))
W=pd.DataFrame(W); W=W[W.size_atr>=K].reset_index(drop=True)
T=pd.read_csv("out_oos/TRADES.csv",parse_dates=["entry_time","exit_time"])
T=T[(T.variant=="BASE")&(T.cost_bps==7.5)]
raw=L.C["raw"][7.5]
def first_third(w): return w.t0+(w.t1-w.t0)/3
out=[]
for w in W.itertuples():
    inw=T[(T.entry_time>=w.t0)&(T.entry_time<w.t1)]
    with_=inw[inw.side==w.dir]; against=inw[inw.side!=w.dir]
    rw=raw[(raw.entry_time>=w.t0)&(raw.entry_time<w.t1)&(raw.side==w.dir)]
    early=with_[with_.entry_time<=first_third(w)]
    # state in first third of wave
    seg=h1.iloc[w.i0:max(w.i0+1,w.i0+(w.i1-w.i0)//3+1)]
    fadeok=((-np.sign(seg.z)==w.dir)&(seg.z.abs()>=1)).any()
    anyext=(seg.z.abs()>=1).any()
    oiup=(seg.oi.iloc[-1]/seg.oi.iloc[0]-1) if len(seg)>1 else 0
    if len(with_): status="ВЗЯВ"
    elif len(rw): status="ПРОПУСТИВ: сигнал був, але слот зайнятий"
    elif fadeok: status="ПРОПУСТИВ: натовп був проти руху, але умови двигунів не зійшлись"
    elif anyext: status="ПРОПУСТИВ: натовп був З рухом (fade дав би протилежний бік)"
    else: status="ПРОПУСТИВ: натовп нейтральний (|z|<1)"
    out.append(dict(t0=w.t0,t1=w.t1,p0=w.p0,p1=w.p1,dir=w.dir,size_atr=w.size_atr,hours=w.hours,status=status,
        n_with=len(with_),n_against=len(against),r_with=with_.net_r.sum(),r_against=against.net_r.sum(),
        early=len(early)>0,oi_first_third=oiup))
O=pd.DataFrame(out)
O["seg"]=np.where(O.t0<pd.Timestamp("2025-01-01",tz="UTC"),"2021-24","2025-26")
O["big"]=np.where(O.size_atr>=12,">=12 ATR","6-12 ATR")
O.to_csv("out_oos/WAVES.csv",index=False)
print("waves",len(O)); print(O.groupby(["seg","dir"]).size())
print(pd.crosstab(O.status,O.seg,margins=True))
print(pd.crosstab([O.big,O.dir],O.status=="ВЗЯВ",normalize="index").round(2))
cap=O[O.status=="ВЗЯВ"]; print("taken: early entry share",cap.early.mean().round(2),"| R with-wave",cap.r_with.sum().round(1))
print("R from trades AGAINST waves:",O.r_against.sum().round(1),"n",O.n_against.sum(),"| R with waves:",O.r_with.sum().round(1),"n",O.n_with.sum(), "| total trades",len(T))
