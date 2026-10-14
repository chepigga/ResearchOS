import os
os.environ["LAB_CACHE"]="/home/claude/lab251/cache_full.pkl"
import numpy as np, pandas as pd
import engD as E
BT,BO,BH,BL,BC,BA,N,TE,COST=E.BT,E.BO,E.BH,E.BL,E.BC,E.BA,E.N,E.TE,E.COST
def sim(H,trail,k=3):
    sig={}
    for i,sd in E.SIG: sig.setdefault(i+1,[]).append(sd)
    idx=sorted(sig); act=[]; done=[]; eq=[]; real=0.0; p=0; i=idx[0]
    def mtm(q,px): return q["s"]*(px-q["e"])/q["R"]-q["c"]
    while i<N:
        for sd in sig.get(i,[]):
            if len(act)==0 or (len(act)==1 and act[0]["s"]==sd and mtm(act[0],BO[i])>=0):
                e=BO[i]; R=k*BA[i]; act.append(dict(s=sd,e=e,R=R,c=COST/1e4*e/R,end=min(i+H*12-1,N-1),i0=i,st=-1.0,pk=0.0))
        keep=[]
        for q in act:
            s,e,R=q["s"],q["e"],q["R"]; sp=e+s*q["st"]*R; res=None
            if (BL[i]<=sp) if s>0 else (BH[i]>=sp): res=q["st"]; why="stop" if q["st"]<0 else "trail"
            else:
                q["pk"]=max(q["pk"],((BH[i]-e) if s>0 else (e-BL[i]))/R)
                if trail and q["pk"]>=2: q["st"]=max(q["st"],q["pk"]-trail)
                if i>=q["end"]: res=s*(BC[i]-e)/R; why="time"
            if res is None: keep.append(q)
            else: net=res-q["c"]; real+=net; done.append(dict(entry_time=BT[q["i0"]],exit_time=BT[i],net_r=net,why=why,hold_h=(i-q["i0"])/12))
        act=keep; eq.append((BT[i],real+sum(mtm(q,BC[i]) for q in act)))
        if act: i+=1
        else:
            while p<len(idx) and idx[p]<=i: p+=1
            if p>=len(idx): break
            i=idx[p]
    return pd.DataFrame(done),pd.Series([v for _,v in eq],index=pd.DatetimeIndex([a for a,_ in eq]))
rows=[];T={}
for H in [48,72,96]:
    for tr in [0,2,3]:
        t,e=sim(H,tr); T[(H,tr)]=t
        for sg in ["TRAIN","OOS"]:
            d=E.seg_stats(t,e,sg,0.10); d.update(H=H,trail=("—" if tr==0 else f"{tr}R"),seg=sg)
            tt=t[(t.entry_time<TE) if sg=="TRAIN" else (t.entry_time>=TE)]
            d["big_share"]=tt.net_r[tt.net_r>=tt.net_r.quantile(.9)].sum()/tt.net_r.sum(); d["best_R"]=tt.net_r.max(); rows.append(d)
R=pd.DataFrame(rows); pd.set_option("display.width",250)
P=R.pivot_table(index=["H","trail"],columns="seg",values=["trades_mo","ev","r_mo","dd_r","r_dd","pct_mo"],sort=False)
print(P.round(2).to_string())
tr=R[R.seg=="TRAIN"].sort_values("r_dd",ascending=False).iloc[0]; print("\nCHOSEN on TRAIN:",tr.H,tr.trail,"r_dd",round(tr.r_dd,2))
R.to_csv("out_oos/ENGINE_D_HOLD_TRAIL.csv",index=False)
for key in [(48,0),(int(tr.H),0 if tr.trail=="—" else int(tr.trail[0]))]:
    t=T[key]; print(key,"exit reasons:",t.why.value_counts(normalize=True).round(2).to_dict(),"| by year R:",t.groupby(t.entry_time.dt.year).net_r.sum().round(1).to_dict())
