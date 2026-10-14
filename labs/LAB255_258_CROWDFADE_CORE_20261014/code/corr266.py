import io,contextlib,numpy as np,pandas as pd
exec(open("st265.py").read().split("\nF={")[0])   # signals, simX, z24, BO/BC..., g (dtune env) etc.
AB_=g["g"]; L,TLD,RAW,al,AB,simD,build=AB_["L"],AB_["TLD"],AB_["RAW"],g["al"],g["AB"],g["simD"],g["build"]
idx=pd.DatetimeIndex(BT)
def eng_replay(srcs):
    t,e,_,_=L.replay(7.5,{},TLD,raw=RAW[RAW.source.isin(srcs)].reset_index(drop=True))
    return al(pd.Series(e.equity_r.to_numpy(),index=pd.DatetimeIndex(e.time))),t
EA,tA=eng_replay(["A"]); EB,tB=eng_replay(["B3_HIGH"]); EAB,_=eng_replay(["A","B3_HIGH"])
tD,eD=simD(build(1.5,0.5,True,None,None)); ED=al(eD)
def st_mtm(tf,sens):
    S=signals(tf,sens); A=simX(S,True,"RIDE")
    A=A[~((A.cz==-A.side)&(A.az>=1))]
    eq=np.zeros(N); real=0.0; pos=np.zeros(N)
    # rebuild per trade path (RIDE: no partials) -> need entry price/R: recompute from S
    Sd={si:(ei,sd,dist) for si,ei,sd,dist in S}
    rows=[]
    for r in A.itertuples():
        ei,sd,R=Sd[r.si]; e=BO[ei]; c=COST/1e4*e/R; xi=min(int(round(ei+r.h*12)),N-1)
        rows.append((ei,xi,sd,e,R,c,r.r))
    rows.sort(); add=np.zeros(N+1)
    for ei,xi,sd,e,R,c,rr in rows:
        seg=slice(ei,xi); eq[seg]+=sd*(BC[seg]-e)/R-c; pos[seg]=sd
        add[xi]+=rr
    real=np.cumsum(add[:N]); EQ=pd.Series(real+eq,index=idx)
    return EQ,pos,A
ES2,posS2,tS2=st_mtm("2h",1.3); ES1,posS1,tS1=st_mtm("1h",1.8)
def stat(s,m,mo):
    x=s[m]-s[m].iloc[0]; return x.iloc[-1]/mo,float((x.cummax()-x).max())
print("== ST MTM (R): 21-24 R/міс, DD | 25-26 R/міс, DD")
for nm,E in [("ST H2 s1.3",ES2),("ST H1 s1.8",ES1)]:
    print(nm,[tuple(round(v,2) for v in stat(E,m,mo)) for m,mo in [(idx<TE,48),(idx>=TE,19.3)]])
# correlation matrix (risk-weighted % equity)
W={"A":EA*0.25,"B3":EB*0.25,"D2":ED*0.10,"ST_H2":ES2*0.10,"ST_H1":ES1*0.10}
for per,rule in [("день","D"),("тиждень","W"),("місяць","ME")]:
    for lab,m in [("2021-24",idx<TE),("2025-26",idx>=TE)]:
        Rr=pd.DataFrame({k:v[m].resample(rule).last().diff() for k,v in W.items()}).dropna()
        print(f"\n== кореляція {per}, {lab}"); print(Rr.corr().round(2).to_string())
# position overlap: share of time both in market, same side vs opposite
inD=np.zeros(N,int)
for r in tD.itertuples(): pass
print("\n== перекриття позицій ST_H2 з D2 / A+B3 (частка часу ST у ринку)")
def posarr_from_trades(t,ent,exi,side):
    p=np.zeros(N,int)
    for a,b,s in zip(t[ent],t[exi],t[side]): p[int(a):int(b)+1]=s
    return p
td2=tD.copy(); td2["side"]=[dict(build(1.5,0.5,True,None,None))[i-1] for i in td2.entry_i]
# simD returns entry_i only; approximate exit by MTM not needed -> skip D overlap if exit missing
pAB=np.zeros(N,int)
for t_ in (tA,tB):
    for a,b,s in zip(t_.entry_i,t_.exit_i,t_.side): pAB[int(a):int(b)+1]=s
for lab,m in [("2021-24",idx<TE),("2025-26",idx>=TE)]:
    s=posS2[m]; ab=pAB[m]; on=s!=0
    print(lab,f"ST_H2 у ринку {on.mean():.0%} часу; одночасно з A/B3: {(on&(ab!=0)).mean():.1%}, той самий бік {(on&(ab==s)).mean():.1%}, протилежний {(on&(ab==-s)).mean():.1%}")
# portfolio money
CORE=EAB*0.25+ED*0.10
def money(P):
    o=[stat(P,m,mo) for m,mo in [(idx<TE,48),(idx>=TE,19.3)]]; k=7/max(o[0][1],o[1][1]); return o, round(o[0][0]*k*1000), round(o[1][0]*k*1000)
print("\n== гроші (MTM), $100k при найгіршій DD 7%")
for nm,P in [("ядро A+B3+D2",CORE),("+ ST_H2 0.10%",CORE+ES2*0.10),("+ ST_H2 0.15%",CORE+ES2*0.15),("+ ST_H2 0.20%",CORE+ES2*0.20),
             ("+ ST_H1 0.10%",CORE+ES1*0.10),("+ ST_H2 0.10% + ST_H1 0.10%",CORE+ES2*0.10+ES1*0.10)]:
    o,a,b=money(P); print(f"{nm:30s} %/міс {o[0][0]:.2f}/{o[1][0]:.2f} DD {o[0][1]:.2f}/{o[1][1]:.2f}  ->  ${a} / ${b}")
pd.to_pickle(dict(ES2=ES2,ES1=ES1,tS2=tS2),"st266.pkl")
