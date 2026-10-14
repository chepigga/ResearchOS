"""LAB259 (pre-registered): trendline method (TrendAssist port) on core A+B3+D.
T1 D trend filter: EMA50-H4 | TL-H4 structure | both agree | none.  (D2 and D thresholds)
T2 engine T = correction-line break (cl_break, fan>=2, with TL-H4) + crowd against (sd*z6<=-zc), exits as D.
T3 D exit: trail by confirmed H1 swing (stop=max(stop, swing -/+ 0.1 ATR) after +2R) vs 3R-from-peak.
Select by 2021-24 portfolio ret/DD; 2025-26 shown only. Money: $100k, worst DD of both periods = 7%."""
import io,contextlib,pickle,numpy as np,pandas as pd
src=open("dtune.py").read().split("rows=[]")[0]
g={}
with contextlib.redirect_stdout(io.StringIO()): exec(compile(src,"dt","exec"),g)
BT,BO,BC,BA,N,TE,AB,al,build,TR4=[g[k] for k in "BT BO BC BA N TE AB al build TR4".split()]
BH,BL=g["g"]["BH"],g["g"]["BL"]
z6=g["z6"]; COST=7.5
TL=pickle.load(open("tl_SERVER.pkl","rb")); MTR=TL["mtr"]; CI=TL["ci"]; SWL=TL["swl"]; SWH=TL["swh"]; CATR=TL["catr"]
def sim(SIG,trail="3R"):
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
                if q["pk"]>=2:
                    if trail=="3R": q["st"]=max(q["st"],q["pk"]-3)
                    else:
                        k=CI[i]
                        if k>=0 and np.isfinite(SWL[k]) and np.isfinite(SWH[k]):
                            lvl=(SWL[k]-0.1*CATR[k]) if s_>0 else (SWH[k]+0.1*CATR[k])
                            r_=s_*(lvl-e)/R
                            if s_*(BC[i]-lvl)>0: q["st"]=max(q["st"],r_)
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
def dsig(x,zmin,filt):
    base=build(x,zmin,False,None,None)
    out=[]
    for i,sd in base:
        e_ok=TR4[i]==sd; t_ok=MTR[i]==sd
        if filt=="EMA" and not e_ok: continue
        if filt=="TL" and not t_ok: continue
        if filt=="BOTH" and not(e_ok and t_ok): continue
        out.append((i,sd))
    return out
# NB: build(...,trend=False) consumes the episode on first crossing regardless of filter -> to keep research semantics
# (trend failure does not consume the episode) rebuild with a custom filter:
def dsig2(x,zmin,filt):
    out=[]; used=set()
    for i,sd,ep in g["CAND"][x]:
        if ep in used: continue
        z24=g["z24"][i]
        if not(np.isfinite(z24) and -np.sign(z24)==sd and abs(z24)>=zmin): continue
        e_ok=TR4[i]==sd; t_ok=MTR[i]==sd
        if filt=="EMA" and not e_ok: continue
        if filt=="TL" and not t_ok: continue
        if filt=="BOTH" and not(e_ok and t_ok): continue
        out.append((i,sd)); used.add(ep)
    return out
def tsig(zc):
    out=[]
    for ei,sd in TL["T"]:
        i=ei-1
        if zc is None or (np.isfinite(z6[i]) and sd*z6[i]<=-zc): out.append((i,sd))
    return out
def stats(name,eqs,t=None):
    tot=AB+sum(eqs); r=dict(v=name)
    for seg,m,mo in [("21-24",BT<TE,48),("25-26",BT>=TE,19.3)]:
        x=tot[m]; x=x-x.iloc[0]; dd=float((x.cummax()-x).max())
        r.update({f"%/міс {seg}":x.iloc[-1]/mo,f"DD {seg}":dd,f"R/DD {seg}":x.iloc[-1]/dd})
        if t is not None:
            tt=t[(BT[t.entry_i.to_numpy(int)]<TE)==(seg=="21-24")]
            r.update({f"угод/міс {seg}":len(tt)/mo,f"EV {seg}":tt.net_r.mean()})
    return r
rows=[]; base_eq={}
for x,zmin,lab in [(2.0,1.0,"D"),(1.5,0.5,"D2")]:
    for filt in ["EMA","TL","BOTH","NONE"]:
        t,e=sim(dsig2(x,zmin,filt)); eq=al(e)*0.10
        if filt=="EMA": base_eq[lab]=eq
        rows.append(stats(f"T1 {lab} тренд={filt}",[eq],t))
    t,e=sim(dsig2(x,zmin,"EMA"),trail="SWING"); rows.append(stats(f"T3 {lab} EMA, трейл за свінгом H1",[al(e)*0.10],t))
for zc in [None,0.0,1.0]:
    t,e=sim(tsig(zc)); eqT=al(e)*0.10
    rows.append(stats(f"T2 D2 + двигун T (натовп {'-' if zc is None else '≥'+str(zc)} проти)",[base_eq["D2"],eqT],t))
R=pd.DataFrame(rows).set_index("v"); k=7/R[["DD 21-24","DD 25-26"]].max(axis=1)
R["$ 21-24"]=R["%/міс 21-24"]*k*1000; R["$ 25-26"]=R["%/міс 25-26"]*k*1000
R.to_csv("out_oos/LAB259_TL_CORE.csv")
pd.set_option("display.width",320); print(R.round(2).to_string())
