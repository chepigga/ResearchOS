#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd

LAB="XAU_VWAP_SEQUENCE_PLACEBO_AND_EXECUTION_FRONTIER_LAB_003"
VERSION="v001"
CANONICAL="XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv"
SHA="db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b"
HOLDOUT=pd.Timestamp("2025-07-01")
DISC_END=pd.Timestamp("2024-01-01")
ANCHOR_HOUR=1
BAND_K=1.618
TOUCH_ATR=.05
REARM_ATR=.25
DECISION_THRESHOLD=.10
CLOCKS=(1,3,5)
FEATURE_MIN=5
OUTCOME_MIN=60
PRIMARY_BARRIER=.50
BOOT_N=4000
BOOT_SEED=20260822
MIN_CELL_SIDE=5

FAMILY_COLS={
    "VWAP_VOLUME":{"MID":"V_MID","HIGH":"V_HIGH","LOW":"V_LOW"},
    "ANCHOR_MEAN":{"MID":"M_MID","HIGH":"M_HIGH","LOW":"M_LOW"},
    "LAGGED_VWAP_SHAPE":{"MID":"P_MID","HIGH":"P_HIGH","LOW":"P_LOW"},
}

def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def load(path:Path)->pd.DataFrame:
    df=pd.read_csv(path,sep=";")
    need=["time","open","high","low","close","tick_volume"]
    miss=[c for c in need if c not in df.columns]
    if miss: raise ValueError(f"missing {miss}")
    keep=[c for c in ["time","open","high","low","close","ask_high","ask_low","ask_close","tick_volume","spread_mean"] if c in df.columns]
    df=df[keep].copy()
    df["time"]=pd.to_datetime(df.time,format="%Y.%m.%d %H:%M",errors="coerce")
    for c in df.columns:
        if c!="time": df[c]=pd.to_numeric(df[c],errors="coerce")
    df=df.dropna(subset=["time","open","high","low","close"]).sort_values("time").drop_duplicates("time",keep="last").reset_index(drop=True)
    if (df.high<df.low).any(): raise ValueError("OHLC integrity failure")
    return df

def wilder_atr(h,l,c,n=14):
    pc=c.shift(1)
    tr=pd.concat([(h-l),(h-pc).abs(),(l-pc).abs()],axis=1).max(axis=1)
    return tr.ewm(alpha=1/n,adjust=False,min_periods=n).mean()

def add_atr(df):
    x=df.set_index("time")
    m=x.resample("15min",label="left",closed="left").agg(
        open=("open","first"),high=("high","max"),low=("low","min"),close=("close","last")
    ).dropna()
    m["atr"]=wilder_atr(m.high,m.low,m.close,14)
    a=m[["atr"]].reset_index()
    a["avail"]=a.time+pd.Timedelta(minutes=15)
    a=a[["avail","atr"]].dropna().sort_values("avail")
    return pd.merge_asof(df.sort_values("time"),a,left_on="time",right_on="avail",direction="backward").drop(columns="avail")

def add_level_families(df):
    o=df.copy()
    o["session"]=(o.time-pd.Timedelta(hours=ANCHOR_HOUR)).dt.floor("D")
    anchor=o["session"]+pd.Timedelta(hours=ANCHOR_HOUR)
    o["offset_min"]=((o.time-anchor).dt.total_seconds()/60).astype(int)
    p=(o.high+o.low+o.close)/3.0

    v=o.tick_volume.fillna(0).clip(lower=0)
    gv=v.groupby(o.session).cumsum()
    gpv=(p*v).groupby(o.session).cumsum()
    gp2=((p*p)*v).groupby(o.session).cumsum()
    vmid=gpv/gv.replace(0,np.nan)
    vvar=(gp2/gv.replace(0,np.nan)-vmid*vmid).clip(lower=0)
    vsd=np.sqrt(vvar)
    o["V_MID"]=vmid
    o["V_HIGH"]=vmid+BAND_K*vsd
    o["V_LOW"]=vmid-BAND_K*vsd

    cnt=o.groupby("session").cumcount()+1
    psum=p.groupby(o.session).cumsum()
    p2sum=(p*p).groupby(o.session).cumsum()
    mmid=psum/cnt
    mvar=(p2sum/cnt-mmid*mmid).clip(lower=0)
    msd=np.sqrt(mvar)
    o["M_MID"]=mmid
    o["M_HIGH"]=mmid+BAND_K*msd
    o["M_LOW"]=mmid-BAND_K*msd

    session_open=o.groupby("session")["open"].transform("first")
    o["session_open"]=session_open
    sessions=pd.Index(pd.unique(o.session)).sort_values()
    prev_map={sessions[i]: (sessions[i-1] if i>0 else pd.NaT) for i in range(len(sessions))}
    o["prev_session"]=o.session.map(prev_map)

    prev=o[["session","offset_min","V_MID","V_HIGH","V_LOW","session_open"]].copy()
    prev=prev.drop_duplicates(["session","offset_min"],keep="last")
    prev=prev.rename(columns={
        "session":"prev_session",
        "V_MID":"PV_MID","V_HIGH":"PV_HIGH","V_LOW":"PV_LOW",
        "session_open":"prev_session_open"
    })
    o["_row"]=np.arange(len(o))
    o=o.merge(prev,on=["prev_session","offset_min"],how="left",sort=False)
    o=o.sort_values("_row").drop(columns="_row").reset_index(drop=True)
    gap=o.session_open-o.prev_session_open
    o["P_MID"]=o.PV_MID+gap
    o["P_HIGH"]=o.PV_HIGH+gap
    o["P_LOW"]=o.PV_LOW+gap
    return o.drop(columns=["PV_MID","PV_HIGH","PV_LOW","prev_session_open"],errors="ignore")

def detect_touches(df,family,role,col):
    line=df[col].to_numpy(float)
    atr=df.atr.to_numpy(float)
    lo=df.low.to_numpy(float); hi=df.high.to_numpy(float); cl=df.close.to_numpy(float)
    sessions=df.session.to_numpy()
    n=len(df); armed=True; rows=[]; touch_no={}
    for i in range(6,n-OUTCOME_MIN-2):
        L=line[i]; A=atr[i]
        if not np.isfinite(L) or not np.isfinite(A) or A<=0: continue
        dist=abs(cl[i]-L)/A
        if not armed:
            if dist>=REARM_ATR: armed=True
            else: continue
        near=(lo[i] <= L+TOUCH_ATR*A) and (hi[i] >= L-TOUCH_ATR*A)
        if not near: continue
        arr=0
        for j in range(i-1,max(-1,i-6),-1):
            if not np.isfinite(line[j]) or not np.isfinite(atr[j]) or atr[j]<=0: continue
            d=(cl[j]-line[j])/atr[j]
            if abs(d)>TOUCH_ATR:
                arr=1 if d>0 else -1
                break
        if arr==0: continue
        key=(sessions[i],family,role)
        tn=touch_no.get(key,0)+1; touch_no[key]=tn
        rows.append((i,family,role,col,arr,tn))
        armed=False
    return rows

def label_barrier(df,i,arr,L0,atr0):
    start=i+FEATURE_MIN+1
    t_end=df.at[i,"time"]+pd.Timedelta(minutes=OUTCOME_MIN)
    times=df.time.to_numpy(dtype="datetime64[ns]")
    end=int(np.searchsorted(times,np.datetime64(t_end),side="right"))
    end=min(end,len(df))
    if start>=end: return "UNRESOLVED"
    h=df.high.to_numpy(float)[start:end]; l=df.low.to_numpy(float)[start:end]
    rej=L0+arr*PRIMARY_BARRIER*atr0
    acc=L0-arr*PRIMARY_BARRIER*atr0
    if arr>0:
        r=np.flatnonzero(h>=rej); a=np.flatnonzero(l<=acc)
    else:
        r=np.flatnonzero(l<=rej); a=np.flatnonzero(h>=acc)
    pr=int(r[0]) if len(r) else 10**9
    pa=int(a[0]) if len(a) else 10**9
    if pr==pa and pr<10**9: return "AMBIGUOUS"
    if pr<pa: return "REJECTION"
    if pa<pr: return "ACCEPTANCE"
    return "UNRESOLVED"

def decision_state(s):
    if not np.isfinite(s): return "INVALID"
    if s>=DECISION_THRESHOLD: return "BACK"
    if s<=-DECISION_THRESHOLD: return "THROUGH"
    return "NEUTRAL"

def event_for_touch(df,rec):
    i,family,role,col,arr,tn=rec
    if i+FEATURE_MIN>=len(df): return None
    t0=df.at[i,"time"]
    for k in range(1,FEATURE_MIN+1):
        if df.at[i+k,"time"] != t0+pd.Timedelta(minutes=k): return None
    atr0=float(df.at[i,"atr"]); L0=float(df.at[i,col])
    if not np.isfinite(atr0) or atr0<=0 or not np.isfinite(L0): return None
    row={
        "i":int(i),"time":t0,"session":df.at[i,"session"],"year":int(t0.year),
        "family":family,"level":role,"arrival_side":int(arr),
        "arrival_from":"ABOVE" if arr>0 else "BELOW","touch_number":int(tn),
        "atr0":atr0,"level0":L0,
    }
    for k in CLOCKS:
        Lk=float(df.at[i+k,col]); ck=float(df.at[i+k,"close"])
        s=arr*(ck-Lk)/atr0 if np.isfinite(Lk) else np.nan
        row[f"s_{k}m"]=float(s) if np.isfinite(s) else np.nan
        row[f"state_{k}m"]=decision_state(s)
    row["label_0p5"]=label_barrier(df,i,arr,L0,atr0)
    return row

def add_split(e):
    x=e.copy()
    t=pd.to_datetime(x.time)
    x["split"]=np.where(t<DISC_END,"DISCOVERY","CONFIRMATION")
    x["week"]=(t-pd.to_timedelta(t.dt.weekday,unit="D")).dt.floor("D")
    return x

def stats_one(g,clock):
    state=g[f"state_{clock}m"]
    signal=state.isin(["BACK","THROUGH"])
    resolved=g.label_0p5.isin(["REJECTION","ACCEPTANCE"])
    sr=signal & resolved
    back=sr & state.eq("BACK")
    thru=sr & state.eq("THROUGH")
    correct=(back & g.label_0p5.eq("REJECTION")) | (thru & g.label_0p5.eq("ACCEPTANCE"))
    rb=float((g.loc[back,"label_0p5"]=="REJECTION").mean()) if back.any() else np.nan
    rt=float((g.loc[thru,"label_0p5"]=="REJECTION").mean()) if thru.any() else np.nan
    return {
        "n":int(len(g)),
        "coverage":float(signal.mean()) if len(g) else np.nan,
        "resolved_signal_n":int(sr.sum()),
        "accuracy":float(correct.sum()/sr.sum()) if sr.sum() else np.nan,
        "back_n":int(back.sum()),"through_n":int(thru.sum()),
        "rejection_rate_back":rb,"rejection_rate_through":rt,
        "separation":float(rb-rt) if np.isfinite(rb) and np.isfinite(rt) else np.nan,
    }

def make_map(e,groups):
    rows=[]
    for keys,g in e.groupby(groups,dropna=False,observed=False):
        if not isinstance(keys,tuple): keys=(keys,)
        base=dict(zip(groups,keys))
        for clock in CLOCKS:
            rows.append(base|{"clock":clock}|stats_one(g,clock))
    return pd.DataFrame(rows)

def weekly_separation(e,split,family,clock):
    x=e[(e.split==split)&(e.family==family)].copy()
    state=x[f"state_{clock}m"]
    x=x[x.label_0p5.isin(["REJECTION","ACCEPTANCE"]) & state.isin(["BACK","THROUGH"])].copy()
    x["decision"]=state.loc[x.index]
    rows=[]
    for (week,arr),g in x.groupby(["week","arrival_side"]):
        b=g[g.decision=="BACK"]; t=g[g.decision=="THROUGH"]
        if len(b)<MIN_CELL_SIDE or len(t)<MIN_CELL_SIDE: continue
        rb=float((b.label_0p5=="REJECTION").mean())
        rt=float((t.label_0p5=="REJECTION").mean())
        rows.append({"week":week,"arrival_side":int(arr),"family":family,"sep":rb-rt,"back_n":len(b),"through_n":len(t)})
    return pd.DataFrame(rows)

def paired_boot(e,split,clock,other):
    a=weekly_separation(e,split,"VWAP_VOLUME",clock).rename(columns={"sep":"vwap_sep"})
    b=weekly_separation(e,split,other,clock).rename(columns={"sep":"other_sep"})
    if a.empty or b.empty:
        return {"n_cells":0,"mean_diff":None,"ci95":[None,None]}
    z=a[["week","arrival_side","vwap_sep"]].merge(b[["week","arrival_side","other_sep"]],on=["week","arrival_side"],how="inner")
    if len(z)<8: return {"n_cells":int(len(z)),"mean_diff":None,"ci95":[None,None]}
    vals=(z.vwap_sep-z.other_sep).to_numpy(float)
    rng=np.random.default_rng(BOOT_SEED)
    boots=np.empty(BOOT_N)
    for i in range(BOOT_N):
        boots[i]=rng.choice(vals,size=len(vals),replace=True).mean()
    return {
        "n_cells":int(len(vals)),
        "mean_diff":float(vals.mean()),
        "ci95":[float(np.quantile(boots,.025)),float(np.quantile(boots,.975))],
        "vwap_mean_sep":float(z.vwap_sep.mean()),
        "other_mean_sep":float(z.other_sep.mean()),
    }

def build_report(audit,verdict,core_map,paired):
    lines=[
        f"# {LAB} — {VERSION} REPORT","",
        f"**Verdict:** `{verdict['status']}`  ",
        f"**Holdout opened:** `{str(audit['holdout_opened']).lower()}`","",
        "## Canonical audit","",
        f"- SHA-256: `{audit['sha256']}`",
        f"- pre-holdout rows: {audit['rows_pre_holdout']:,}",
        f"- mapped events: {audit['mapped_events']:,}",
        f"- VWAP / mean / lagged-placebo events: {audit['family_counts'].get('VWAP_VOLUME',0):,} / {audit['family_counts'].get('ANCHOR_MEAN',0):,} / {audit['family_counts'].get('LAGGED_VWAP_SHAPE',0):,}","",
        "## Core map","",
        "| Split | Family | Clock | Coverage | Accuracy | Separation |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for r in core_map.sort_values(["split","family","clock"]).itertuples(index=False):
        lines.append(f"| {r.split} | {r.family} | T+{int(r.clock)} | {r.coverage:.3f} | {r.accuracy:.3f} | {r.separation:.3f} |")
    lines+=["","## Paired weekly specificity tests","",
            f"- Confirmation T+3 VWAP - ANCHOR_MEAN: {paired['confirmation_t3_vs_mean']}",
            f"- Confirmation T+3 VWAP - LAGGED_VWAP_SHAPE: {paired['confirmation_t3_vs_lagged']}","",
            "## Frozen gates",""]
    for k,v in verdict["gates"].items():
        lines.append(f"- {k}: {'PASS' if v else 'FAIL'}")
    lines+=["","## Interpretation","",verdict["interpretation"],"",
            "This LAB does not test 1.5R/2R trade economics and does not authorize holdout opening or live allocation."]
    return "\n".join(lines)+"\n"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("input",type=Path)
    ap.add_argument("--outdir",type=Path,required=True)
    args=ap.parse_args()
    out=args.outdir; out.mkdir(parents=True,exist_ok=True)

    h=sha256(args.input)
    if h!=SHA: raise RuntimeError(f"canonical SHA mismatch {h}")
    df=load(args.input); raw_rows=len(df)
    df=df[df.time<HOLDOUT].copy().reset_index(drop=True)
    volume_present=bool(df.tick_volume.notna().any() and (df.tick_volume.fillna(0)>0).any())
    df=add_atr(df); df=add_level_families(df)

    touches=[]
    for family,roles in FAMILY_COLS.items():
        for role,col in roles.items():
            touches.extend(detect_touches(df,family,role,col))
    touches=sorted(touches,key=lambda z:(z[0],z[1],z[2]))

    rows=[]
    for rec in touches:
        r=event_for_touch(df,rec)
        if r is not None: rows.append(r)
    e=add_split(pd.DataFrame(rows))
    e.to_csv(out/"events.csv.gz",index=False,compression="gzip")

    core=make_map(e,["split","family"])
    core.to_csv(out/"core_map.csv",index=False)
    by_level=make_map(e,["split","family","level"])
    by_level.to_csv(out/"level_map.csv",index=False)
    by_dir=make_map(e,["split","family","arrival_side"])
    by_dir.to_csv(out/"direction_map.csv",index=False)
    yearly=make_map(e,["year","family"])
    yearly.to_csv(out/"yearly_map.csv",index=False)

    paired={}
    for split in ["DISCOVERY","CONFIRMATION"]:
        for clock in CLOCKS:
            for other,key in [("ANCHOR_MEAN","mean"),("LAGGED_VWAP_SHAPE","lagged")]:
                paired[f"{split.lower()}_t{clock}_vs_{key}"]=paired_boot(e,split,clock,other)
    (out/"paired_bootstrap.json").write_text(json.dumps(paired,indent=2,default=str))

    def core_sep(split,family,clock):
        q=core[(core.split==split)&(core.family==family)&(core.clock==clock)]
        return float(q.iloc[0].separation) if len(q)==1 else np.nan

    g1=all(np.isfinite(core_sep(s,"VWAP_VOLUME",k)) and core_sep(s,"VWAP_VOLUME",k)>0
           for s in ["DISCOVERY","CONFIRMATION"] for k in CLOCKS)
    pmean=paired["confirmation_t3_vs_mean"]; plag=paired["confirmation_t3_vs_lagged"]
    g2=bool(pmean["ci95"][0] is not None and pmean["ci95"][0]>0)
    g3=bool(plag["ci95"][0] is not None and plag["ci95"][0]>0)
    s1=core_sep("CONFIRMATION","VWAP_VOLUME",1); s5=core_sep("CONFIRMATION","VWAP_VOLUME",5)
    g4=bool(np.isfinite(s1) and np.isfinite(s5) and s5>0 and s1>=.60*s5)
    g5=True
    for arr in [1,-1]:
        q=by_dir[(by_dir.split=="CONFIRMATION")&(by_dir.family=="VWAP_VOLUME")&(by_dir.clock==3)&(by_dir.arrival_side==arr)]
        g5=g5 and len(q)==1 and np.isfinite(q.iloc[0].separation) and q.iloc[0].separation>0
    g6=True
    for lev in ["MID","HIGH","LOW"]:
        q=by_level[(by_level.split=="CONFIRMATION")&(by_level.family=="VWAP_VOLUME")&(by_level.clock==3)&(by_level.level==lev)]
        g6=g6 and len(q)==1 and np.isfinite(q.iloc[0].separation) and q.iloc[0].separation>0

    gates={
        "G0_DATA_CLOCK":bool(h==SHA and volume_present),
        "G1_VWAP_MAP_TRANSFER":bool(g1),
        "G2_VWAP_OVER_MEAN_T3":g2,
        "G3_VWAP_OVER_LAGGED_T3":g3,
        "G4_T1_RETAINS_SIGNAL":g4,
        "G5_DIRECTION_MIRROR":bool(g5),
        "G6_LEVEL_BREADTH":bool(g6),
    }
    if not gates["G0_DATA_CLOCK"]:
        status="INVALID_DATA_CLOCK"
        interp="Canonical data/volume gate failed."
    elif not (gates["G1_VWAP_MAP_TRANSFER"] and gates["G5_DIRECTION_MIRROR"] and gates["G6_LEVEL_BREADTH"]):
        status="SEQUENCE_NOT_STABLE"
        interp="The VWAP sequence itself did not remain directionally stable across required internal partitions/breadth checks."
    elif all(gates.values()):
        status="VWAP_SPECIFIC_SEQUENCE_EDGE"
        interp="The post-touch sequence transfers and current-session tick-volume VWAP outperforms both frozen placebos at the primary T+3 clock."
    else:
        status="GENERIC_SEQUENCE_NOT_VWAP_SPECIFIC"
        interp="The post-touch sequence is strongly transferable, but current-session tick-volume VWAP does not beat both frozen placebos with positive paired-cluster confidence; treat most of the effect as generic short-horizon path persistence rather than VWAP-specific information."

    verdict={
        "status":status,"gates":gates,
        "confirmation_vwap_sep":{"T1":s1,"T3":core_sep("CONFIRMATION","VWAP_VOLUME",3),"T5":s5},
        "confirmation_t3_vs_mean":pmean,
        "confirmation_t3_vs_lagged":plag,
        "holdout_opened":False,
        "interpretation":interp,
    }
    (out/"verdict.json").write_text(json.dumps(verdict,indent=2,default=str))
    audit={
        "lab":LAB,"version":VERSION,"sha256":h,"raw_rows":int(raw_rows),
        "rows_pre_holdout":int(len(df)),
        "period_start":str(df.time.min()),"period_end":str(df.time.max()),
        "holdout_opened":False,"touch_candidates":int(len(touches)),
        "mapped_events":int(len(e)),"volume_proxy_present":volume_present,
        "family_counts":{k:int(v) for k,v in e.family.value_counts().to_dict().items()},
        "split_counts":{k:int(v) for k,v in e.split.value_counts().to_dict().items()},
        "anchor_platform_hour":ANCHOR_HOUR,"band_k":BAND_K,
        "touch_atr":TOUCH_ATR,"rearm_atr":REARM_ATR,"decision_threshold":DECISION_THRESHOLD,
        "decision_clocks":list(CLOCKS),"future_barrier_atr":PRIMARY_BARRIER,
        "future_label_starts_after_minute":FEATURE_MIN,"future_horizon_minutes_from_touch":OUTCOME_MIN,
    }
    (out/"audit.json").write_text(json.dumps(audit,indent=2,default=str))
    report=build_report(audit,verdict,core,paired)
    (out/"REPORT.md").write_text(report)
    print(json.dumps(audit,indent=2))
    print(json.dumps(verdict,indent=2))

if __name__=="__main__":
    main()
