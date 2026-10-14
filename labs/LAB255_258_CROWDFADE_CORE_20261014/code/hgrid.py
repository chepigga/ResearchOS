import numpy as np,pandas as pd
exec(open("sw260.py").read().split("\nrows=[]")[0])
EN=entries("NOW",0,"ATR3")
# 1) drift path: mean move in trade direction (ATR) h hours after entry, no stops
H=[1,2,4,6,12,24,36,48]
P=[]
for ei,sd,e,d,a in EN:
    P.append([sd*(BC[min(ei+h*12-1,N-1)]-e)/a for h in H]+[BT[ei]<TE])
P=pd.DataFrame(P,columns=[f"{h}h" for h in H]+["tr"])
print("== середній рух у бік угоди D2 після входу (ATR H1), без стопів")
for tr,x in P.groupby("tr"): print("2021-24" if tr else "2025-26","mean:",x.drop(columns="tr").mean().round(2).to_dict()); print("        median:",x.drop(columns="tr").median().round(2).to_dict())
# 2) hold x stop grid, trail scaled (start 2R, dist 3R in R of that stop)
def simH(EN,k,Hh,trail):
    EN2=[(ei,sd,e,k*a,a) for ei,sd,e,d,a in EN]
    sig={}
    for ei,sd,e,dd,a in EN2: sig.setdefault(ei,[]).append((sd,dd,a))
    idx=sorted(sig); act=[]; done=[]; eq=[]; real=0.0; p=0; i=idx[0]
    mt=lambda q,px:(q["s"]*(px-q["e"])-q["c"])/q["d"]
    while i<N:
        for sd,dd,a in sig.get(i,[]):
            if len(act)==0 or (len(act)==1 and act[0]["s"]==sd and mt(act[0],BO[i])>=0):
                e=BO[i]; act.append(dict(s=sd,e=e,d=dd,c=COST/1e4*e,end=min(i+Hh*12-1,N-1),i0=i,stp=e-sd*dd,pk=0.0))
        keep=[]
        for q in act:
            s_,e=q["s"],q["e"]; res=None
            if (BL[i]<=q["stp"]) if s_>0 else (BH[i]>=q["stp"]): res=s_*(q["stp"]-e)
            else:
                q["pk"]=max(q["pk"],(BH[i]-e) if s_>0 else (e-BL[i]))
                if trail and q["pk"]>=2*q["d"]:
                    ns=e+s_*(q["pk"]-3*q["d"]); q["stp"]=max(q["stp"],ns) if s_>0 else min(q["stp"],ns)
                if i>=q["end"]: res=s_*(BC[i]-e)
            if res is None: keep.append(q)
            else: r=(res-q["c"])/q["d"]; real+=r; done.append(dict(entry_i=q["i0"],net_r=r))
        act=keep; eq.append((BT[i],real+sum(mt(q,BC[i]) for q in act)))
        if act: i+=1
        else:
            while p<len(idx) and idx[p]<=i: p+=1
            if p>=len(idx): break
            i=idx[p]
    return pd.DataFrame(done),pd.Series([v for _,v in eq],index=pd.DatetimeIndex([a for a,_ in eq]))
rows=[]
for Hh in (2,4,6,12,24,48):
    for k in (1.0,2.0,3.0):
        t,e=simH(EN,k,Hh,True); tot=AB+al(e)*0.10; r=dict(hold=Hh,stop=k)
        for seg,mk,mo in [("21-24",BT<TE,48),("25-26",BT>=TE,19.3)]:
            x=tot[mk]; x=x-x.iloc[0]; dd=float((x.cummax()-x).max()); tt=t[(BT[t.entry_i.to_numpy(int)]<TE)==(seg=="21-24")]
            r.update({f"угод {seg}":len(tt)/mo,f"EV {seg}":tt.net_r.mean(),f"R/DD {seg}":x.iloc[-1]/dd,f"%м {seg}":x.iloc[-1]/mo,f"DD {seg}":dd})
        rows.append(r)
R=pd.DataFrame(rows); k_=7/R[["DD 21-24","DD 25-26"]].max(axis=1); R["$ 21-24"]=R["%м 21-24"]*k_*1000; R["$ 25-26"]=R["%м 25-26"]*k_*1000
R.to_csv("out_oos/LAB261_HOLD_GRID.csv",index=False)
pd.set_option("display.width",300); print(R[["hold","stop","угод 21-24","EV 21-24","R/DD 21-24","EV 25-26","R/DD 25-26","$ 21-24","$ 25-26"]].round(2).to_string(index=False))
