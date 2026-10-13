import os, pickle
os.environ["LAB_CACHE"]="/home/claude/lab251/cache_full.pkl"
import numpy as np, pandas as pd
import lab251 as L
BO,BH,BL,BC,N,BT=L.BO,L.BH,L.BL,L.BC,L.N,L.BT
TE=pd.Timestamp("2025-01-01",tz="UTC"); COST=7.5
X=pickle.load(open("extra.pkl","rb")); IDX={t:i for i,t in enumerate(BT)}
base=L.C["raw"][COST][["source","entry_time","entry_i","side","atr","pri"]].copy(); base["w"]=1.0; base["tier"]="CORE"
def rows(df,src):
    out=[]
    for r in df.itertuples(index=False):
        t=pd.Timestamp(r.entry_time); t=t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")
        if t in IDX: out.append(dict(source=src,entry_time=t,entry_i=IDX[t],side=int(r.side),atr=float(r.atr),pri=5))
    return pd.DataFrame(out)
EXT={"A_X":rows(X["a_all"][~X["a_all"].phase.isin(["CONT","REACCEL"])],"A_X"),
     "B3_X":rows(X["b_bal"],"B3_X"),"R48_X":rows(X["r48_bal"],"R48_X"),
     "R48_ALL":rows(X["r48_all"][X["r48_all"].mech=="R48_ACCEPT"],"R48_ALL"),"EARLY_X":rows(X["res_all"],"EARLY_X")}
bk=set(zip(base.entry_i,base.side))
for k,d in EXT.items():
    EXT[k]=d[~pd.Series(list(zip(d.entry_i,d.side))).isin(bk).values].drop_duplicates(["entry_i","side"])
def pool(names,w):
    ps=[base]+[EXT[n].assign(w=w,tier="EXT") for n in names]
    return pd.concat(ps,ignore_index=True).sort_values(["entry_i","pri"]).reset_index(drop=True)
def sim(rw,H=72,maxpos=2):
    sig={}
    for r in rw.itertuples(index=False): sig.setdefault(int(r.entry_i),[]).append((int(r.pri),int(r.side),float(r.atr),float(r.w),r.tier))
    idx=sorted(sig); act=[]; done=[]; eq=[]; real=0.0; i=idx[0]; p=0
    def mtm(q,px):
        x=q["s"]*(px-q["e"])/q["R"]; return q["w"]*((q["bank"]+q["k"]*x if q["half"] else x)-q["c"])
    while i<N:
        for pri,s,a,w,tier in sorted(sig.get(i,[])):
            if len(act)==0 or (len(act)<maxpos and all(q["s"]==s and mtm(q,BO[i])>=0 for q in act)):
                e=BO[i]; act.append(dict(s=s,e=e,R=a,c=COST/1e4*e/a,st=-1.0,end=min(i+H*12-1,N-1),half=False,bank=0.0,k=1.0,w=w,tier=tier))
        keep=[]
        for q in act:
            s,e,R=q["s"],q["e"],q["R"]; sp=e+s*q["st"]*R
            res=None
            if (BL[i]<=sp) if s>0 else (BH[i]>=sp): res=q["bank"]+q["k"]*q["st"]
            elif not q["half"] and ((BH[i]>=e+3*R) if s>0 else (BL[i]<=e-3*R)):
                q["half"]=True;q["bank"]=1.5;q["k"]=0.5;q["st"]=max(q["st"],2.0)
            if res is None and i>=q["end"]: res=q["bank"]+q["k"]*s*(BC[i]-e)/R
            if res is None: keep.append(q)
            else:
                net=q["w"]*(res-q["c"]); real+=net; done.append((net,q["tier"],q["w"]))
        act=keep; eq.append(real+sum(mtm(q,BC[i]) for q in act))
        if act: i+=1
        else:
            while p<len(idx) and idx[p]<=i: p+=1
            if p>=len(idx): break
            i=idx[p]
    d=pd.DataFrame(done,columns=["net","tier","w"]); e=np.array(eq); dd=float(np.max(np.maximum.accumulate(e)-e))
    ext=d[d.tier=="EXT"]
    return dict(n=len(d),n_ext=len(ext),ev_ext_perR=(ext.net/ext.w).mean() if len(ext) else np.nan,tot=d.net.sum(),dd=dd)
cfgs=[("BASE",[]),("+A_X",["A_X"]),("+B3_X",["B3_X"]),("+R48_X",["R48_X"]),("+R48_ALL",["R48_ALL"]),("+EARLY_X",["EARLY_X"]),
      ("+ALL_EXT",["A_X","B3_X","R48_X","EARLY_X"])]
out=[]
for name,ns in cfgs:
    for w in ([1.0] if not ns else [1.0,0.5]):
        for mp in ([2] if name!="+ALL_EXT" else [2,3]):
            P=pool(ns,w)
            for seg,(m,mo) in {"TRAIN":(P.entry_time<TE,48),"OOS":(P.entry_time>=TE,19)}.items():
                s=sim(P[m].reset_index(drop=True),maxpos=mp)
                out.append(dict(cfg=name,w_ext=w,maxpos=mp,seg=seg,trades_mo=s["n"]/mo,ext_ev_perR=s["ev_ext_perR"],r_month=s["tot"]/mo,dd=s["dd"],r_dd=s["tot"]/s["dd"]))
O=pd.DataFrame(out)
pd.set_option("display.width",250)
print(O.pivot_table(index=["cfg","w_ext","maxpos"],columns="seg",values=["trades_mo","ext_ev_perR","r_month","dd","r_dd"]).round(2).to_string())
print({k:len(v) for k,v in EXT.items()})
