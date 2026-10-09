from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parents[2]
def loadmod(name,path):
    sp=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m

L155=loadmod("lab155",ROOT/"labs/LAB155_ADDON_RISK_TRANSFER_20261009/run_lab155.py")
OUT=Path("lab157_out");OUT.mkdir(exist_ok=True)

COSTS=[2.81,7.5]
MODES=["TP3_NO_TRANSFER","LOCK2_NO_TRANSFER","LOCK2_LOCK025"]
RISK=0.25

def perf(t):
    x=t.net_r.to_numpy(float)
    pos=x[x>0].sum();neg=-x[x<0].sum()
    ce=np.cumsum(x)
    dd=float(np.max(np.maximum.accumulate(ce)-ce)) if len(x) else np.nan
    # consecutive losses
    max_ls=0;cur=0
    for v in x:
        if v<0: cur+=1;max_ls=max(max_ls,cur)
        else: cur=0
    return dict(n=len(t),ev=float(x.mean()) if len(x) else np.nan,
                pf=float(pos/neg) if neg>0 else np.inf,
                wr=float((x>0).mean()) if len(x) else np.nan,
                total_r=float(x.sum()),booked_dd_r=dd,max_consec_losses=max_ls)

summary=[];year=[];month=[];engine=[];addon=[];rolling=[];trades_all=[];eq_all=[]

for cost in COSTS:
    for mode in MODES:
        t,eq,sk,adds=L155.replay(cost,mode)
        s=L155.stats(t,eq)
        s.update(cost_bps=cost,mode=mode,skipped=sk,addons=adds)
        summary.append(s)
        tt=t.copy()
        tt["cost_bps"]=cost;tt["mode"]=mode
        tt["year"]=pd.to_datetime(tt.entry_time,utc=True).dt.year
        tt["month"]=pd.to_datetime(tt.entry_time,utc=True).dt.to_period("M").astype(str)
        trades_all.append(tt)
        ee=eq.copy();ee["cost_bps"]=cost;ee["mode"]=mode;eq_all.append(ee)

        for y,g in tt.groupby("year"):
            q=perf(g)
            year.append(dict(cost_bps=cost,mode=mode,year=int(y),**q))

        for m,g in tt.groupby("month"):
            q=perf(g)
            month.append(dict(cost_bps=cost,mode=mode,month=m,**q))

        for src,g in tt.groupby("source"):
            q=perf(g)
            engine.append(dict(cost_bps=cost,mode=mode,source=src,**q))

        # add-on vs primary attribution
        for lab,mask in [("PRIMARY",~tt.addon_parent.astype(bool)),("ADDON",tt.addon_parent.astype(bool))]:
            g=tt[mask]
            if len(g):
                q=perf(g)
                addon.append(dict(cost_bps=cost,mode=mode,role=lab,**q))

        # rolling 12 calendar months by entry month
        mdf=pd.DataFrame(month)
        # defer below after month df assembled

S=pd.DataFrame(summary)
Y=pd.DataFrame(year)
M=pd.DataFrame(month)
E=pd.DataFrame(engine)
AD=pd.DataFrame(addon)
T=pd.concat(trades_all,ignore_index=True)
EQ=pd.concat(eq_all,ignore_index=True)

# Rolling 12-month P/L and PF from actual trades, per cost/mode.
for cost in COSTS:
    for mode in MODES:
        z=T[(T.cost_bps==cost)&(T["mode"]==mode)].copy()
        z["mperiod"]=pd.to_datetime(z.entry_time,utc=True).dt.to_period("M")
        allm=pd.period_range(z.mperiod.min(),z.mperiod.max(),freq="M")
        for endp in allm[11:]:
            startp=endp-11
            g=z[(z.mperiod>=startp)&(z.mperiod<=endp)]
            if len(g)==0: continue
            q=perf(g)
            rolling.append(dict(cost_bps=cost,mode=mode,start=str(startp),end=str(endp),**q))
R=pd.DataFrame(rolling)

S.to_csv(OUT/"LAB157_summary.csv",index=False)
Y.to_csv(OUT/"LAB157_year.csv",index=False)
M.to_csv(OUT/"LAB157_month.csv",index=False)
E.to_csv(OUT/"LAB157_engine.csv",index=False)
AD.to_csv(OUT/"LAB157_addon_role.csv",index=False)
R.to_csv(OUT/"LAB157_rolling12m.csv",index=False)
T.to_csv(OUT/"LAB157_trades.csv",index=False)

# Candidate robustness extracts.
cand="LOCK2_LOCK025"
stress=S[(S.cost_bps==7.5)&(S["mode"]==cand)].iloc[0]
base=S[(S.cost_bps==7.5)&(S["mode"]=="TP3_NO_TRANSFER")].iloc[0]
runner=S[(S.cost_bps==7.5)&(S["mode"]=="LOCK2_NO_TRANSFER")].iloc[0]

ys=Y[(Y.cost_bps==7.5)&(Y["mode"]==cand)].copy()
rs=R[(R.cost_bps==7.5)&(R["mode"]==cand)].copy()
ms=M[(M.cost_bps==7.5)&(M["mode"]==cand)].copy()
eng=E[(E.cost_bps==7.5)&(E["mode"]==cand)].copy()
adr=AD[(AD.cost_bps==7.5)&(AD["mode"]==cand)].copy()

prof_months=int((ms.total_r>0).sum())
loss_months=int((ms.total_r<0).sum())
zero_months=int((ms.total_r==0).sum())
worst_month=ms.sort_values("total_r").iloc[0]
best_month=ms.sort_values("total_r",ascending=False).iloc[0]
worst_roll=rs.sort_values("total_r").iloc[0] if len(rs) else None

# concentration: contribution by engine
tot=float(eng.total_r.sum())
eng["contribution_pct"]=100*eng.total_r/tot if tot!=0 else np.nan
eng.to_csv(OUT/"LAB157_engine_with_contribution.csv",index=False)

lines=["# LAB157 — NEW CANDIDATE ARCHITECTURE FULL DATA REPLAY","",
       "Frozen candidate tested exactly:",
       "- Engines: A + B3_HIGH + R48_HIGH + EARLY_EPISODE",
       "- Exit: 50% at +3R; remaining 50% stop locked at +2R after TP3",
       "- Add-on: max 2 positions; second only if first MTM>=0R at current M5 OPEN and same side",
       "- On add-on: first position stop -> max(current stop, +0.25R)",
       "- Risk: 0.25% per position",
       "- No LOWVOL_HALF scaler in the candidate baseline",
       "",
       "## Portfolio comparison"]
for cost in COSTS:
    lines.append(f"### {cost:.2f}bps")
    for mode in MODES:
        r=S[(S.cost_bps==cost)&(S["mode"]==mode)].iloc[0]
        lines.append(f"- {mode}: N={int(r.n)} ({r.trades_month:.2f}/mo), addons={int(r.addons)}, EV={r.ev:+.3f}R, PF={r.pf:.2f}, R/mo={r.r_month:+.2f}, MTM DD={r.mtm_dd_pct:.2f}%, daily={r.daily_start_loss_pct:.2f}%, worst float={r.worst_floating_pct:.2f}%")

lines += ["","## Candidate yearly @7.5bps"]
for _,r in ys.iterrows():
    lines.append(f"- {int(r.year)}: N={int(r.n)}, EV={r.ev:+.3f}R, PF={r.pf:.2f}, WR={r.wr:.1%}, total={r.total_r:+.1f}R, booked DD={r.booked_dd_r:.1f}R, max loss streak={int(r.max_consec_losses)}")

lines += ["","## Candidate engine attribution @7.5bps"]
for _,r in eng.sort_values("total_r",ascending=False).iterrows():
    lines.append(f"- {r.source}: N={int(r.n)}, EV={r.ev:+.3f}R, PF={r.pf:.2f}, total={r.total_r:+.1f}R, contribution={r.contribution_pct:.1f}%")

lines += ["","## Primary vs add-on @7.5bps"]
for _,r in adr.iterrows():
    lines.append(f"- {r.role}: N={int(r.n)}, EV={r.ev:+.3f}R, PF={r.pf:.2f}, total={r.total_r:+.1f}R, max loss streak={int(r.max_consec_losses)}")

lines += ["","## Monthly robustness @7.5bps",
          f"- Profitable months: {prof_months}",
          f"- Losing months: {loss_months}",
          f"- Flat months: {zero_months}",
          f"- Worst month: {worst_month.month}, {worst_month.total_r:+.2f}R, PF={worst_month.pf:.2f}",
          f"- Best month: {best_month.month}, {best_month.total_r:+.2f}R, PF={best_month.pf:.2f}"]
if worst_roll is not None:
    lines.append(f"- Worst rolling 12m: {worst_roll.start}..{worst_roll.end}, total={worst_roll.total_r:+.2f}R, PF={worst_roll.pf:.2f}, EV={worst_roll.ev:+.3f}R")

lines += ["","## Decision",
          f"Candidate stress headline: {stress.trades_month:.2f} trades/mo, EV {stress.ev:+.3f}R, PF {stress.pf:.2f}, R/mo {stress.r_month:+.2f}, MTM DD {stress.mtm_dd_pct:.2f}%, daily {stress.daily_start_loss_pct:.2f}%.",
          f"Versus exact-causal TP3 baseline: R/mo delta {stress.r_month-base.r_month:+.2f}R, MTM DD delta {stress.mtm_dd_pct-base.mtm_dd_pct:+.2f}pp.",
          f"Versus runner without risk-transfer: R/mo delta {stress.r_month-runner.r_month:+.2f}R, MTM DD delta {stress.mtm_dd_pct-runner.mtm_dd_pct:+.2f}pp.",
          "This remains TRAIN/development evidence; do not call it production validated. Exact FTMO CET/CEST reset replay and forward/demo parity are still required."]

(OUT/"LAB157_REPORT.md").write_text("\n".join(lines)+"\n")
(OUT/"LAB157_meta.json").write_text(json.dumps(dict(
    candidate="A+B3_HIGH+R48_HIGH+EARLY_EPISODE / HALF_TP3_LOCK2 / SECOND_MTM_GE0_SAME_SIDE / first stop LOCK025 on add-on",
    risk_pct=RISK,costs=COSTS,lowvol_scaler=False,
    caveat="TRAIN/development full exact-causal replay"
),indent=2))
print("\n".join(lines))
