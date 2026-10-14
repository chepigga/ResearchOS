import os
os.environ["LAB_CACHE"]="/home/claude/lab251/cache_full.pkl"
import numpy as np, pandas as pd
import engD as E
BT,BO,BH,BL,BC,BA,N,TE,COST=E.BT,E.BO,E.BH,E.BL,E.BC,E.BA,E.N,E.TE,E.COST
z6,z24,TR4=E.z6,E.z24,E.TR4
# base episodes: first fresh |z6|>=2 crossing with 24h same side >=1; one per episode
def base_signals():
    out=[]; armed=True
    for i in range(1,N-1000):
        if not np.isfinite(z6[i]): continue
        if abs(z6[i])<1: armed=True; continue
        if armed and abs(z6[i])>=2 and abs(z6[i-1])<2 and np.isfinite(z24[i]) and np.sign(z24[i])==np.sign(z6[i]) and abs(z24[i])>=1:
            out.append((i,-int(np.sign(z6[i])))); armed=False
    return out
BASE=base_signals()
def sim(variant):
    ev={}
    for i,sd in BASE:
        t=TR4[i]
        if t==sd: ev.setdefault(i+1,[]).append(("D",sd,1.0))
        elif variant=="V1" or (variant=="V2" and t==0): ev.setdefault(i+1,[]).append(("PROBE",sd,1/3))
    idx=sorted(ev); act=[]; done=[]; eq=[]; real=0.0; p=0; i=idx[0]
    def mtm(q,px): return q["w"]*(q["s"]*(px-q["e"])/q["R"]-q["c"])
    def can(sd,w,i): return sum(q["w"] for q in act)+w<=2.0+1e-9 and all(q["s"]==sd and mtm(q,BO[i])>=0 for q in act)
    def open_(kind,sd,w,i):
        e=BO[i]; R=3*BA[i]; act.append(dict(kind=kind,s=sd,e=e,R=R,c=COST/1e4*e/R,end=min(i+576-1,N-1),i0=i,st=-1.0,pk=0.0,w=w,added=False))
    stats=dict(probes=0,adds=0,d=0)
    while i<N:
        # scale-in: H4 turned to probe side (TR4 known at bar open i)
        for q in list(act):
            if q["kind"]=="PROBE" and not q["added"] and TR4[i]==q["s"] and mtm(q,BO[i])>=0 and can(q["s"],2/3,i):
                open_("ADD",q["s"],2/3,i); q["added"]=True; stats["adds"]+=1
        for kind,sd,w in ev.get(i,[]):
            if (len(act)==0 and True) or can(sd,w,i):
                if len(act)==0 or can(sd,w,i): open_(kind,sd,w,i); stats["probes" if kind=="PROBE" else "d"]+=1
        keep=[]
        for q in act:
            s,e,R=q["s"],q["e"],q["R"]; sp=e+s*q["st"]*R; res=None
            if (BL[i]<=sp) if s>0 else (BH[i]>=sp): res=q["st"]
            else:
                q["pk"]=max(q["pk"],((BH[i]-e) if s>0 else (e-BL[i]))/R)
                if q["pk"]>=2: q["st"]=max(q["st"],q["pk"]-3)
                if i>=q["end"]: res=s*(BC[i]-e)/R
            if res is None: keep.append(q)
            else:
                net=q["w"]*(res-q["c"]); real+=net; done.append(dict(entry_time=BT[q["i0"]],net_r=net,kind=q["kind"],w=q["w"]))
        act=keep; eq.append((BT[i],real+sum(mtm(q,BC[i]) for q in act)))
        nxt=i+1
        if not act:
            while p<len(idx) and idx[p]<=i: p+=1
            if p>=len(idx): break
            nxt=idx[p]
        i=nxt
    return pd.DataFrame(done),pd.Series([v for _,v in eq],index=pd.DatetimeIndex([a for a,_ in eq])),stats
rows=[]
for v in ["D_ONLY","V1","V2"]:
    t,e,stt=sim(v)
    for sg in ["TRAIN","OOS"]:
        tt=t[(t.entry_time<TE) if sg=="TRAIN" else (t.entry_time>=TE)]
        ee=e[(e.index<TE) if sg=="TRAIN" else (e.index>=TE)]; ee=ee-ee.iloc[0]; mo=48 if sg=="TRAIN" else 19.3
        dd=float((ee.cummax()-ee).max())
        by={k:round(g.net_r.sum()/mo,2) for k,g in tt.groupby("kind")}
        nb={k:round(len(g)/mo,1) for k,g in tt.groupby("kind")}
        evk={k:round((g.net_r/g.w).mean(),2) for k,g in tt.groupby("kind")}
        rows.append(dict(variant=v,seg=sg,r_mo=tt.net_r.sum()/mo,dd_r=dd,r_dd=tt.net_r.sum()/dd,pct_mo=tt.net_r.sum()/mo*0.10,dd_pct=dd*0.10,
                         R_mo_by_part=by,entries_mo=nb,ev_perR=evk))
R=pd.DataFrame(rows); pd.set_option("display.width",260); pd.set_option("display.max_colwidth",80)
print(R.round(2).to_string(index=False))
