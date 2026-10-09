from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path(__file__).resolve().parents[2]
def loadmod(name,path):
    sp=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
L155=loadmod("lab155",ROOT/"labs/LAB155_ADDON_RISK_TRANSFER_20261009/run_lab155.py")
OUT=Path("lab156_out");OUT.mkdir(exist_ok=True)
BT=L155.BT;BO=L155.BO;BH=L155.BH;BL=L155.BL;BC=L155.BC
COSTS=[2.81,7.5];BASE_RISK=0.25;MODE="LOCK2_LOCK025";SCALERS=["FLAT","LOWVOL_HALF"]
m5=pd.DataFrame({"time":pd.to_datetime(BT,utc=True),"o":BO,"h":BH,"l":BL,"c":BC});m5["day"]=m5.time.dt.floor("D")
d=m5.groupby("day").agg(o=("o","first"),h=("h","max"),l=("l","min"),c=("c","last")).reset_index()
prev=d.c.shift(1);tr=np.maximum(d.h-d.l,np.maximum((d.h-prev).abs(),(d.l-prev).abs()))
d["atr14"]=tr.rolling(14,min_periods=14).mean();d["q30_prev365"]=d["atr14"].rolling(365,min_periods=250).quantile(.30)
d["lowvol_for_next_day"]=(d["atr14"]<d["q30_prev365"])&d["q30_prev365"].notna()
nextmap={pd.Timestamp(r.day)+pd.Timedelta(days=1):bool(r.lowvol_for_next_day) for _,r in d.iterrows()}
def is_lowvol(ts): return bool(nextmap.get(pd.Timestamp(ts).tz_convert("UTC").floor("D"),False))
def replay_weighted(cost,scaler):
    raw=L155.raw_signals(cost);by_i={}
    for _,r in raw.iterrows():by_i.setdefault(int(r.entry_i),[]).append(r)
    active=[];closed=[];skipped=0;addons=0;realized_pct=0.;rows=[]
    start=int(raw.entry_i.min());end=min(int(raw.entry_i.max())+L155.MAX_H_BARS,len(BT)-1)
    for i in range(start,end+1):
        for r in sorted(by_i.get(i,[]),key=lambda x:int(x.pri)):
            allow=False;is_add=False
            if len(active)==0:allow=True
            elif len(active)==1:
                allow=int(active[0]["side"])==int(r.side) and L155.total_mtm_at_open(active[0],i)>=0;is_add=allow
            if allow:
                if is_add:addons+=1;L155.transfer_first_stop(active[0],MODE)
                p=L155.init_pos(r,cost,"LOCK2");p["addon_parent"]=is_add;p["risk_mult"]=0.5 if scaler=="LOWVOL_HALF" and is_lowvol(p["entry_time"]) else 1.0;active.append(p)
            else:skipped+=1
        still=[]
        for p in active:
            done=L155.evaluate_bar(p,i)
            if done is None:still.append(p)
            else:
                done["risk_mult"]=p["risk_mult"];done["lowvol"]=p["risk_mult"]<1;done["weighted_pct"]=done["net_r"]*BASE_RISK*p["risk_mult"]
                closed.append(done);realized_pct+=done["weighted_pct"]
        active=still
        floating=sum(L155.total_mtm_at_close(p,i)*BASE_RISK*p["risk_mult"] for p in active)
        rows.append(dict(time=BT.iloc[i],equity_pct=realized_pct+floating,floating_pct=floating))
        if i>int(raw.entry_i.max()) and not active:break
    return pd.DataFrame(closed),pd.DataFrame(rows),skipped,addons
def stats(t,eq):
    a=pd.Timestamp(t.entry_time.min());b=pd.Timestamp(t.exit_time.max());months=max((b.year-a.year)*12+b.month-a.month+1,1)
    e=eq.copy();e["peak"]=e.equity_pct.cummax();e["dd"]=e.peak-e.equity_pct;e["day"]=pd.to_datetime(e.time,utc=True).dt.floor("D")
    prev=0.;maxday=0.
    for _,g in e.groupby("day"):
        maxday=max(maxday,max(0.,prev-float(g.equity_pct.min())));prev=float(g.equity_pct.iloc[-1])
    return dict(n=len(t),trades_month=len(t)/months,total_pct=float(t.weighted_pct.sum()),pct_month=float(t.weighted_pct.sum()/months),
                mtm_dd_pct=float(e.dd.max()),daily_start_loss_pct=maxday,worst_floating_pct=float(e.floating_pct.min()),
                lowvol_trades=int(t.lowvol.sum()),lowvol_share=float(t.lowvol.mean()))
summary=[];yrs=[];alltr=[]
for cost in COSTS:
    for sc in SCALERS:
        t,eq,sk,adds=replay_weighted(cost,sc);s=stats(t,eq);s.update(cost_bps=cost,scaler=sc,skipped=sk,addons=adds);summary.append(s)
        tt=t.copy();tt["cost_bps"]=cost;tt["scaler"]=sc;alltr.append(tt);tt["year"]=pd.to_datetime(tt.entry_time,utc=True).dt.year
        for y,g in tt.groupby("year"):yrs.append(dict(cost_bps=cost,scaler=sc,year=int(y),n=len(g),lowvol_n=int(g.lowvol.sum()),total_pct=float(g.weighted_pct.sum())))
S=pd.DataFrame(summary);Y=pd.DataFrame(yrs);S.to_csv(OUT/"LAB156_summary.csv",index=False);Y.to_csv(OUT/"LAB156_year_attribution.csv",index=False)
pd.concat(alltr,ignore_index=True).to_csv(OUT/"LAB156_trades.csv",index=False);d.to_csv(OUT/"LAB156_daily_vol_regime.csv",index=False)
base=S[(S.cost_bps==7.5)&(S.scaler=="LOWVOL_HALF")].iloc[0];scens=[]
for rp in [0.25,0.30,0.35,0.40]:
    k=rp/BASE_RISK;scens.append(dict(base_risk_pct=rp,pct_month=base.pct_month*k,dollars_month_100k=base.pct_month*k*1000,mtm_dd_pct=base.mtm_dd_pct*k,daily_start_loss_pct=base.daily_start_loss_pct*k))
PD=pd.DataFrame(scens);PD.to_csv(OUT/"LAB156_risk_scale_scenarios.csv",index=False)
lines=["# LAB156 — LOW-VOL RISK SCALER","","Frozen portfolio mode: LOCK2_LOCK025 + HALF_TP3_LOCK2.","Low-vol = previous completed D1 ATR14 below trailing 365-day 30th percentile (min 250 observations). Risk is halved; signals are not filtered.",""]
for cost in COSTS:
    lines.append(f"## {cost:.2f}bps")
    for _,r in S[S.cost_bps==cost].iterrows():lines.append(f"- {r.scaler}: N={int(r.n)} ({r.trades_month:.2f}/mo), return={r.pct_month:+.3f}%/mo, MTM DD={r.mtm_dd_pct:.2f}%, daily={r.daily_start_loss_pct:.2f}%, low-vol trades={int(r.lowvol_trades)} ({r.lowvol_share:.1%})")
lines+=["","## Year attribution @7.5bps"]
for _,r in Y[Y.cost_bps==7.5].iterrows():lines.append(f"- {r.scaler} {int(r.year)}: N={int(r.n)}, low-vol={int(r.lowvol_n)}, total={r.total_pct:+.2f}%")
lines+=["","## LOWVOL_HALF scaling @7.5bps"]
for _,r in PD.iterrows():lines.append(f"- base risk {r.base_risk_pct:.2f}%: {r.pct_month:.3f}%/mo, approx USD {r.dollars_month_100k:.0f}/mo on 100k, MTM DD={r.mtm_dd_pct:.2f}%, daily={r.daily_start_loss_pct:.2f}%")
lines+=["","TRAIN/development only. UTC day boundary remains a proxy; exact FTMO CET/CEST replay is separate."]
(OUT/"LAB156_REPORT.md").write_text("\n".join(lines)+"\n");(OUT/"LAB156_meta.json").write_text(json.dumps(dict(mode=MODE,base_risk_pct=BASE_RISK,lowvol_rule="prev D1 ATR14 < trailing365 q30; x0.5",caveat="TRAIN/UTC proxy"),indent=2))
print("\n".join(lines))
