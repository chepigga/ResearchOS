import os
os.environ["LAB_CACHE"]="/home/claude/lab251/cache_full.pkl"
import numpy as np, pandas as pd
import lab251 as L, engD as E
BT,BO,BH,BL,BC,BA,N=L.BT,L.BO,L.BH,L.BL,L.BC,L.BA,L.N; TE=pd.Timestamp("2025-01-01",tz="UTC"); COST=7.5
z6,z24=E.z6,E.z24
s=pd.Series(BC,index=BT)
def asof(ser,sh): x=ser.copy(); x.index=x.index+sh; return x.reindex(BT,method="ffill").to_numpy()
h1=s.resample("1h").last().dropna(); h4=s.resample("4h").last().dropna()
def rule(c,span,lag):
    e=c.ewm(span=span,adjust=False).mean(); return pd.Series(np.where((c>e)&(e>e.shift(lag)),1,np.where((c<e)&(e<e.shift(lag)),-1,0)),index=c.index)
e20h1=h1.ewm(span=20,adjust=False).mean()
EMA20H1=asof(e20h1,pd.Timedelta("1h"))
TR={"1 H4 EMA50 (зараз)":E.TR4,
    "2 без тренду":np.ones(N)*9,
    "3 H4 EMA20":asof(rule(h4,20,6),pd.Timedelta("4h")),
    "4 H1 EMA50":asof(rule(h1,50,6),pd.Timedelta("1h")),
    "5 нахил EMA20 H1 (6 год)":asof(np.sign(e20h1-e20h1.shift(6)),pd.Timedelta("1h")),
    "6 ціна vs EMA20 H1":np.sign(BC-EMA20H1),
    "7 зміна ціни за 24 год":np.sign(BC-np.r_[np.full(288,np.nan),BC[:-288]])}
def signals(T,chase):
    out=[]; armed=True
    for i in range(300,N-1000):
        if not np.isfinite(z6[i]): continue
        if abs(z6[i])<1: armed=True; continue
        if armed and abs(z6[i])>=2 and abs(z6[i-1])<2 and np.isfinite(z24[i]) and np.sign(z24[i])==np.sign(z6[i]) and abs(z24[i])>=1:
            sd=-int(np.sign(z6[i]))
            if T[i]==9 or T[i]==sd:
                if chase and sd*(BO[i+1]-EMA20H1[i+1])/BA[i+1]>2: armed=False; continue
                out.append((i,sd)); armed=False
    return out
def simD(SIG):
    sig={}
    for i,sd in SIG: sig.setdefault(i+1,[]).append(sd)
    idx=sorted(sig); act=[]; done=[]; eq=[]; real=0.0; p=0; i=idx[0]
    mt=lambda q,px: q["s"]*(px-q["e"])/q["R"]-q["c"]
    while i<N:
        for sd in sig.get(i,[]):
            if len(act)==0 or (len(act)==1 and act[0]["s"]==sd and mt(act[0],BO[i])>=0):
                e=BO[i]; R=3*BA[i]; act.append(dict(s=sd,e=e,R=R,c=COST/1e4*e/R,end=min(i+575,N-1),i0=i,st=-1.0,pk=0.0))
        keep=[]
        for q in act:
            s_,e,R=q["s"],q["e"],q["R"]; sp=e+s_*q["st"]*R; res=None
            if (BL[i]<=sp) if s_>0 else (BH[i]>=sp): res=q["st"]
            else:
                q["pk"]=max(q["pk"],((BH[i]-e) if s_>0 else (e-BL[i]))/R)
                if q["pk"]>=2: q["st"]=max(q["st"],q["pk"]-3)
                if i>=q["end"]: res=s_*(BC[i]-e)/R
            if res is None: keep.append(q)
            else: real+=res-q["c"]; done.append(dict(entry_i=q["i0"],net_r=res-q["c"]))
        act=keep; eq.append((BT[i],real+sum(mt(q,BC[i]) for q in act)))
        if act: i+=1
        else:
            while p<len(idx) and idx[p]<=i: p+=1
            if p>=len(idx): break
            i=idx[p]
    return pd.DataFrame(done),pd.Series([v for _,v in eq],index=pd.DatetimeIndex([a for a,_ in eq]))
def al(x): x=x[~x.index.duplicated(keep="last")]; return x.reindex(x.index.union(BT)).ffill().reindex(BT).ffill().fillna(0.0)
TLD=dict(mtr=np.zeros(N,int),ci=np.zeros(N,int),swl=None,swh=None,catr=None)
RAW=L.C["raw"][7.5]
tv,ev,_,_=L.replay(7.5,{},TLD,raw=RAW[RAW.source.isin(["A","B3_HIGH"])].reset_index(drop=True))
AB=al(pd.Series(ev.equity_r.to_numpy(),index=pd.DatetimeIndex(ev.time)))*0.25
# waves for first-third coverage

df=pd.DataFrame({"c":BC,"a":BA},index=BT); hh=df.resample("1h").agg({"c":"last","a":"last"}).dropna()
C=hh.c.to_numpy(); A=hh.a.to_numpy(); Th=hh.index
piv=[0]; d=0; ei=0
for i in range(1,len(C)):
    if d>=0:
        if C[i]>C[ei]: ei=i
        elif C[ei]-C[i]>=3*A[ei]: piv.append(ei); d=-1; ei=i; continue
    if d<=0:
        if C[i]<C[ei]: ei=i
        elif C[i]-C[ei]>=3*A[ei]: piv.append(ei); d=1; ei=i
piv.append(ei)
pos=lambda t:int(np.searchsorted(BT.values,np.datetime64(t.tz_convert("UTC").tz_localize(None))))
WV=[(pos(Th[a_]),pos(Th[b_]),int(np.sign(C[b_]-C[a_])),Th[a_]<TE) for a_,b_ in zip(piv[:-1],piv[1:]) if b_>a_ and abs(C[b_]-C[a_])>=3*A[a_]]
rows=[]
for name,T in TR.items():
    for chase in [False,True]:
        SIG=signals(T,chase); t,e=simD(SIG); D=al(e)*0.10
        si=np.array([i for i,_ in SIG]); ss=np.array([sd for _,sd in SIG])
        for seg,mask in [("2021-24",BT<TE),("2025-26",BT>=TE)]:
            P=(AB+D)[mask]; P=P-P.iloc[0]; Dm=D[mask]; Dm=Dm-Dm.iloc[0]
            mo=48 if seg=="2021-24" else 19.3
            m=P.groupby(P.index.strftime("%Y-%m")).last(); mm=m.diff().fillna(m.iloc[0])
            ddP=float((P.cummax()-P).max()); ddD=float((Dm.cummax()-Dm).max())
            tt=t[(BT[t.entry_i.to_numpy(int)]<TE)==(seg=="2021-24")]
            # early coverage
            ft=0; nw=0
            for i0,i1,d_,tr in WV:
                if tr!=(seg=="2021-24"): continue
                nw+=1; third=i0+(i1-i0)//3
                ft+=bool(((si>=i0)&(si<=third)&(ss==d_)).any())
            rows.append(dict(trend=name,chase="так" if chase else "ні",seg=seg,D_trades_mo=len(tt)/mo,D_ev=tt.net_r.mean(),D_r_mo=tt.net_r.sum()/mo,
                             D_ret_dd=tt.net_r.sum()/ddD*0.10 if ddD>0 else np.nan,port_pct_mo=P.iloc[-1]/mo,port_dd=ddP,port_ret_dd=P.iloc[-1]/ddP,
                             port_sharpe=mm.mean()/mm.std()*np.sqrt(12),start_cov=ft/nw))
R=pd.DataFrame(rows); pd.set_option("display.width",280)
print(R.pivot_table(index=["trend","chase"],columns="seg",values=["D_trades_mo","D_ev","D_r_mo","port_pct_mo","port_dd","port_ret_dd","port_sharpe","start_cov"],sort=False).round(2).to_string())
b=R[R.seg=="2021-24"].sort_values("port_ret_dd",ascending=False).head(3)[["trend","chase","port_ret_dd"]]; print("\nTOP by TRAIN portfolio ret/DD:\n",b.to_string(index=False))
R.to_csv("out_oos/TREND_ALTERNATIVES.csv",index=False)
