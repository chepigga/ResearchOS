import io,contextlib,numpy as np,pandas as pd
src=open("trendalt.py").read(); src=src[:src.index("df=pd.DataFrame({\"c\":BC")]
g={}
with contextlib.redirect_stdout(io.StringIO()): exec(compile(src,"ta","exec"),g)
BT,BO,BH,BL,BC,BA,N,TE,COST,AB,al=[g[k] for k in "BT BO BH BL BC BA N TE COST AB al".split()]
TR4=g["E"].TR4
SIG=g["signals"](g["TR"]["2 без тренду"],False)
SIGH=g["signals"](g["TR"]["1 H4 EMA50 (зараз)"],False)
def sim(SIG,w_off,sep):
    sig={}
    for i,sd in SIG: sig.setdefault(i+1,[]).append((sd,1 if TR4[i]==sd else 0))
    idx=sorted(sig); pools={0:[],1:[]}; done=[]; eq=[]; real=0.0; p=0; i=idx[0]
    mt=lambda q,px:(q["s"]*(px-q["e"])/q["R"]-q["c"])*q["w"]
    while i<N:
        for sd,al_ in sig.get(i,[]):
            k=al_ if sep else 1; act=pools[k]; cap=2 if (al_ or not sep) else sep
            ok=len(act)==0 or (len(act)<cap and all(q["s"]==sd and mt(q,BO[i])>=0 for q in act))
            if ok:
                e=BO[i]; R=3*BA[i]; act.append(dict(s=sd,e=e,R=R,c=COST/1e4*e/R,end=min(i+575,N-1),i0=i,st=-1.0,pk=0.0,w=1.0 if al_ else w_off,al=al_))
        for k in pools:
            keep=[]
            for q in pools[k]:
                s_,e,R=q["s"],q["e"],q["R"]; sp=e+s_*q["st"]*R; res=None
                if (BL[i]<=sp) if s_>0 else (BH[i]>=sp): res=q["st"]
                else:
                    q["pk"]=max(q["pk"],((BH[i]-e) if s_>0 else (e-BL[i]))/R)
                    if q["pk"]>=2: q["st"]=max(q["st"],q["pk"]-3)
                    if i>=q["end"]: res=s_*(BC[i]-e)/R
                if res is None: keep.append(q)
                else: real+=(res-q["c"])*q["w"]; done.append(dict(entry_i=q["i0"],net_r=res-q["c"],w=q["w"],al=q["al"]))
            pools[k]=keep
        allq=pools[0]+pools[1]
        eq.append((BT[i],real+sum(mt(q,BC[i]) for q in allq)))
        if allq: i+=1
        else:
            while p<len(idx) and idx[p]<=i: p+=1
            if p>=len(idx): break
            i=idx[p]
    return pd.DataFrame(done),pd.Series([v for _,v in eq],index=pd.DatetimeIndex([a for a,_ in eq]))
V={"0 D з H4 (зараз)":(SIGH,1.0,0),"1 D' усі повний ризик":(SIG,1.0,0),
   "2 D' слабкі ×0.5":(SIG,0.5,0),"3 D' слабкі ×0.33":(SIG,0.33,0),
   "4 D' окремий слот (1) ×1":(SIG,1.0,1),"5 D' окремий слот (1) ×0.5":(SIG,0.5,1),
   "6 D' окремі слоти (2) ×0.5":(SIG,0.5,2),"7 D' окремий слот (1) ×0.33":(SIG,0.33,1)}
rows=[];curves={}
for name,(S,w,sep) in V.items():
    t,e=sim(S,w,sep); D=al(e)*0.10; tot=AB+D; curves[name]=tot
    for seg,mask,mo in [("TRAIN",BT<TE,48),("OOS",BT>=TE,19.3)]:
        P=tot[mask]; P=P-P.iloc[0]; dd=float((P.cummax()-P).max())
        tt=t[(BT[t.entry_i.to_numpy(int)]<TE)==(seg=="TRAIN")]
        m=P.groupby(P.index.strftime("%Y-%m")).last(); mm=m.diff().fillna(m.iloc[0])
        rows.append(dict(v=name,seg=seg,D_n_mo=len(tt)/mo,D_Rw_mo=(tt.net_r*tt.w).sum()/mo,pct_mo=P.iloc[-1]/mo,dd=dd,ret_dd=P.iloc[-1]/dd,
                         sharpe=mm.mean()/mm.std()*np.sqrt(12),neg_m=(mm<0).mean()))
R=pd.DataFrame(rows)
W=R.pivot_table(index="v",columns="seg",values=["D_n_mo","D_Rw_mo","pct_mo","dd","ret_dd","sharpe","neg_m"],sort=False)
# money: scale so that worst DD across both periods =7%
k=7/W[("dd","TRAIN")].combine(W[("dd","OOS")],max)
W[("$/міс","TRAIN")]=W[("pct_mo","TRAIN")]*k*1000; W[("$/міс","OOS")]=W[("pct_mo","OOS")]*k*1000; W[("scale","")]=k
pd.set_option("display.width",300); print(W.round(2).to_string())
R.to_csv("out_oos/D_WEIGHT_SLOTS.csv",index=False)
