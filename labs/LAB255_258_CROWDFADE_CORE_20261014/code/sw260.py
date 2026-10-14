"""LAB260 (pre-registered): lower-TF swing confirmation for D2 entries.
Signal = D2 (z6 cross 1.5, |z24|>=0.5 same sign, EMA50-H4 with trade), one per episode.
Entry modes: NOW (next M5 open) | M5S3: first M5 close beyond max high/min low of previous 3 bars |
  M15F: first M5 close crossing last CONFIRMED M15 fractal (1/1) high (long) / low (short).
Wait window W = 1h/3h/6h after signal, else skip. Entry = next M5 open after trigger.
Stop: ATR3 (3 H1ATR) | STRUCT: last confirmed swing (M5: min low of last 6 bars; M15: last fractal low) -/+0.1ATR, clamp [0.5,3] ATR.
Exit identical in price terms for all: trail stop = peak-9ATR once peak >= +6ATR (=3R/2R of ATR3), 48h. net R = pnl / initial stop distance.
Risk 0.10% per trade (per R). Select by 2021-24 portfolio ret/DD; 2025-26 shown."""
import io,contextlib,pickle,numpy as np,pandas as pd
src=open("dtune.py").read().split("rows=[]")[0]
g={}
with contextlib.redirect_stdout(io.StringIO()): exec(compile(src,"dt","exec"),g)
BT,BO,BC,BA,N,TE,AB,al,TR4=[g[k] for k in "BT BO BC BA N TE AB al TR4".split()]
BH,BL=g["g"]["BH"],g["g"]["BL"]; COST=7.5
def d2sig():
    out=[]; used=set()
    for i,sd,ep in g["CAND"][1.5]:
        if ep in used: continue
        z24=g["z24"][i]
        if not(np.isfinite(z24) and -np.sign(z24)==sd and abs(z24)>=0.5): continue
        if TR4[i]!=sd: continue
        out.append((i,sd)); used.add(ep)
    return out
SIG=d2sig()
# M15 fractals from M5 (UTC buckets), confirmed at close of bar m+1
b15=(pd.DatetimeIndex(BT).floor("15min")); df=pd.DataFrame({"h":BH,"l":BL,"b":b15})
m15=df.groupby("b").agg(h=("h","max"),l=("l","min")); H15=m15.h.to_numpy(); L15=m15.l.to_numpy(); T15=m15.index
fh=np.full(len(H15),np.nan); fl=np.full(len(H15),np.nan); lh=np.nan; ll=np.nan
for m in range(len(H15)):            # value known at close of m
    j=m-1
    if j>=1:
        if H15[j]>=H15[j-1] and H15[j]>H15[j+1]: lh=H15[j]
        if L15[j]<=L15[j-1] and L15[j]<L15[j+1]: ll=L15[j]
    fh[m]=lh; fl[m]=ll
pos15=np.searchsorted(T15.values,b15.values)          # M15 bucket of each M5 bar
end15=(pd.DatetimeIndex(BT)+pd.Timedelta("5min"))==(b15+pd.Timedelta("15min"))
# last CLOSED M15 index known at close of M5 bar i
last15=np.where(end15,pos15,pos15-1)
def entries(mode,W,stopm):
    out=[]
    for i,sd in SIG:
        a=BA[i]
        if mode=="NOW": trig=i
        else:
            trig=None
            for j in range(i+1,min(i+W*12,N-2)+1):
                if mode=="M5S3":
                    if sd>0 and BC[j]>BH[j-3:j].max(): trig=j;break
                    if sd<0 and BC[j]<BL[j-3:j].min(): trig=j;break
                else:
                    k=last15[j]; kp=last15[j-1]
                    if k<0: continue
                    lv=fh[k] if sd>0 else fl[k]; lvp=fh[kp] if sd>0 else fl[kp]
                    if not np.isfinite(lv): continue
                    if sd>0 and BC[j]>lv and BC[j-1]<=lvp: trig=j;break
                    if sd<0 and BC[j]<lv and BC[j-1]>=lvp: trig=j;break
            if trig is None: continue
        ei=trig+1; e=BO[ei]
        if stopm=="ATR3": dist=3*a
        else:
            if mode=="M15F":
                k=last15[trig]; lv=fl[k] if sd>0 else fh[k]
            else:
                lv=BL[trig-5:trig+1].min() if sd>0 else BH[trig-5:trig+1].max()
            dist=sd*(e-lv)+0.1*a if np.isfinite(lv) else 3*a
            dist=min(max(dist,0.5*a),3*a)
        out.append((ei,sd,e,dist,a))
    return out
def sim(EN):
    sig={}
    for ei,sd,e,d,a in EN: sig.setdefault(ei,[]).append((sd,d,a))
    idx=sorted(sig); act=[]; done=[]; eq=[]; real=0.0; p=0; i=idx[0]
    mt=lambda q,px:(q["s"]*(px-q["e"])-q["c"])/q["d"]
    while i<N:
        for sd,d,a in sig.get(i,[]):
            if len(act)==0 or (len(act)==1 and act[0]["s"]==sd and mt(act[0],BO[i])>=0):
                e=BO[i]; act.append(dict(s=sd,e=e,d=d,a=a,c=COST/1e4*e,end=min(i+575,N-1),i0=i,stp=e-sd*d,pk=0.0))
        keep=[]
        for q in act:
            s_,e=q["s"],q["e"]; res=None
            if (BL[i]<=q["stp"]) if s_>0 else (BH[i]>=q["stp"]): res=s_*(q["stp"]-e)
            else:
                q["pk"]=max(q["pk"],(BH[i]-e) if s_>0 else (e-BL[i]))
                if q["pk"]>=6*q["a"]:
                    ns=e+s_*(q["pk"]-9*q["a"])
                    q["stp"]=max(q["stp"],ns) if s_>0 else min(q["stp"],ns)
                if i>=q["end"]: res=s_*(BC[i]-e)
            if res is None: keep.append(q)
            else:
                r=(res-q["c"])/q["d"]; real+=r; done.append(dict(entry_i=q["i0"],net_r=r,d_atr=q["d"]/q["a"]))
        act=keep; eq.append((BT[i],real+sum(mt(q,BC[i]) for q in act)))
        if act: i+=1
        else:
            while p<len(idx) and idx[p]<=i: p+=1
            if p>=len(idx): break
            i=idx[p]
    return pd.DataFrame(done),pd.Series([v for _,v in eq],index=pd.DatetimeIndex([a for a,_ in eq]))
rows=[]
VAR=[("NOW",0,"ATR3")]+[(m,W,s) for m in ("M5S3","M15F") for W in (1,3,6) for s in ("ATR3","STRUCT")]
for m,W,s in VAR:
    EN=entries(m,W,s); t,e=sim(EN); tot=AB+al(e)*0.10
    # entry improvement vs signal: price gained/lost (ATR) in trade direction between signal next-open and actual entry
    sidx={i+1:sd for i,sd in SIG}
    r=dict(v=f"{m} {W}h {s}" if m!="NOW" else "NOW (зараз)",взято=len(EN)/len(SIG))
    imp=[]
    for ei,sd,e0,d,a in EN:
        # find originating signal: nearest signal before ei
        pass
    for seg,mk,mo in [("21-24",BT<TE,48),("25-26",BT>=TE,19.3)]:
        x=tot[mk]; x=x-x.iloc[0]; dd=float((x.cummax()-x).max())
        tt=t[(BT[t.entry_i.to_numpy(int)]<TE)==(seg=="21-24")]
        r.update({f"угод/міс {seg}":len(tt)/mo,f"EV {seg}":tt.net_r.mean(),f"стоп ATR {seg}":tt.d_atr.median(),f"WR {seg}":(tt.net_r>0).mean(),
                  f"%/міс {seg}":x.iloc[-1]/mo,f"DD {seg}":dd,f"R/DD {seg}":x.iloc[-1]/dd})
    rows.append(r); print(r["v"],flush=True)
R=pd.DataFrame(rows).set_index("v"); k=7/R[["DD 21-24","DD 25-26"]].max(axis=1)
R["$ 21-24"]=R["%/міс 21-24"]*k*1000; R["$ 25-26"]=R["%/міс 25-26"]*k*1000
R.to_csv("out_oos/LAB260_SWING_ENTRY.csv")
pd.set_option("display.width",350); print(R.round(2).to_string())
