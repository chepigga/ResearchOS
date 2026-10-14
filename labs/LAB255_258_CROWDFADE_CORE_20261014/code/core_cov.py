import os
os.environ["LAB_CACHE"]="/home/claude/lab251/cache_full.pkl"
import numpy as np, pandas as pd
import lab251 as L, engD as E
BT,BO,BH,BL,BC,BA,N=L.BT,L.BO,L.BH,L.BL,L.BC,L.BA,L.N; TE=pd.Timestamp("2025-01-01",tz="UTC"); COST=7.5
TLD=dict(mtr=np.zeros(N,int),ci=np.zeros(N,int),swl=None,swh=None,catr=None)
RAW=L.C["raw"][7.5]
# --- core trades
tv,_,_,_=L.replay(7.5,{},TLD,raw=RAW[RAW.source.isin(["A","B3_HIGH"])].reset_index(drop=True))
tv=tv.assign(k=1.0,eng=tv.source.str.replace("_HIGH",""),exit_px=np.nan)
# D sim with fields (48h, SL3, trail 3R after +2R) + record skipped
def simD():
    sig={}
    for i,sd in E.SIG: sig.setdefault(i+1,[]).append(sd)
    idx=sorted(sig); act=[]; done=[]; skipped=[]; p=0; i=idx[0]
    mt=lambda q,px: q["s"]*(px-q["e"])/q["R"]-q["c"]
    while i<N:
        for sd in sig.get(i,[]):
            if len(act)==0 or (len(act)==1 and act[0]["s"]==sd and mt(act[0],BO[i])>=0):
                e=BO[i]; R=3*BA[i]; act.append(dict(s=sd,e=e,R=R,c=COST/1e4*e/R,end=min(i+575,N-1),i0=i,st=-1.0,pk=0.0,a=BA[i]))
            else: skipped.append((i,sd))
        keep=[]
        for q in act:
            s,e,R=q["s"],q["e"],q["R"]; sp=e+s*q["st"]*R; res=None
            if (BL[i]<=sp) if s>0 else (BH[i]>=sp): res=q["st"]; px=sp
            else:
                q["pk"]=max(q["pk"],((BH[i]-e) if s>0 else (e-BL[i]))/R)
                if q["pk"]>=2: q["st"]=max(q["st"],q["pk"]-3)
                if i>=q["end"]: res=s*(BC[i]-e)/R; px=BC[i]
            if res is None: keep.append(q)
            else: done.append(dict(entry_i=q["i0"],exit_i=i,side=s,entry=e,atr=q["a"],net_r=res-q["c"],k=3.0,eng="D",exit_px=px))
        act=keep
        if act: i+=1
        else:
            while p<len(idx) and idx[p]<=i: p+=1
            if p>=len(idx): break
            i=idx[p]
    return pd.DataFrame(done),skipped
td,skD=simD()
T=pd.concat([tv[["entry_i","exit_i","side","entry","atr","net_r","k","eng"]],td[["entry_i","exit_i","side","entry","atr","net_r","k","eng","exit_px"]]],ignore_index=True)
T["exit_px"]=np.where(T.exit_px.isna(),np.nan,T.exit_px)
T["captured_atr"]=T.net_r*T.k
# --- waves >=3 ATR (H1 zigzag)
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
W=[]
for a_,b_ in zip(piv[:-1],piv[1:]):
    if b_<=a_ or abs(C[b_]-C[a_])<3*A[a_]: continue
    W.append(dict(i0=pos(Th[a_]),i1=pos(Th[b_]),p0=C[a_],p1=C[b_],dir=int(np.sign(C[b_]-C[a_])),size=abs(C[b_]-C[a_])/A[a_],a0=A[a_],seg="2021-24" if Th[a_]<TE else "2025-26"))
W=pd.DataFrame(W)
# signal presence for reasons
z6,z24,TR4=E.z6,E.z24,E.TR4
dsig=(np.abs(z6)>=2)&(np.r_[0,np.abs(z6)[:-1]]<2)&np.isfinite(z24)&(np.sign(z24)==np.sign(z6))&(np.abs(z24)>=1)
skipset=set(i for i,_ in skD)
rawAB=RAW[RAW.source.isin(["A","B3_HIGH"])]
rows=[]
for w in W.itertuples():
    tw=T[(T.entry_i>=w.i0)&(T.entry_i<w.i1)]
    wi=tw[tw.side==w.dir]; ag=tw[tw.side!=w.dir]
    r=dict(seg=w.seg,dir=w.dir,size=w.size,n_with=len(wi),n_against=len(ag),R_with=wi.net_r.sum(),R_against=ag.net_r.sum(),cap_atr=wi.captured_atr.sum())
    if len(wi):
        f=wi.sort_values("entry_i").iloc[0]
        r.update(taken=True,eng_first=f.eng,entry_frac=(f.entry-w.p0)/(w.p1-w.p0),
                 left_at_start=abs(f.entry-w.p0)/w.a0)
        last=wi.sort_values("exit_i").iloc[-1]
        exit_px=last.exit_px if np.isfinite(last.exit_px) else BC[int(last.exit_i)]
        r["left_after_exit"]=max(0.0,w.dir*(w.p1-exit_px)/w.a0) if last.exit_i<w.i1 else 0.0
        r["why"]="ВЗЯВ"
    else:
        r["taken"]=False
        rng=np.arange(w.i0,w.i0+max(1,(w.i1-w.i0)*2//3))
        sd=-np.sign(z6[rng])
        dok=rng[dsig[rng]&(sd==w.dir)]
        abraw=rawAB[(rawAB.entry_i>=w.i0)&(rawAB.entry_i<w.i1)&(rawAB.side==w.dir)]
        if len(abraw): r["why"]="A/B3 сигнал був, але не відкрили (ліміт/MTM)"
        elif len(dok) and any((i+1) in skipset for i in dok): r["why"]="D-сигнал був, але ліміт позицій"
        elif len(dok) and (TR4[dok]==w.dir).any(): r["why"]="D-сигнал був, але не відкрили (епізод уже використано)"
        elif len(dok): r["why"]="натовп є (6г+24г), але H4-тренд не підтвердив"
        elif ((np.abs(z6[rng])>=1)&(sd==w.dir)).any(): r["why"]="натовп слабкий (|z|<2 або 24г не підтвердив)"
        else: r["why"]="натовп мовчить або з рухом"
    rows.append(r)
Wd=pd.DataFrame(rows)
pd.set_option("display.width",250); pd.set_option("display.max_colwidth",60)
mo={"2021-24":48,"2025-26":19.3}
for sg,x in Wd.groupby("seg"):
    print(f"\n===== {sg}: рухів ≥3 ATR {len(x)} ({len(x)/mo[sg]:.1f}/міс), сумарно {x['size'].sum():.0f} ATR")
    print((x.why.value_counts(normalize=True)).round(2).to_string())
    t=x[x.taken]
    print(f"взяв {len(t)} рухів ({len(t)/len(x):.0%}), що містять {t['size'].sum()/x['size'].sum():.0%} усього руху")
    print("частка взятих за розміром:",x.groupby(pd.cut(x['size'],[3,4.5,6,10,1e9],right=False),observed=True).taken.mean().round(2).to_dict())
    print("частка взятих: ріст",round(x[x.dir>0].taken.mean(),2),"падіння",round(x[x.dir<0].taken.mean(),2))
    print("у взятих рухах (медіана): вхід після",round(t.entry_frac.median(),2),"руху; втрачено на старті",round(t.left_at_start.median(),1),"ATR; лишилось після виходу",round(t.left_after_exit.median(),1),"ATR; розмір руху",round(t['size'].median(),1),"ATR")
    print("сумарно по взятих: рух",round(t['size'].sum()),"ATR | втрачено на старті",round(t.left_at_start.sum()),"| після виходу",round(t.left_after_exit.sum()),"| забрано (ATR)",round(t.cap_atr.sum()))
    print("R: угоди за рухом",round(x.R_with.sum(),1),"| угоди проти руху",round(x.R_against.sum(),1),"(",int(x.n_against.sum()),"угод)")
    print("хто перший входить у взяті рухи:",t.eng_first.value_counts().to_dict())
Wd.to_csv("out_oos/CORE_WAVES.csv",index=False)
