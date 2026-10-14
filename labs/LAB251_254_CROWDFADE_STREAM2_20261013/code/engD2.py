import os
os.environ["LAB_CACHE"]="/home/claude/lab251/cache_full.pkl"
import numpy as np, pandas as pd
import engD as E
BT,BO,BH,BL,BC,BA,N,TE,COST=E.BT,E.BO,E.BH,E.BL,E.BC,E.BA,E.N,E.TE,E.COST
def sim(mode,k=3,H=48,maxpos=2,record_skips=False):
    sig={}
    for i,sd in E.SIG: sig.setdefault(i+1,[]).append(sd)
    idx=sorted(sig); act=[]; done=[]; eq=[]; real=0.0; p=0; i=idx[0]; skipped=[]
    def mtm(q,px):
        r=q["s"]*(px-q["e"])/q["R"]; return (q["bank"]+q["w"]*r if q["half"] else r)-q["c"]
    while i<N:
        for sd in sig.get(i,[]):
            if len(act)==0 or (len(act)<maxpos and all(q["s"]==sd and mtm(q,BO[i])>=0 for q in act)):
                e=BO[i]; R=k*BA[i]; act.append(dict(s=sd,e=e,R=R,c=COST/1e4*e/R,end=min(i+H*12-1,N-1),i0=i,st=-1.0,half=False,bank=0.0,w=1.0,pk=0.0))
            else: skipped.append((i,sd))
        keep=[]
        for q in act:
            s,e,R=q["s"],q["e"],q["R"]; sp=e+s*q["st"]*R; res=None
            if (BL[i]<=sp) if s>0 else (BH[i]>=sp): res=q["bank"]+q["w"]*q["st"]
            else:
                fav=((BH[i]-e) if s>0 else (e-BL[i]))/R; q["pk"]=max(q["pk"],fav)
                if mode=="BE1" and q["pk"]>=1: q["st"]=max(q["st"],0.0)
                if mode=="BE2" and q["pk"]>=2: q["st"]=max(q["st"],0.0)
                if mode=="HALF2" and not q["half"] and fav>=2: q["half"]=True; q["bank"]=1.0; q["w"]=0.5; q["st"]=max(q["st"],0.0)
                if mode=="TRAIL2" and q["pk"]>=2: q["st"]=max(q["st"],q["pk"]-2)
            if res is None and i>=q["end"]: res=q["bank"]+q["w"]*s*(BC[i]-e)/R
            if res is None: keep.append(q)
            else: net=res-q["c"]; real+=net; done.append(dict(entry_time=BT[q["i0"]],exit_time=BT[i],net_r=net))
        act=keep; eq.append((BT[i],real+sum(mtm(q,BC[i]) for q in act)))
        if act: i+=1
        else:
            while p<len(idx) and idx[p]<=i: p+=1
            if p>=len(idx): break
            i=idx[p]
    t=pd.DataFrame(done); e=pd.Series([v for _,v in eq],index=pd.DatetimeIndex([a for a,_ in eq]))
    return t,e,skipped
rows=[]
for mode in ["TIME","BE1","BE2","HALF2","TRAIL2"]:
    t,e,_=sim(mode)
    for sg in ["TRAIN","OOS"]:
        d=E.seg_stats(t,e,sg,0.10); d.update(mode=mode,seg=sg); rows.append(d)
R=pd.DataFrame(rows); pd.set_option("display.width",250)
print(R.pivot_table(index="mode",columns="seg",values=["ev","r_mo","dd_r","r_dd"],sort=False).round(2).to_string())
# skipped signals outcome (stand-alone sim of each skipped, SL3 48h time)
t,e,sk=sim("TIME")
def solo(i,s):
    e0=BO[i]; R=3*BA[i]; end=min(i+576-1,N-1)
    for j in range(i,end+1):
        if (BL[j]<=e0-R) if s>0 else (BH[j]>=e0+R): return -1-COST/1e4*e0/R
    return s*(BC[end]-e0)/R-COST/1e4*e0/R
S=pd.DataFrame([dict(t=BT[i],r=solo(i,s)) for i,s in sk])
S["seg"]=np.where(S.t<TE,"TRAIN","OOS")
print("\nвідкинуті лімітом сигнали:",S.groupby("seg").r.agg(["count","mean","sum"]).round(2).to_dict("index"))
for mp in [3,4]:
    t3,e3,_=sim("TIME",maxpos=mp)
    print(f"maxpos={mp}:",{sg:{k:round(v,2) for k,v in E.seg_stats(t3,e3,sg,0.10).items() if k in("r_mo","dd_r","r_dd")} for sg in ["TRAIN","OOS"]})
