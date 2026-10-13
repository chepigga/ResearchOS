import os
os.environ["LAB_CACHE"]="/home/claude/lab251/cache_full.pkl"
import numpy as np, pandas as pd
import lab251 as L
BO,BH,BL,BC,N,BT=L.BO,L.BH,L.BL,L.BC,L.N,L.BT
BZ=np.asarray(L.C["BZ"],float); BA=L.BA
TE=pd.Timestamp("2025-01-01",tz="UTC"); COST=7.5
raw=L.C["raw"][COST].copy()
# 1) giveback stats per signal, 72h window
rows=[]
for r in raw.itertuples():
    ei,s,a=int(r.entry_i),int(r.side),float(r.atr); j1=min(ei+72*12,N-1); e=BO[ei]
    fav=((BH[ei:j1]-e) if s>0 else (e-BL[ei:j1]))/a
    adv=((e-BL[ei:j1]) if s>0 else (BH[ei:j1]-e))/a
    cl=s*(BC[ei:j1]-e)/a
    pk=np.argmax(fav); 
    rows.append(dict(seg="TRAIN" if r.entry_time<TE else "OOS",mfe=fav.max(),end=cl[-1],
       peak_h=pk/12,give=fav.max()-cl[-1],stop1_first=(np.argmax(adv>=1) if (adv>=1).any() else 1e9)<(np.argmax(fav>=2) if (fav>=2).any() else 1e9)))
D=pd.DataFrame(rows)
for seg,g in D.groupby("seg"):
    m2=g[g.mfe>=2]
    print(seg,"n",len(g),"| MFE>=2ATR:",f"{(g.mfe>=2).mean():.0%}","| of them end72h<0:",f"{(m2.end<0).mean():.0%}",
          "| median giveback from peak:",round(m2.give.median(),2),"ATR | median hours to peak:",round(m2.peak_h.median(),1),
          "| 1ATR adverse before +2:",f"{g.stop1_first.mean():.0%}")
# 2) exits: base half TP3 lock2 72h vs reversal-aware exits on time-exit 72h
def sim(rw,mode,k=1.0,H=72):
    sig={}
    for r in rw.itertuples(index=False): sig.setdefault(int(r.entry_i),[]).append((int(r.pri),int(r.side),float(r.atr)))
    idx=sorted(sig); act=[]; done=[]; eq=[]; real=0.0; i=idx[0]; p=0
    def mtm(q,px):
        x=q["s"]*(px-q["e"])/q["R"]; return (q["bank"]+q["w"]*x if q["half"] else x)-q["c"]
    while i<N:
        for pri,s,a in sorted(sig.get(i,[])):
            if len(act)==0 or (len(act)==1 and act[0]["s"]==s and mtm(act[0],BO[i])>=0):
                e=BO[i]; act.append(dict(s=s,e=e,R=k*a,c=COST/1e4*e/(k*a),st=-1.0,end=min(i+H*12-1,N-1),i0=i,half=False,bank=0.0,w=1.0,pk=0.0,a=a))
        keep=[]
        for q in act:
            s,e,R=q["s"],q["e"],q["R"]
            sp=e+s*q["st"]*R; hs=(BL[i]<=sp) if s>0 else (BH[i]>=sp); res=None
            if hs: res=q["bank"]+q["w"]*q["st"]
            elif mode=="HALF_TP3_LOCK2":
                tp=e+s*3*R
                if not q["half"] and ((BH[i]>=tp) if s>0 else (BL[i]<=tp)):
                    q["half"]=True;q["bank"]=1.5;q["w"]=0.5;q["st"]=max(q["st"],2.0)
            if res is None:
                hi=(BH[i]-e)/R if s>0 else (e-BL[i])/R; q["pk"]=max(q["pk"],hi)
                if mode.startswith("TRAIL"):     # after peak>=2R, stop = peak - X R (updated from next bar)
                    X=float(mode.split("_")[1])
                    if q["pk"]>=2: q["st"]=max(q["st"],q["pk"]-X)
                if mode=="BE1":                   # breakeven after +1R
                    if q["pk"]>=1: q["st"]=max(q["st"],0.0)
                if mode=="ZFLIP":                 # exit at close when crowd flips to our side (z sign agrees with position) |z|>=1
                    if s*BZ[i]>=1.0: res=s*(BC[i]-e)/R
            if res is None and i>=q["end"]: res=q["bank"]+q["w"]*s*(BC[i]-e)/R
            if res is None: keep.append(q)
            else: real+=res-q["c"]; done.append(res-q["c"])
        act=keep; eq.append(real+sum(mtm(q,BC[i]) for q in act))
        if act: i+=1
        else:
            while p<len(idx) and idx[p]<=i: p+=1
            if p>=len(idx): break
            i=idx[p]
    x=np.array(done); eqa=np.array(eq); dd=float(np.max(np.maximum.accumulate(eqa)-eqa))
    return len(x),x.mean(),x.sum(),dd
out=[]
for mode in ["HALF_TP3_LOCK2","TIME","BE1","TRAIL_1","TRAIL_2","TRAIL_3","ZFLIP"]:
    for seg,(rw,m) in {"TRAIN":(raw[raw.entry_time<TE],48),"OOS":(raw[raw.entry_time>=TE],19)}.items():
        n,ev,tot,dd=sim(rw,mode); out.append(dict(mode=mode,seg=seg,n=n,ev=ev,r_month=tot/m,dd_r=dd,r_dd=tot/dd))
O=pd.DataFrame(out).pivot(index="mode",columns="seg",values=["r_month","dd_r","r_dd","ev"]).round(2)
print(O.to_string())
