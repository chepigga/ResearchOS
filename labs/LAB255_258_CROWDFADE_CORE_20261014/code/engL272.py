"""LAB272 (pre-registered): engine L = liquidation cascade.
Entry: crowd-skew state (|z6|>=1, z24 same sign |z24|>=0.5), side against crowd; trigger: coin OI change over k bars <= -q AND price moved >= m ATR in trade side over k bars; one entry per state episode; next M5 open.
Grid: triggers {k3 q0.6% m0.3, k3 q1.0% m0.3, k6 q0.6% m0.6, k6 q1.0% m0.6} x hold {4,8,12,24h} x stop {1.5,2,3} H1ATR x trail {none, stop=peak-1.5R after +1.5R}.
L: max 1 position, risk 0.10%. Base portfolio = A+B3 (0.25%) + D2 (0.10%) + S H2 (0.10%, MTM).
Select by 2021-24 portfolio ret/DD (base+L); 2025-26 shown; money $100k at worst DD 7%."""
import numpy as np,pandas as pd
exec(open("trig271.py").read().split("\nV={")[0])
ES2=pd.read_pickle("st266.pkl")["ES2"]
tD,eD=sim(entries("NOW",0,"ATR3")); D2=al(eD)
BASE=AB+D2*0.10+ES2*0.10
def simL(S,k,H,trail):
    eq=np.zeros(N); add=np.zeros(N+1); busy=-1; rows=[]
    for i,sd in S:
        ei=i+1
        if ei<=busy: continue
        e=BO[ei]; R=k*BA[ei]; c=COST/1e4*e/R; stp=e-sd*R; pk=0.0; x=None
        for j in range(ei,min(ei+H*12,N-1)):
            if (BL[j]<=stp) if sd>0 else (BH[j]>=stp): r=sd*(stp-e)/R; x=j; break
            pk=max(pk,((BH[j]-e) if sd>0 else (e-BL[j]))/R)
            if trail and pk>=1.5:
                ns=e+sd*(pk-1.5)*R; stp=max(stp,ns) if sd>0 else min(stp,ns)
            eq[j]+=sd*(BC[j]-e)/R-c
        if x is None: x=min(ei+H*12,N-1); r=sd*(BC[x]-e)/R
        add[x]+=r-c; busy=x; rows.append(dict(i=ei,r=r-c,tr=BT[ei]<TE,h=(x-ei)/12))
    E=pd.Series(np.cumsum(add[:N])+eq,index=T); return pd.DataFrame(rows),E
def seg_stats(P):
    o=[]
    for m,mo in [(T<TE,48),(T>=TE,19.3)]:
        y=P[m]-P[m].iloc[0]; o+=[y.iloc[-1]/mo,float((y.cummax()-y).max())]
    return o
b=seg_stats(BASE); kb=7/max(b[1],b[3])
print(f"БАЗА A+B3+D2+S: %/міс {b[0]:.2f}/{b[2]:.2f} DD {b[1]:.2f}/{b[3]:.2f} R/DD {b[0]*48/b[1]:.1f}/{b[2]*19.3/b[3]:.1f} -> ${b[0]*kb*1000:.0f} / ${b[2]*kb*1000:.0f}")
TRG={"k3 0.6% 0.3ATR":(3,0.006,0.3),"k3 1.0% 0.3ATR":(3,0.01,0.3),"k6 0.6% 0.6ATR":(6,0.006,0.6),"k6 1.0% 0.6ATR":(6,0.01,0.6)}
rows=[]; cmD=D2.groupby(T.strftime("%Y-%m")).last().diff()
for tn,(k,q,m) in TRG.items():
    S=episodes((lambda k,q,m:lambda i,s:oich[k][i]<=-q and s*pch[k][i]>=m)(k,q,m))
    for H in (4,8,12,24):
        for stp in (1.5,2.0,3.0):
            for tr in (False,True):
                t,E=simL(S,stp,H,tr); P=BASE+E*0.10; o=seg_stats(P)
                r=dict(trig=tn,hold=H,stop=stp,trail="1.5R" if tr else "-")
                for seg,ix,mo in [("21",0,48),("25",2,19.3)]:
                    tt=t[t.tr==(seg=="21")]
                    r.update({f"n{seg}":len(tt)/mo,f"ev{seg}":tt.r.mean(),f"Rmo{seg}":tt.r.sum()/mo,f"pRDD{seg}":o[ix]*mo/o[ix+1],f"pct{seg}":o[ix],f"dd{seg}":o[ix+1]})
                r["corrD"]=E.groupby(T.strftime("%Y-%m")).last().diff().corr(cmD)
                rows.append(r)
    print(tn,flush=True)
R=pd.DataFrame(rows); kk=7/R[["dd21","dd25"]].max(axis=1); R["$21"]=R.pct21*kk*1000; R["$25"]=R.pct25*kk*1000
R.to_csv("out_oos/LAB272_ENGINE_L.csv",index=False); pd.set_option("display.width",300)
c=["trig","hold","stop","trail","n21","ev21","Rmo21","pRDD21","n25","ev25","Rmo25","pRDD25","corrD","$21","$25"]
print("\n== топ-15 за R/DD портфеля 2021-24"); print(R.sort_values("pRDD21",ascending=False)[c].head(15).round(2).to_string(index=False))
print("\n== середнє по тригерах (усі виходи)"); print(R.groupby("trig")[["ev21","ev25","pRDD21","pRDD25","$21","$25"]].mean().round(2).to_string())
print("\n== середнє по утриманню"); print(R.groupby("hold")[["ev21","ev25","pRDD21","pRDD25","$21","$25"]].mean().round(2).to_string())
print(f"\nбаза R/DD {b[0]*48/b[1]:.2f} / {b[2]*19.3/b[3]:.2f}; частка конфігурацій, що кращі за базу за R/DD в обох періодах: {((R.pRDD21>b[0]*48/b[1])&(R.pRDD25>b[2]*19.3/b[3])).mean():.0%}")
