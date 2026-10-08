from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/"labs/LAB124_ANTI_CROWD_QUALITY_SCORE_20261008/run_lab124.py"
spec=importlib.util.spec_from_file_location("lab124",SRC)
A=importlib.util.module_from_spec(spec);spec.loader.exec_module(A)

OUT=Path("lab147_out");OUT.mkdir(exist_ok=True)
BT=A.BT;BO=A.BO;BH=A.BH;BL=A.BL;BC=A.BC;BA=A.BA;BZ=A.BZ
b=A.b.reset_index(drop=True)
TRAIN_END=A.TRAIN_END
EXT=A.EXT80
OI=A.OI70
MAX_H=48
SEARCH6=72
SEARCH12=144
COSTS=[2.81,7.5]

def ph(age,imp):
    return A.phase(int(age),int(imp))

def swing3(i,side,maxbars):
    end=min(i+maxbars,len(b)-2)
    for j in range(i+1,end+1):
        lo=max(i,j-3)
        if side>0:
            ref=float(np.max(BH[lo:j]))
            if BC[j]>ref:return j+1,j
        else:
            ref=float(np.min(BL[lo:j]))
            if BC[j]<ref:return j+1,j
    return None,None

def sim(ei,side,atr,cost):
    entry=float(BO[ei]);sl=entry-side*atr;tp=entry+side*3*atr;end=min(ei+MAX_H*12-1,len(b)-1)
    gross=side*(BC[end]-entry)/atr;reason="TIME";xi=end
    for j in range(ei,end+1):
        hs=(BL[j]<=sl) if side>0 else (BH[j]>=sl)
        ht=(BH[j]>=tp) if side>0 else (BL[j]<=tp)
        if hs and ht:gross=-1;reason="BOTH_STOP_FIRST";xi=j;break
        if hs:gross=-1;reason="SL";xi=j;break
        if ht:gross=3;reason="TP";xi=j;break
    return float(gross-(cost/10000.0)*entry/atr),reason,xi

def classify_fresh_events():
    rows=[]
    last=len(b)-1-MAX_H*12-1
    for i in range(1,last):
        if BT.iloc[i]>=TRAIN_END:break
        if not(abs(BZ[i])>=1 and abs(BZ[i-1])<1):continue
        side=-1 if BZ[i]>0 else 1
        trend=int(b.trend.iloc[i])
        if trend==0 or trend==side:continue
        phase=ph(b.trend_age.iloc[i],b.impulse_age.iloc[i])
        phase_ok=phase in ("CONT","REACCEL")
        ext=float(b.extension.iloc[i]);ext_ok=((side>0 and ext<0) or (side<0 and ext>0)) and abs(ext)>=EXT
        oi=float(b.oi4h.iloc[i]);oi_ok=oi>=OI
        ei6,ti6=swing3(i,side,SEARCH6)
        ei12,ti12=swing3(i,side,SEARCH12)
        swing6=ei6 is not None
        swing12=ei12 is not None
        gates=dict(phase_ok=phase_ok,ext_ok=ext_ok,oi_ok=oi_ok,swing6=swing6)
        failed=[k for k,v in gates.items() if not v]
        if len(failed)==0:bucket="CANONICAL"
        elif len(failed)==1:bucket="FAIL_ONLY_"+failed[0].upper()
        else:bucket="FAIL_MULTI"
        # Special late swing rescue: all context gates pass, swing appears only in 6-12h.
        late_swing=(phase_ok and ext_ok and oi_ok and (not swing6) and swing12)
        rows.append(dict(anchor_i=i,signal_time=BT.iloc[i],side=side,phase=phase,phase_ok=phase_ok,
                         extension=ext,ext_ok=ext_ok,oi4h=oi,oi_ok=oi_ok,swing6=swing6,swing12=swing12,
                         bucket=bucket,late_swing_6_12=late_swing,entry_i_6=ei6,entry_i_12=ei12,
                         atr=float(BA[i]),z=float(BZ[i])))
    return pd.DataFrame(rows)

fresh=classify_fresh_events()

# Active-Z rescue: inside each |Z|>=1 same-sign episode, after the fresh bar,
# find first later bar where phase/ext/OI pass while Z remains extreme in same sign.
resc=[]
i=1
while i<len(b)-MAX_H*12-2 and BT.iloc[i]<TRAIN_END:
    if abs(BZ[i])>=1 and abs(BZ[i-1])<1:
        sign=1 if BZ[i]>0 else -1;side=-sign;start=i
        j=i+1
        while j<len(b)-MAX_H*12-2 and BT.iloc[j]<TRAIN_END and abs(BZ[j])>=1 and (1 if BZ[j]>0 else -1)==sign and (j-start)<=144:
            trend=int(b.trend.iloc[j])
            if trend!=0 and trend!=side:
                phase=ph(b.trend_age.iloc[j],b.impulse_age.iloc[j])
                ext=float(b.extension.iloc[j]);oi=float(b.oi4h.iloc[j])
                phase_ok=phase in ("CONT","REACCEL")
                ext_ok=((side>0 and ext<0) or (side<0 and ext>0)) and abs(ext)>=EXT
                oi_ok=oi>=OI
                if phase_ok and ext_ok and oi_ok:
                    ei,ti=swing3(j,side,SEARCH6)
                    if ei is not None:
                        resc.append(dict(anchor_i=j,signal_time=BT.iloc[j],side=side,phase=phase,
                                         extension=ext,oi4h=oi,atr=float(BA[j]),z=float(BZ[j]),
                                         episode_start=BT.iloc[start],episode_age_min=(BT.iloc[j]-BT.iloc[start]).total_seconds()/60,
                                         entry_i=ei,trigger_i=ti))
                        break
            j+=1
        i=max(i+1,j)
    else:
        i+=1
active_rescue=pd.DataFrame(resc)

# Remove rescues that occur at fresh episode start (should be later by construction)
if len(active_rescue):
    active_rescue=active_rescue[active_rescue.episode_age_min>0].copy()

# Prepare outcome cohorts.
cohorts=[]
for bucket,g in fresh.groupby("bucket"):
    # For context failures, still use first SWING3 within 6h if it exists.
    gg=g[g.entry_i_6.notna()].copy()
    if len(gg):cohorts.append((bucket,gg,"entry_i_6"))
late=fresh[fresh.late_swing_6_12].copy()
if len(late):cohorts.append(("LATE_SWING_6_12",late,"entry_i_12"))
if len(active_rescue):
    cohorts.append(("ACTIVE_Z_RESCUE",active_rescue,"entry_i"))

summary=[];trades=[]
for cost in COSTS:
    for name,g,ecol in cohorts:
        open_until=pd.Timestamp.min.tz_localize("UTC");rows=[]
        for _,r in g.sort_values("signal_time").iterrows():
            ei=int(r[ecol]);entry_time=BT.iloc[ei]
            if entry_time<open_until:continue
            net,reason,xi=sim(ei,int(r.side),float(r.atr),cost);open_until=BT.iloc[xi]
            q=dict(cohort=name,cost_bps=cost,signal_time=r.signal_time,entry_time=entry_time,exit_time=BT.iloc[xi],
                   side="BUY" if int(r.side)>0 else "SELL",net_r=net,reason=reason,
                   z=float(r.z),extension=float(r.extension),oi4h=float(r.oi4h),phase=str(r.phase))
            if "episode_age_min" in r.index:q["episode_age_min"]=float(r.episode_age_min)
            rows.append(q)
        t=pd.DataFrame(rows)
        if t.empty:continue
        trades.append(t)
        x=t.net_r.to_numpy(float);pos=x[x>0].sum();neg=-x[x<0].sum()
        ce=np.cumsum(x);dd=float(np.max(np.maximum.accumulate(ce)-ce))
        a=pd.Timestamp(t.entry_time.min());bb=pd.Timestamp(t.exit_time.max());months=max((bb.year-a.year)*12+bb.month-a.month+1,1)
        summary.append(dict(cohort=name,cost_bps=cost,n=len(t),trades_month=len(t)/months,ev=float(x.mean()),
                            pf=float(pos/neg) if neg>0 else np.inf,wr=float((x>0).mean()),r_month=float(x.sum()/months),
                            dd_r=dd,buy_n=int((t.side=="BUY").sum()),sell_n=int((t.side=="SELL").sum())))

S=pd.DataFrame(summary);S.to_csv(OUT/"LAB147_funnel_outcomes.csv",index=False)
fresh.to_csv(OUT/"LAB147_fresh_event_funnel.csv",index=False)
active_rescue.to_csv(OUT/"LAB147_active_z_rescue.csv",index=False)
if trades:pd.concat(trades,ignore_index=True).to_csv(OUT/"LAB147_trades.csv",index=False)

# Funnel counts and single-gate near misses.
counts=fresh.bucket.value_counts().rename_axis("bucket").reset_index(name="n")
counts.to_csv(OUT/"LAB147_funnel_counts.csv",index=False)

# BUY-only OI negative diagnostics among events passing phase/ext and with swing6.
buy_oi=fresh[(fresh.side>0)&fresh.phase_ok&fresh.ext_ok&fresh.swing6].copy()
buy_oi["oi_group"]=np.where(buy_oi.oi4h>=OI,"PASS_CANON_OI",
                     np.where(buy_oi.oi4h<0,"OI_NEGATIVE","OI_POS_BELOW_GATE"))
buyrows=[]
for grp,g in buy_oi.groupby("oi_group"):
    for cost in COSTS:
        rows=[]
        for _,r in g.sort_values("signal_time").iterrows():
            net,reason,xi=sim(int(r.entry_i_6),int(r.side),float(r.atr),cost)
            rows.append(net)
        x=np.asarray(rows,float)
        if len(x):
            pos=x[x>0].sum();neg=-x[x<0].sum()
            buyrows.append(dict(group=grp,cost_bps=cost,n=len(x),ev=float(x.mean()),pf=float(pos/neg) if neg>0 else np.inf,wr=float((x>0).mean())))
pd.DataFrame(buyrows).to_csv(OUT/"LAB147_buy_oi_diagnostic.csv",index=False)

lines=["# LAB147 — ENGINE A MISSED TRADE FUNNEL","",
       "Purpose: identify where Engine A loses potentially profitable anti-crowd reversals before entry.",
       f"Canonical gates: phase CONT/REACCEL; extension >= {EXT:.3f} H1ATR against old trend; OI4h >= {OI:+.3%}; first SWING3 within 6h.",
       "Primary funnel starts from every TRAIN fresh |Z|>=1 event whose inverse-crowd side is opposite an established H4 trend.",
       "Each event is labeled by the single failed gate, multiple failures, or canonical pass.",
       "Forward outcome uses the same SL1 H1ATR / TP3R / 48h execution.",
       "",
       "## Funnel counts"]
for _,r in counts.iterrows():lines.append(f"- {r.bucket}: {int(r.n)}")
lines += ["","## Forward outcomes"]
for cost in COSTS:
    lines.append(f"### {cost:.2f}bps")
    for _,r in S[S.cost_bps==cost].sort_values("r_month",ascending=False).iterrows():
        lines.append(f"- {r.cohort}: N={int(r.n)} ({r.trades_month:.2f}/mo), EV={r.ev:+.3f}R, PF={r.pf:.2f}, WR={r.wr:.1%}, R/mo={r.r_month:+.2f}, DD={r.dd_r:.1f}R, BUY/SELL={int(r.buy_n)}/{int(r.sell_n)}")
lines += ["","## BUY OI diagnostic"]
bd=pd.DataFrame(buyrows)
for cost in COSTS:
    lines.append(f"### {cost:.2f}bps")
    for _,r in bd[bd.cost_bps==cost].iterrows():
        lines.append(f"- {r.group}: N={int(r.n)}, EV={r.ev:+.3f}R, PF={r.pf:.2f}, WR={r.wr:.1%}")
lines += ["","## Interpretation rule",
          "A failed-only gate is interesting only if its forward cohort is positive after 7.5bps and does not merely add a large low-PF population.",
          "ACTIVE_Z_RESCUE specifically measures opportunities that become fully valid later inside the same Z-extreme episode, i.e. losses caused by requiring the context to be valid exactly at the fresh crossing.",
          "LATE_SWING_6_12 measures opportunities lost only because the canonical SWING3 search window ends at 6h.",
          "TRAIN discovery only; no gate is promoted here."]
(OUT/"LAB147_REPORT.md").write_text("\n".join(lines)+"\n")
(OUT/"LAB147_meta.json").write_text(json.dumps(dict(ext_gate=EXT,oi_gate=OI,
    canonical="fresh |Z|>=1 + opposite H4 trend + CONT/REACCEL + extension + OI + SWING3<=6h",
    active_z_rescue="same Z episode, later all non-fresh gates pass + SWING3<=6h",
    caveat="BTC TRAIN discovery only"),indent=2))
print("\n".join(lines))
