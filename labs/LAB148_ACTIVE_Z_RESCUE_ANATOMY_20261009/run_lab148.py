from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/"labs/LAB124_ANTI_CROWD_QUALITY_SCORE_20261008/run_lab124.py"
spec=importlib.util.spec_from_file_location("lab124",SRC)
A=importlib.util.module_from_spec(spec);spec.loader.exec_module(A)

OUT=Path("lab148_out");OUT.mkdir(exist_ok=True)
BT=A.BT;BO=A.BO;BH=A.BH;BL=A.BL;BC=A.BC;BA=A.BA;BZ=A.BZ
b=A.b.reset_index(drop=True)
TRAIN_END=A.TRAIN_END
EXT=A.EXT80
OI=A.OI70
MAX_H=48
SEARCH6=72
COSTS=[2.81,7.5]

def phase_name(age,imp):
    return A.phase(int(age),int(imp))

def swing3(i,side,maxbars=SEARCH6):
    end=min(i+maxbars,len(b)-2)
    for j in range(i+1,end+1):
        lo=max(i,j-3)
        if side>0:
            ref=float(np.max(BH[lo:j]))
            if BC[j]>ref:
                strength=(BC[j]-ref)/float(BA[i])
                return j+1,j,ref,strength
        else:
            ref=float(np.min(BL[lo:j]))
            if BC[j]<ref:
                strength=(ref-BC[j])/float(BA[i])
                return j+1,j,ref,strength
    return None,None,np.nan,np.nan

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

# Rebuild ACTIVE_Z_RESCUE exactly in spirit of LAB147, with richer causal features.
rows=[]
i=1
while i<len(b)-MAX_H*12-2 and BT.iloc[i]<TRAIN_END:
    if abs(BZ[i])>=1 and abs(BZ[i-1])<1:
        sign=1 if BZ[i]>0 else -1
        side=-sign
        start=i
        start_z=float(BZ[start])
        start_oi=float(b.oi4h.iloc[start])
        start_px=float(BC[start])
        j=i+1
        while j<len(b)-MAX_H*12-2 and BT.iloc[j]<TRAIN_END and abs(BZ[j])>=1 and (1 if BZ[j]>0 else -1)==sign and (j-start)<=144:
            trend=int(b.trend.iloc[j])
            if trend!=0 and trend!=side:
                ph=phase_name(b.trend_age.iloc[j],b.impulse_age.iloc[j])
                ext=float(b.extension.iloc[j]);oi=float(b.oi4h.iloc[j])
                phase_ok=ph in ("CONT","REACCEL")
                ext_ok=((side>0 and ext<0) or (side<0 and ext>0)) and abs(ext)>=EXT
                oi_ok=oi>=OI
                if phase_ok and ext_ok and oi_ok:
                    ei,ti,ref,br=swing3(j,side,SEARCH6)
                    if ei is not None:
                        seg=slice(start,j+1)
                        absz=np.abs(BZ[seg])
                        z_peak=float(np.nanmax(absz))
                        z_now=abs(float(BZ[j]))
                        z_change=float(z_now-abs(start_z))
                        oi_change_from_start=float(oi-start_oi)
                        price_disp=float(side*(BC[j]-start_px)/float(BA[j]))
                        age_min=float((BT.iloc[j]-BT.iloc[start]).total_seconds()/60)
                        trigger_delay=float((BT.iloc[ei]-BT.iloc[j]).total_seconds()/60)
                        ext_abs=abs(ext)
                        rows.append(dict(
                            episode_start=BT.iloc[start],anchor_time=BT.iloc[j],entry_time=BT.iloc[ei],
                            start_i=start,anchor_i=j,trigger_i=ti,entry_i=ei,side=side,phase=ph,
                            atr=float(BA[j]),episode_age_min=age_min,trigger_delay_min=trigger_delay,
                            z_start=abs(start_z),z_now=z_now,z_peak=z_peak,z_change=z_change,
                            oi4h=oi,oi_change_from_start=oi_change_from_start,ext_abs=ext_abs,
                            break_strength=float(br),price_disp_from_start=price_disp))
                        break
            j+=1
        i=max(i+1,j)
    else:
        i+=1

df=pd.DataFrame(rows)
if df.empty: raise RuntimeError("No ACTIVE_Z_RESCUE events")
df.to_csv(OUT/"LAB148_rescue_events.csv",index=False)

# Non-return TRAIN-distribution thresholds only.
thr={
    "age_q40":float(df.episode_age_min.quantile(.40)),
    "age_q60":float(df.episode_age_min.quantile(.60)),
    "znow_q60":float(df.z_now.quantile(.60)),
    "zpeak_q60":float(df.z_peak.quantile(.60)),
    "zchange_q60":float(df.z_change.quantile(.60)),
    "oi_q60":float(df.oi4h.quantile(.60)),
    "oi_accel_q60":float(df.oi_change_from_start.quantile(.60)),
    "ext_q60":float(df.ext_abs.quantile(.60)),
    "break_q60":float(df.break_strength.quantile(.60)),
    "delay_q40":float(df.trigger_delay_min.quantile(.40)),
}
(OUT/"LAB148_thresholds.json").write_text(json.dumps(thr,indent=2))

# Predeclared anatomy gates. No return-derived thresholds.
GATES={
    "ALL":lambda d:pd.Series(True,index=d.index),
    "EARLY_EPISODE":lambda d:d.episode_age_min<=thr["age_q40"],
    "MID_EPISODE":lambda d:(d.episode_age_min>thr["age_q40"])&(d.episode_age_min<=thr["age_q60"]),
    "STRONG_Z_NOW":lambda d:d.z_now>=thr["znow_q60"],
    "STRONG_Z_PEAK":lambda d:d.z_peak>=thr["zpeak_q60"],
    "Z_STILL_BUILDING":lambda d:d.z_change>=thr["zchange_q60"],
    "STRONG_OI":lambda d:d.oi4h>=thr["oi_q60"],
    "OI_ACCEL":lambda d:d.oi_change_from_start>=thr["oi_accel_q60"],
    "STRONG_EXT":lambda d:d.ext_abs>=thr["ext_q60"],
    "STRONG_BREAK":lambda d:d.break_strength>=thr["break_q60"],
    "FAST_TRIGGER":lambda d:d.trigger_delay_min<=thr["delay_q40"],
    "REACCEL":lambda d:d.phase=="REACCEL",
    "CONT":lambda d:d.phase=="CONT",
    "EARLY_STRONG_BREAK":lambda d:(d.episode_age_min<=thr["age_q40"])&(d.break_strength>=thr["break_q60"]),
    "EARLY_STRONG_Z":lambda d:(d.episode_age_min<=thr["age_q40"])&(d.z_now>=thr["znow_q60"]),
    "STRONG_Z_OI":lambda d:(d.z_now>=thr["znow_q60"])&(d.oi4h>=thr["oi_q60"]),
    "STRONG_EXT_BREAK":lambda d:(d.ext_abs>=thr["ext_q60"])&(d.break_strength>=thr["break_q60"]),
    "REACCEL_STRONG_BREAK":lambda d:(d.phase=="REACCEL")&(d.break_strength>=thr["break_q60"]),
    "CONT_STRONG_BREAK":lambda d:(d.phase=="CONT")&(d.break_strength>=thr["break_q60"]),
    "EARLY_Z_OI":lambda d:(d.episode_age_min<=thr["age_q40"])&(d.z_now>=thr["znow_q60"])&(d.oi4h>=thr["oi_q60"]),
}

summary=[];alltr=[]
for cost in COSTS:
    for gate,fn in GATES.items():
        g=df[fn(df)].sort_values("entry_time")
        open_until=pd.Timestamp.min.tz_localize("UTC");trs=[]
        for _,r in g.iterrows():
            if r.entry_time<open_until:continue
            net,reason,xi=sim(int(r.entry_i),int(r.side),float(r.atr),cost)
            open_until=BT.iloc[xi]
            trs.append(dict(gate=gate,cost_bps=cost,entry_time=r.entry_time,exit_time=BT.iloc[xi],
                            side="BUY" if int(r.side)>0 else "SELL",net_r=net,reason=reason,
                            episode_age_min=r.episode_age_min,z_now=r.z_now,z_peak=r.z_peak,z_change=r.z_change,
                            oi4h=r.oi4h,oi_change_from_start=r.oi_change_from_start,ext_abs=r.ext_abs,
                            break_strength=r.break_strength,phase=r.phase))
        t=pd.DataFrame(trs)
        if t.empty:continue
        alltr.append(t)
        x=t.net_r.to_numpy(float);pos=x[x>0].sum();neg=-x[x<0].sum()
        ce=np.cumsum(x);dd=float(np.max(np.maximum.accumulate(ce)-ce))
        a=pd.Timestamp(t.entry_time.min());bb=pd.Timestamp(t.exit_time.max());months=max((bb.year-a.year)*12+bb.month-a.month+1,1)
        summary.append(dict(gate=gate,cost_bps=cost,n=len(t),trades_month=len(t)/months,
                            ev=float(x.mean()),pf=float(pos/neg) if neg>0 else np.inf,
                            wr=float((x>0).mean()),r_month=float(x.sum()/months),dd_r=dd,
                            buy_n=int((t.side=="BUY").sum()),sell_n=int((t.side=="SELL").sum())))

S=pd.DataFrame(summary)
S.to_csv(OUT/"LAB148_summary.csv",index=False)
pd.concat(alltr,ignore_index=True).to_csv(OUT/"LAB148_trades.csv",index=False)

# Rank promotable anatomy candidates on stress: target 1-2.5 trades/mo, PF>=1.45, positive R/mo.
rank=S[(S.cost_bps==7.5)&(S.trades_month>=1.0)&(S.trades_month<=2.5)&(S.pf>=1.45)&(S.r_month>0)].copy()
rank=rank.sort_values(["r_month","pf"],ascending=False)
rank.to_csv(OUT/"LAB148_rank.csv",index=False)
winner=str(rank.iloc[0].gate) if len(rank) else "NONE"

lines=["# LAB148 — ACTIVE Z RESCUE ANATOMY","",
       f"Universe: {len(df)} ACTIVE_Z_RESCUE events from LAB147 logic.",
       "All thresholds below are TRAIN-distribution quantiles of causal features, not return-fitted thresholds.",
       f"- episode age q40/q60 = {thr['age_q40']:.0f}m / {thr['age_q60']:.0f}m",
       f"- |Z| now q60 = {thr['znow_q60']:.3f}",
       f"- |Z| peak q60 = {thr['zpeak_q60']:.3f}",
       f"- Z change q60 = {thr['zchange_q60']:+.3f}",
       f"- OI4h q60 = {thr['oi_q60']:+.3%}",
       f"- OI accel from episode start q60 = {thr['oi_accel_q60']:+.3%}",
       f"- extension q60 = {thr['ext_q60']:.3f} H1ATR",
       f"- SWING3 break strength q60 = {thr['break_q60']:.3f} H1ATR",
       f"- trigger delay q40 = {thr['delay_q40']:.0f}m",
       "",
       "## Results"]
for cost in COSTS:
    lines.append(f"### {cost:.2f}bps")
    for _,r in S[S.cost_bps==cost].sort_values(["pf","r_month"],ascending=False).iterrows():
        lines.append(f"- {r.gate}: N={int(r.n)} ({r.trades_month:.2f}/mo), EV={r.ev:+.3f}R, PF={r.pf:.2f}, WR={r.wr:.1%}, R/mo={r.r_month:+.2f}, DD={r.dd_r:.1f}R, BUY/SELL={int(r.buy_n)}/{int(r.sell_n)}")
lines += ["","## Promotion screen",
          "Target: about 1–2.5 extra trades/month, stress PF>=1.45, positive R/month.",
          f"Best candidate by frozen screen: **{winner}**.",
          "This LAB is still BTC TRAIN discovery. Any selected rescue gate must be tested as an incremental portfolio add-on and then forward-validated."]
(OUT/"LAB148_REPORT.md").write_text("\n".join(lines)+"\n")
(OUT/"LAB148_meta.json").write_text(json.dumps(dict(
    universe="LAB147 ACTIVE_Z_RESCUE",
    thresholds=thr,
    gates=list(GATES.keys()),
    winner=winner,
    promotion_screen="7.5bps; 1.0-2.5 trades/mo; PF>=1.45; R/mo>0",
    caveat="BTC TRAIN discovery only"
),indent=2))
print("\n".join(lines))
