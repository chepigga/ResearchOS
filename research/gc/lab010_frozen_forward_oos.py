import os, zipfile, json, math
from pathlib import Path
import pandas as pd, numpy as np

OUT=Path("lab010_out"); OUT.mkdir(exist_ok=True)
GC_ZIP=Path("gc_ticks.zip")
XAU_CSV=Path("xau_m1_2026.csv")
H=(1,3,5,10,15,30,60)
EPS=1e-12
NS=60_000_000_000

FEATURES=["atr_ratio","attack_impulse","h1_bias_trade","h4_bias_trade","h1_trend_trade","h4_trend_trade","m15_ema_bias_trade","m30_ema_bias_trade","m15_slope8_trade","m30_slope8_trade"]
MU=np.array([0.9753604272336306,-0.11487040110706151,0.010218865005918669,-0.02877109073435043,0.04580152671755725,-0.022900763358778626,-0.0012778962763255934,0.01670961685150088,-0.014372229816374565,-0.012276267782425649])
SC=np.array([0.18871000065914803,2.6938891049621403,1.4641230906061975,1.3836568924310928,0.9452917646974366,0.9146724453398868,0.7399399650942042,0.75545545977259,0.44517513767583705,0.44909062327389027])
CTR=np.array([
[-0.32184527375519933,-0.10173670811930037,0.38527732640719053,0.5904841408560407,0.8285889411011339,0.46422100854956627,0.002744837232914653,0.4097761561901306,-0.43138815915604684,-0.19159332767730214],
[0.07498112286450771,0.008359178130824952,-0.8465720071129778,-0.7851041802068167,-1.0117680990940903,-0.6590310703407836,-0.6293547482687747,-0.8229890191304429,-0.2519871307639209,-0.5117550149339656],
[0.24983789728465539,0.10728764911897411,1.0975148668410486,0.7365670492460146,0.8676451920516399,0.6562134390793918,1.158075814266595,1.024445609794887,0.9853413508041166,1.1754697630043736]])
REG={0:"ALIGNED_BIAS_LOCAL_PULLBACK",1:"COUNTER_BIAS",2:"ALIGNED_MOMENTUM_MATURE"}

def findcol(cols,names):
    m={c.lower().strip():c for c in cols}
    for n in names:
        if n in m:return m[n]
    for c in cols:
        lc=c.lower().strip()
        if any(n in lc for n in names):return c
    return None

def to_time(s):
    if pd.api.types.is_numeric_dtype(s):
        v=pd.to_numeric(s,errors="coerce")
        med=v.dropna().median()
        unit="ms" if med>1e11 else "s"
        return pd.to_datetime(v,unit=unit,utc=True,errors="coerce")
    return pd.to_datetime(s,utc=True,errors="coerce")

def load_gc():
    fs=[]
    with zipfile.ZipFile(GC_ZIP) as z:
        names=[n for n in z.namelist() if n.lower().endswith(".csv")]
        for n in names:
            try:
                df=pd.read_csv(z.open(n),sep=None,engine="python")
            except Exception:
                continue
            if len(df)==0: continue
            tc=findcol(df.columns,["time_msc","timestamp_ms","time","timestamp"])
            bc=findcol(df.columns,["is_buy","buy"])
            sc=findcol(df.columns,["is_sell","sell"])
            vc=findcol(df.columns,["volume_real","volume","vol","size","qty"])
            if not (tc and bc and sc and vc): continue
            t=to_time(df[tc]).dt.floor("min")
            b=pd.to_numeric(df[bc],errors="coerce").fillna(0).astype(int)
            s=pd.to_numeric(df[sc],errors="coerce").fillna(0).astype(int)
            v=pd.to_numeric(df[vc],errors="coerce").fillna(0.0)
            fs.append(pd.DataFrame({"minute":t,"buy_vol":np.where((b==1)&(s==0),v,0.0),"sell_vol":np.where((s==1)&(b==0),v,0.0)}))
    if not fs: raise RuntimeError("No explicit-aggressor GC data parsed")
    g=pd.concat(fs,ignore_index=True).dropna(subset=["minute"]).groupby("minute",as_index=False)[["buy_vol","sell_vol"]].sum().sort_values("minute").reset_index(drop=True)
    return g

def load_xau():
    # release file: detect delimiter and fields; historical convention is broker clock UTC+3
    x=pd.read_csv(XAU_CSV,sep=None,engine="python")
    tc=findcol(x.columns,["time","datetime","date"])
    oc=findcol(x.columns,["open"]); hc=findcol(x.columns,["high"]); lc=findcol(x.columns,["low"]); cc=findcol(x.columns,["close"])
    if not all([tc,oc,hc,lc,cc]): raise RuntimeError("XAU OHLC columns not found: "+str(list(x.columns)))
    raw=pd.to_datetime(x[tc],errors="coerce")
    if getattr(raw.dt,"tz",None) is None:
        minute=(raw-pd.Timedelta(hours=3)).dt.tz_localize("UTC")
    else:
        minute=raw.dt.tz_convert("UTC")
    q=pd.DataFrame({"minute":minute,"open":pd.to_numeric(x[oc],errors="coerce"),"high":pd.to_numeric(x[hc],errors="coerce"),"low":pd.to_numeric(x[lc],errors="coerce"),"close":pd.to_numeric(x[cc],errors="coerce")})
    # optional ask fields
    for fld in ["ask_open","ask_high","ask_low","ask_close"]:
        c=findcol(x.columns,[fld])
        if c:q[fld]=pd.to_numeric(x[c],errors="coerce")
    q=q.dropna(subset=["minute","open","high","low","close"]).sort_values("minute").drop_duplicates("minute").reset_index(drop=True)
    pc=q.close.shift(1)
    tr=pd.concat([(q.high-q.low),(q.high-pc).abs(),(q.low-pc).abs()],axis=1).max(axis=1)
    q["atr14"]=tr.rolling(14,min_periods=14).mean().shift(1)
    return q

def alignment(g):
    a=g.copy()
    cs=[]
    for h in H:
        b=a.buy_vol.rolling(h,min_periods=h).sum(); s=a.sell_vol.rolling(h,min_periods=h).sum()
        c=np.sign(np.log((b+EPS)/(s+EPS)))
        a[f"c{h}"]=c; cs.append(f"c{h}")
    ar=a[cs].to_numpy(float)
    a["buy_support"]=np.sum(ar==1,axis=1); a["sell_support"]=np.sum(ar==-1,axis=1)
    a["align"]=np.where(a.buy_support==7,1,np.where(a.sell_support==7,-1,0))
    rows=[]; prev=0
    for i,r in a.iterrows():
        sd=int(r["align"])
        if sd!=0 and sd!=prev: rows.append((i,r.minute,sd))
        prev=sd
    sat=pd.DataFrame(rows,columns=["gi","sat_time","crowd_side"])
    sat["sat_id"]=np.arange(len(sat))
    return a,sat

def make_pivots(x,tf=15):
    q=x.set_index("minute").resample(f"{tf}min",closed="left",label="left").agg(high=("high","max"),low=("low","min")).dropna().reset_index()
    rows=[]
    for i in range(2,len(q)-2):
        t=q.minute.iloc[i]; conf=t+pd.Timedelta(minutes=3*tf)
        if q.high.iloc[i]>q.high.iloc[i-1] and q.high.iloc[i]>q.high.iloc[i-2] and q.high.iloc[i]>q.high.iloc[i+1] and q.high.iloc[i]>q.high.iloc[i+2]:
            rows.append((1,t,conf,float(q.high.iloc[i])))
        if q.low.iloc[i]<q.low.iloc[i-1] and q.low.iloc[i]<q.low.iloc[i-2] and q.low.iloc[i]<q.low.iloc[i+1] and q.low.iloc[i]<q.low.iloc[i+2]:
            rows.append((-1,t,conf,float(q.low.iloc[i])))
    p=pd.DataFrame(rows,columns=["kind","pivot_time","confirm_time","level"])
    # active-until = first completed M1 close accepted beyond level after confirmation
    uts=[]
    times=x.minute.to_numpy()
    closes=x.close.to_numpy()
    for r in p.itertuples():
        j=x.minute.searchsorted(r.confirm_time)
        br=pd.Timestamp.max.tz_localize("UTC")
        if r.kind==1:
            z=np.flatnonzero(closes[j:]>r.level)
        else:z=np.flatnonzero(closes[j:]<r.level)
        if len(z): br=x.minute.iloc[j+int(z[0])]
        uts.append(br)
    p["active_until"]=uts
    return p

def build_signals(a,sat,x):
    p=make_pivots(x,15)
    gt=pd.Index(a.minute)
    xt=pd.Index(x.minute)
    rows=[]
    for e in sat.itertuples(index=False):
        if e.sat_time<x.minute.iloc[0] or e.sat_time>x.minute.iloc[-1]:continue
        kind=1 if e.crowd_side==1 else -1
        cand=p[(p.kind==kind)&(p.confirm_time<=e.sat_time)&(p.active_until>e.sat_time)]
        if cand.empty:continue
        pv=cand.iloc[-1]
        j=xt.searchsorted(e.sat_time)
        end=min(len(x),j+62); hit=None
        for k in range(j+1,end):
            if (e.crowd_side==1 and x.high.iloc[k]>=pv.level) or (e.crowd_side==-1 and x.low.iloc[k]<=pv.level):
                hit=k;break
        if hit is None:continue
        ct=x.minute.iloc[hit]
        i0=gt.searchsorted(ct); i5=gt.searchsorted(ct+pd.Timedelta(minutes=5))
        if i0>=len(a) or i5>=len(a) or a.minute.iloc[i0]!=ct or a.minute.iloc[i5]!=(ct+pd.Timedelta(minutes=5)):continue
        s0=int(a.buy_support.iloc[i0] if e.crowd_side==1 else a.sell_support.iloc[i0])
        s5=int(a.buy_support.iloc[i5] if e.crowd_side==1 else a.sell_support.iloc[i5])
        if s0-s5<3:continue
        rows.append({"sat_id":e.sat_id,"crowd_side":e.crowd_side,"side":"SELL" if e.crowd_side==1 else "BUY","sat_time":e.sat_time,"pivot_time":pv.pivot_time,"level":pv.level,"contact_time":ct,"signal_time":ct+pd.Timedelta(minutes=5),"atr_contact":x.atr14.iloc[hit],"support0":s0,"support5":s5})
    ev=pd.DataFrame(rows)
    if ev.empty:return ev
    ev=ev.sort_values("signal_time").drop_duplicates(["side","pivot_time","contact_time"]).reset_index(drop=True)
    return ev

def bars(x,tf):
    q=x.set_index("minute").resample(tf,closed="left",label="right").agg(open=("open","first"),high=("high","max"),low=("low","min"),close=("close","last")).dropna().reset_index()
    pc=q.close.shift(1); tr=pd.concat([(q.high-q.low),(q.high-pc).abs(),(q.low-pc).abs()],axis=1).max(axis=1)
    q["atr"]=tr.rolling(14,min_periods=14).mean()
    q["ema8"]=q.close.ewm(span=8,adjust=False).mean();q["ema20"]=q.close.ewm(span=20,adjust=False).mean()
    q["slope8"]=q.ema8-q.ema8.shift(4);q["slope20"]=q.ema20-q.ema20.shift(4)
    q["trend"]=np.where((q.close>q.ema20)&(q.ema20>q.ema20.shift(4)),1,np.where((q.close<q.ema20)&(q.ema20<q.ema20.shift(4)),-1,0))
    return q

def enrich_cluster(ev,x):
    if ev.empty:return ev
    h1=bars(x,"1h");h4=bars(x,"4h");m15=bars(x,"15min");m30=bars(x,"30min")
    h1["atr_med60"]=h1.atr.shift(1).rolling(60,min_periods=20).median()
    def getrow(q,t):
        j=q.minute.searchsorted(t,side="right")-1
        return q.iloc[j] if j>=0 else None
    xx=x.set_index("minute")
    out=[]
    for r in ev.itertuples(index=False):
        rr=r._asdict(); ss=1 if r.side=="BUY" else -1
        a1=getrow(h1,r.signal_time);a4=getrow(h4,r.signal_time);a15=getrow(m15,r.signal_time);a30=getrow(m30,r.signal_time)
        if any(v is None for v in [a1,a4,a15,a30]):continue
        try:
            c0=float(xx.loc[r.contact_time,"close"])
            t15=r.contact_time-pd.Timedelta(minutes=15)
            j=x.minute.searchsorted(t15,side="right")-1
            c15=float(x.close.iloc[j]); atr=float(r.atr_contact)
            impulse15=(r.crowd_side*(c0-c15)/atr) if atr>0 else np.nan
            feat=np.array([
                a1.atr/a1.atr_med60,
                -ss*impulse15,
                ss*(a1.close-a1.ema20)/a1.atr,
                ss*(a4.close-a4.ema20)/a4.atr,
                ss*a1.trend,ss*a4.trend,
                ss*((a15.ema8-a15.ema20)/a15.atr),
                ss*((a30.ema8-a30.ema20)/a30.atr),
                ss*(a15.slope8/a15.atr),
                ss*(a30.slope8/a30.atr)
            ],float)
        except Exception:continue
        if not np.isfinite(feat).all():continue
        z=(feat-MU)/SC; cid=int(np.argmin(np.sum((CTR-z)**2,axis=1)))
        rr.update({FEATURES[i]:feat[i] for i in range(len(FEATURES))});rr["cluster"]=cid;rr["regime"]=REG[cid]
        out.append(rr)
    return pd.DataFrame(out)

def simulate(ev,x,retr):
    rows=[]
    for r in ev.itertuples(index=False):
        st=r.signal_time+pd.Timedelta(minutes=1)
        j=x.minute.searchsorted(st)
        if j>=len(x):continue
        market=float(x.open.iloc[j]); atr=float(r.atr_contact)
        if r.side=="BUY":
            limit=r.level+(1-retr)*(market-r.level)
            sl=r.level-0.25*atr
            risk=limit-sl
            if risk<=0:continue
        else:
            limit=r.level-(1-retr)*(r.level-market)
            sl=r.level+0.25*atr
            risk=sl-limit
            if risk<=0:continue
        tp=limit+(2*risk if r.side=="BUY" else -2*risk)
        # 30m fill
        fill=None
        for k in range(j,min(len(x),j+31)):
            if (r.side=="BUY" and x.low.iloc[k]<=limit) or (r.side=="SELL" and x.high.iloc[k]>=limit):
                fill=k;break
        R=0.0; reason="UNFILLED"; exit_t=pd.NaT
        if fill is not None:
            reason="TIME";end=min(len(x),fill+121);exit_t=x.minute.iloc[end-1]
            Rgross=0.0
            for k in range(fill,end):
                hit_sl=(x.low.iloc[k]<=sl) if r.side=="BUY" else (x.high.iloc[k]>=sl)
                hit_tp=(x.high.iloc[k]>=tp) if r.side=="BUY" else (x.low.iloc[k]<=tp)
                if hit_sl and hit_tp: Rgross=-1.0;reason="SL_AMBIG";exit_t=x.minute.iloc[k];break
                if hit_sl:Rgross=-1.0;reason="SL";exit_t=x.minute.iloc[k];break
                if hit_tp:Rgross=2.0;reason="TP";exit_t=x.minute.iloc[k];break
            else:
                last=float(x.close.iloc[end-1])
                Rgross=((last-limit)/risk) if r.side=="BUY" else ((limit-last)/risk)
            # approximate FTMO metals commission 0.0007% notional per side, 100 oz/lot cancels in R ratio
            commissionR=(0.000014*limit)/risk
            R=Rgross-commissionR
        rows.append({"signal_time":r.signal_time,"side":r.side,"regime":r.regime,"retr_frac":retr,"filled":fill is not None,"R":R,"reason":reason,"exit_time":exit_t})
    return pd.DataFrame(rows)

g=load_gc(); x=load_xau()
# forward cutoff and actual overlap
g=g[g.minute>pd.Timestamp("2026-07-28",tz="UTC")].reset_index(drop=True)
x=x[x.minute>pd.Timestamp("2026-07-28",tz="UTC")].reset_index(drop=True)
a,sat=alignment(g)
ev=build_signals(a,sat,x)
ev=enrich_cluster(ev,x)
# Forward signal-quality audit independent of the invalid old cluster
xtidx=pd.Index(x.minute)
quality=[]
for r in ev.itertuples(index=False):
    ci=xtidx.searchsorted(r.contact_time)
    if ci>=len(x) or x.minute.iloc[ci]!=r.contact_time: continue
    end=min(len(x),ci+31); atr=float(r.atr_contact); level=float(r.level)
    cont_i=999; rev_i=999
    for k in range(ci,end):
        if r.crowd_side==1:
            cont=x.high.iloc[k]>=level+atr; rev=x.low.iloc[k]<=level-atr
        else:
            cont=x.low.iloc[k]<=level-atr; rev=x.high.iloc[k]>=level+atr
        if cont and cont_i==999: cont_i=k-ci
        if rev and rev_i==999: rev_i=k-ci
    outcome="REV" if rev_i<cont_i else ("CONT" if cont_i<rev_i else ("AMBIG" if rev_i<999 else "NONE"))
    quality.append({"signal_time":r.signal_time,"side":r.side,"crowd_side":r.crowd_side,"outcome":outcome,"rev_i":rev_i,"cont_i":cont_i})
Q=pd.DataFrame(quality)
Q.to_csv(OUT/"LAB010_FORWARD_SIGNAL_QUALITY.csv",index=False)

# Strict causal signal audit starting at signal_time, not contact_time.
causal=[]
xtidx=pd.Index(x.minute)
for r in ev.itertuples(index=False):
    si=xtidx.searchsorted(r.signal_time)
    if si>=len(x) or x.minute.iloc[si]!=r.signal_time: continue
    ref=float(x.close.iloc[si]); atr=float(r.atr_contact)
    if not np.isfinite(atr) or atr<=0: continue
    sgn=1 if r.side=="BUY" else -1
    row={"signal_time":r.signal_time,"side":r.side,"ref":ref,"atr":atr}
    first_fav=999; first_adv=999
    end=min(len(x),si+61)
    for k in range(si+1,end):
        fav=((x.high.iloc[k]-ref)/atr) if sgn==1 else ((ref-x.low.iloc[k])/atr)
        adv=((ref-x.low.iloc[k])/atr) if sgn==1 else ((x.high.iloc[k]-ref)/atr)
        if fav>=1 and first_fav==999:first_fav=k-si
        if adv>=1 and first_adv==999:first_adv=k-si
    row["first_fav_1atr"]=first_fav; row["first_adv_1atr"]=first_adv
    row["outcome_1atr"]="FAV" if first_fav<first_adv else ("ADV" if first_adv<first_fav else ("AMBIG" if first_fav<999 else "NONE"))
    for h in [5,10,15,30,60]:
        j=min(len(x)-1,si+h)
        sl=x.iloc[si+1:j+1]
        row[f"ret{h}_atr"]=sgn*(float(x.close.iloc[j])-ref)/atr
        if len(sl):
            row[f"mfe{h}_atr"]=((float(sl.high.max())-ref)/atr) if sgn==1 else ((ref-float(sl.low.min()))/atr)
            row[f"mae{h}_atr"]=((ref-float(sl.low.min()))/atr) if sgn==1 else ((float(sl.high.max())-ref)/atr)
        else:
            row[f"mfe{h}_atr"]=np.nan; row[f"mae{h}_atr"]=np.nan
    causal.append(row)
CQ=pd.DataFrame(causal)
CQ.to_csv(OUT/"LAB010_CAUSAL_SIGNAL_AUDIT_FROM_SIGNAL_TIME.csv",index=False)
cs=[]
if len(CQ):
    for scope,z in [("ALL",CQ),("BUY",CQ[CQ.side=="BUY"]),("SELL",CQ[CQ.side=="SELL"])]:
        resolved=z[z.outcome_1atr.isin(["FAV","ADV"])]
        rr={"scope":scope,"n":len(z),"resolved":len(resolved),"fav_first_pct":100*(resolved.outcome_1atr=="FAV").mean() if len(resolved) else np.nan}
        for h in [5,10,15,30,60]:
            rr[f"mean_ret{h}_atr"]=z[f"ret{h}_atr"].mean()
            rr[f"median_ret{h}_atr"]=z[f"ret{h}_atr"].median()
            rr[f"mean_mfe{h}_atr"]=z[f"mfe{h}_atr"].mean()
            rr[f"mean_mae{h}_atr"]=z[f"mae{h}_atr"].mean()
        cs.append(rr)
CS=pd.DataFrame(cs)
CS.to_csv(OUT/"LAB010_CAUSAL_SIGNAL_SUMMARY_FROM_SIGNAL_TIME.csv",index=False)
resolved=Q[Q.outcome.isin(["REV","CONT"])] if len(Q) else Q
qsum={"signals":int(len(Q)),"resolved":int(len(resolved)),"reversal_rate_pct":float(100*(resolved.outcome=="REV").mean()) if len(resolved) else None}
(OUT/"LAB010_SIGNAL_QUALITY_SUMMARY.json").write_text(json.dumps(qsum,indent=2))

alltr=[]
for rf in [0.5,0.75]:
    zz=simulate(ev,x,rf); zz["scope"]="ALL_REGIMES"; alltr.append(zz)
ALLT=pd.concat(alltr,ignore_index=True) if alltr else pd.DataFrame()
ALLT.to_csv(OUT/"LAB010_FORWARD_EXECUTION_ALL.csv",index=False)
alls=[]
for rf in [0.5,0.75]:
    z=ALLT[ALLT.retr_frac==rf] if len(ALLT) else pd.DataFrame()
    if len(z):
        alls.append({"retr_frac":rf,"signals":len(z),"filled":int(z.filled.sum()),"fill_rate_pct":100*z.filled.mean(),"mean_R_per_signal":z.R.mean(),"sum_R":z.R.sum(),"mean_R_filled":z.loc[z.filled,"R"].mean() if z.filled.any() else np.nan})
pd.DataFrame(alls).to_csv(OUT/"LAB010_FORWARD_SUMMARY_ALL.csv",index=False)

# Exact monetization candidate from corrected historical replay:
# M15 COLLAPSE, BUY only, H1&H4 trend aligned, +0.5 ATR response within 3m,
# enter next M1 open, 2 ATR stop, TP 3R, max hold 30m.
mon=[]
xti=pd.Index(x.minute)
for r in ev.itertuples(index=False):
    if r.side!="BUY" or r.h1_trend_trade!=1 or r.h4_trend_trade!=1: continue
    si=xti.searchsorted(r.signal_time)
    if si>=len(x) or x.minute.iloc[si]!=r.signal_time: continue
    ref=float(x.close.iloc[si]); atr0=float(r.atr_contact)
    ei=None
    for k in range(si+1,min(len(x)-1,si+4)):
        if (float(x.close.iloc[k])-ref)/atr0>=0.5:
            ei=k+1; break
    if ei is None: continue
    entry=float(x.ask_open.iloc[ei]) if "ask_open" in x.columns else float(x.open.iloc[ei])
    stop=entry-2.0*atr0; risk=entry-stop; tp=entry+3.0*risk
    end=min(len(x),ei+31); gr=None; reason=None; exi=None
    for k in range(ei,end):
        low=float(x.low.iloc[k]); high=float(x.high.iloc[k])
        if low<=stop and high>=tp:
            gr=-1.0; reason="SL_AMBIG"; exi=k; break
        if low<=stop:
            gr=-1.0; reason="SL"; exi=k; break
        if high>=tp:
            gr=3.0; reason="TP"; exi=k; break
    if gr is None:
        exi=end-1; exitp=float(x.close.iloc[exi]); gr=(exitp-entry)/risk; reason="TIME"
    # conservative $7 RT/lot commission proxy
    net=gr-7.0/(risk*100.0)
    mon.append({"signal_time":r.signal_time,"entry_time":x.minute.iloc[ei],"exit_time":x.minute.iloc[exi],"R":net,"grossR":gr,"reason":reason,"h1_trend_trade":r.h1_trend_trade,"h4_trend_trade":r.h4_trend_trade})
MON=pd.DataFrame(mon)
MON.to_csv(OUT/"LAB010_MONETIZATION_CANDIDATE_FORWARD.csv",index=False)
if len(MON):
    MON["month"]=pd.to_datetime(MON.exit_time,utc=True).dt.to_period("M").astype(str)
    ms=MON.groupby("month").agg(N=("R","size"),sumR=("R","sum"),meanR=("R","mean")).reset_index()
    ms.to_csv(OUT/"LAB010_MONETIZATION_CANDIDATE_MONTHLY.csv",index=False)
    rr=MON.sort_values("exit_time").R.to_numpy()
    eq=np.r_[0,np.cumsum(rr)]; dd=np.maximum.accumulate(eq)-eq
    days=MON.assign(day=pd.to_datetime(MON.exit_time,utc=True).dt.date).groupby("day").R.sum()
    met={"N":int(len(MON)),"sumR":float(rr.sum()),"meanR":float(rr.mean()),"maxddR":float(dd.max()),"worstdayR":float(-min(0,days.min()))}
else:
    ms=pd.DataFrame(); met={"N":0}
(OUT/"LAB010_MONETIZATION_CANDIDATE_METRICS.json").write_text(json.dumps(met,indent=2))
# Broad forward monetization grid for intersection with historical robustness.
grid=[]
for filt in ["NONE","H1","H4","H1H4"]:
  for thr in [0.0,0.1,0.2,0.3,0.5]:
    for wait in [3,5]:
      for stop_atr in [1.0,1.25,1.5,2.0,2.5]:
        for rr0 in [1.5,2.0,2.5,3.0]:
          for hold0 in [15,30]:
            rs=[]
            for r in ev.itertuples(index=False):
              if r.side!="BUY": continue
              if filt=="H1" and r.h1_trend_trade!=1: continue
              if filt=="H4" and r.h4_trend_trade!=1: continue
              if filt=="H1H4" and not (r.h1_trend_trade==1 and r.h4_trend_trade==1): continue
              si=xti.searchsorted(r.signal_time)
              if si>=len(x) or x.minute.iloc[si]!=r.signal_time: continue
              ref=float(x.close.iloc[si]); atr0=float(r.atr_contact)
              ei=None
              for k in range(si+1,min(len(x)-1,si+wait+1)):
                if (float(x.close.iloc[k])-ref)/atr0>=thr:
                  ei=k+1; break
              if ei is None: continue
              entry=float(x.ask_open.iloc[ei]) if "ask_open" in x.columns else float(x.open.iloc[ei])
              stop=entry-stop_atr*atr0; risk=entry-stop; tp=entry+rr0*risk
              end=min(len(x),ei+hold0+1); gr=None; exi=None
              for k in range(ei,end):
                lo=float(x.low.iloc[k]); hi=float(x.high.iloc[k])
                if lo<=stop and hi>=tp: gr=-1.; exi=k; break
                if lo<=stop: gr=-1.; exi=k; break
                if hi>=tp: gr=rr0; exi=k; break
              if gr is None:
                exi=end-1; gr=(float(x.close.iloc[exi])-entry)/risk
              net=gr-7.0/(risk*100.0)
              rs.append((x.minute.iloc[exi],net))
            if len(rs)<3: continue
            z=pd.DataFrame(rs,columns=["time","R"]).sort_values("time")
            z["month"]=pd.to_datetime(z.time,utc=True).dt.to_period("M").astype(str)
            eq=np.r_[0,z.R.cumsum().to_numpy()]; dd=np.maximum.accumulate(eq)-eq
            ms=z.groupby("month").R.sum().to_dict()
            grid.append({"filter":filt,"thr":thr,"wait":wait,"stop_atr":stop_atr,"rr":rr0,"hold":hold0,
                         "N":len(z),"sumR":z.R.sum(),"meanR":z.R.mean(),"maxddR":dd.max(),
                         "augR":ms.get("2026-08",0.0),"sepR":ms.get("2026-09",0.0)})
pd.DataFrame(grid).to_csv(OUT/"LAB010_FORWARD_MONETIZATION_GRID.csv",index=False)
# Structural-stop forward grid.
sgrid=[]
for filt in ["NONE","H1","H4","H1H4"]:
  for thr in [0.0,0.1,0.2,0.3,0.5]:
    for wait in [3,5]:
      for buf in [0.25,0.5,0.75]:
        for rr0 in [1.5,2.0,2.5,3.0]:
          for hold0 in [15,30]:
            rs=[]
            for r in ev.itertuples(index=False):
              if r.side!="BUY": continue
              if filt=="H1" and r.h1_trend_trade!=1: continue
              if filt=="H4" and r.h4_trend_trade!=1: continue
              if filt=="H1H4" and not (r.h1_trend_trade==1 and r.h4_trend_trade==1): continue
              si=xti.searchsorted(r.signal_time)
              if si>=len(x) or x.minute.iloc[si]!=r.signal_time: continue
              ref=float(x.close.iloc[si]); atr0=float(r.atr_contact)
              ei=None
              for k in range(si+1,min(len(x)-1,si+wait+1)):
                if (float(x.close.iloc[k])-ref)/atr0>=thr:
                  ei=k+1; break
              if ei is None: continue
              entry=float(x.ask_open.iloc[ei]) if "ask_open" in x.columns else float(x.open.iloc[ei])
              stop=float(r.level)-buf*atr0
              if stop>=entry: continue
              risk=entry-stop
              if risk<=0 or risk>4*atr0: continue
              tp=entry+rr0*risk
              end=min(len(x),ei+hold0+1); gr=None; exi=None
              for k in range(ei,end):
                lo=float(x.low.iloc[k]); hi=float(x.high.iloc[k])
                if lo<=stop and hi>=tp: gr=-1.; exi=k; break
                if lo<=stop: gr=-1.; exi=k; break
                if hi>=tp: gr=rr0; exi=k; break
              if gr is None:
                exi=end-1; gr=(float(x.close.iloc[exi])-entry)/risk
              net=gr-7.0/(risk*100.0)
              rs.append((x.minute.iloc[exi],net))
            if len(rs)<3: continue
            z=pd.DataFrame(rs,columns=["time","R"]).sort_values("time")
            z["month"]=pd.to_datetime(z.time,utc=True).dt.to_period("M").astype(str)
            eq=np.r_[0,z.R.cumsum().to_numpy()]; dd=np.maximum.accumulate(eq)-eq
            ms=z.groupby("month").R.sum().to_dict()
            sgrid.append({"filter":filt,"thr":thr,"wait":wait,"struct_buf":buf,"rr":rr0,"hold":hold0,
                          "N":len(z),"sumR":z.R.sum(),"meanR":z.R.mean(),"maxddR":dd.max(),
                          "augR":ms.get("2026-08",0.0),"sepR":ms.get("2026-09",0.0)})
pd.DataFrame(sgrid).to_csv(OUT/"LAB010_FORWARD_MONETIZATION_STRUCT_GRID.csv",index=False)



ev.to_csv(OUT/"LAB010_FORWARD_SIGNALS_WITH_REGIME.csv",index=False)

trades=[]
for rf in [0.5,0.75]:
    t=simulate(ev[ev.regime=="ALIGNED_BIAS_LOCAL_PULLBACK"],x,rf)
    trades.append(t)
T=pd.concat(trades,ignore_index=True) if trades else pd.DataFrame()
T.to_csv(OUT/"LAB010_FORWARD_EXECUTION.csv",index=False)

summary=[]
for rf in [0.5,0.75]:
    z=T[T.retr_frac==rf] if len(T) else pd.DataFrame()
    if len(z):
        summary.append({"retr_frac":rf,"signals":len(z),"filled":int(z.filled.sum()),"fill_rate_pct":100*z.filled.mean(),"mean_R_per_signal":z.R.mean(),"sum_R":z.R.sum(),"mean_R_filled":z.loc[z.filled,"R"].mean() if z.filled.any() else np.nan})
S=pd.DataFrame(summary); S.to_csv(OUT/"LAB010_FORWARD_SUMMARY.csv",index=False)

meta={"gc_start":str(g.minute.min()),"gc_end":str(g.minute.max()),"gc_m1":len(g),"xau_start":str(x.minute.min()),"xau_end":str(x.minute.max()),"xau_m1":len(x),"saturations":len(sat),"frozen_signals_all_regimes":len(ev),"aligned_bias_local_pullback":int((ev.regime=="ALIGNED_BIAS_LOCAL_PULLBACK").sum()) if len(ev) else 0,"xau_columns":list(x.columns)}
(OUT/"LAB010_META.json").write_text(json.dumps(meta,indent=2,default=str))
report="# LAB010 Frozen Forward OOS\n\n"+json.dumps(meta,indent=2,default=str)+"\n\n## Signal quality\n"+json.dumps(qsum,indent=2)+"\n\n## Old-cluster execution (diagnostic only)\n"+(S.to_markdown(index=False) if len(S) else "NO EXECUTION CANDIDATES")+"\n\n## All-signal execution\n"+(pd.DataFrame(alls).to_markdown(index=False) if len(alls) else "NONE")+"\n"
(OUT/"LAB010_REPORT.md").write_text(report)
print(report)
