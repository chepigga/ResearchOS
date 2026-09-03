#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd

LAB="BTC_REVERSAL_LIMIT_RETEST_RR15_FIRST_HIT_AND_PROP_ECONOMICS_LAB_006"
SEED=20260903
HERE=Path(__file__).resolve().parent
OUT=HERE/"output"; OUT.mkdir(parents=True,exist_ok=True)
SRC=HERE.parent/"BTC_24H_REVERSAL_ENTRY_DECAY_AND_CAUSAL_LIMIT_RETEST_LAB_005"/"run_lab.py"
spec=importlib.util.spec_from_file_location("lab005",SRC); L5=importlib.util.module_from_spec(spec); spec.loader.exec_module(L5)
RRS=[1.5,2.0]; COST_BPS=[0.0,2.0,5.0,10.0]; PRIMARY_RR=1.5; PRIMARY_COST=5.0
LIMIT_MULT=.50; TTL=4

def first_hit(x,row,rr):
    i=int(row.event_i); d=float(row.impulse_dir); rng=float(row.event_high-row.event_low)
    if not np.isfinite(rng) or rng<=0: return None
    entry=float(row.event_close+d*LIMIT_MULT*rng)
    fill=None
    for k in range(i+1,min(i+1+TTL,i+L5.H24)):
        hi=float(x.btc_high.iloc[k]); lo=float(x.btc_low.iloc[k])
        if (d>0 and hi>=entry) or (d<0 and lo<=entry): fill=k; break
    if fill is None: return None
    sl=entry+d*rng; tp=entry-d*rr*rng
    exit_i=i+L5.H24; outcome="TIME_EXIT"; gross=np.nan
    actual_exit=exit_i
    mfe=0.0; mae=0.0
    for k in range(fill,exit_i+1):
        hi=float(x.btc_high.iloc[k]); lo=float(x.btc_low.iloc[k])
        if d>0:
            fav=(entry-lo)/rng; adv=(hi-entry)/rng; hit_sl=hi>=sl; hit_tp=lo<=tp
        else:
            fav=(hi-entry)/rng; adv=(entry-lo)/rng; hit_sl=lo<=sl; hit_tp=hi>=tp
        mfe=max(mfe,float(fav)); mae=max(mae,float(adv))
        if hit_sl and hit_tp:
            outcome="SL"; gross=-1.0; actual_exit=k; break
        if hit_sl:
            outcome="SL"; gross=-1.0; actual_exit=k; break
        if hit_tp:
            outcome="TP"; gross=float(rr); actual_exit=k; break
    if outcome=="TIME_EXIT":
        px=float(x.btc_close.iloc[exit_i]); gross=float(-d*(px-entry)/rng)
    stop_frac=rng/entry
    return dict(event_row=int(row.name),split=row.split,event_time=row.event_time,impulse_dir=d,rr=float(rr),entry=entry,fill_i=int(fill),fill_time=x.index[fill],exit_i=int(actual_exit),exit_time=x.index[actual_exit],outcome=outcome,gross_R=gross,mfe_R=float(mfe),mae_R=float(mae),stop_frac=float(stop_frac),duration_h=float((actual_exit-fill)*.25))

def max_consecutive_loss(a):
    best=cur=0
    for v in a:
        if v<0: cur+=1; best=max(best,cur)
        else: cur=0
    return int(best)

def max_dd_r(a):
    c=np.cumsum(np.asarray(a,float)); c=np.r_[0.0,c]; peak=np.maximum.accumulate(c); return float(np.max(peak-c))

def pf(a):
    a=np.asarray(a,float); pos=a[a>0].sum(); neg=-a[a<0].sum()
    return float(pos/neg) if neg>0 else (float("inf") if pos>0 else np.nan)

def overlap_max(d):
    if len(d)==0: return 0
    starts=d.fill_time.to_numpy(); ends=d.exit_time.to_numpy(); mx=0
    for t in starts:
        mx=max(mx,int(np.sum((starts<=t)&(ends>t))))
    return mx

def equity_stats(net_r,risk):
    eq=1.0; peak=1.0; mdd=0.0
    for r in net_r:
        eq*=max(0.0,1.0+risk*float(r)); peak=max(peak,eq); mdd=max(mdd,(peak-eq)/peak)
    return float((eq-1.0)*100),float(mdd*100)

def summarize(trades):
    rows=[]
    for (sp,rr),d0 in trades.groupby(["split","rr"]):
        d0=d0.sort_values("fill_time")
        ov=overlap_max(d0)
        for cb in COST_BPS:
            d=d0.copy(); d["cost_R"]=(cb/10000.0)/d.stop_frac; d["net_R"]=d.gross_R-d.cost_R
            net=d.net_R.to_numpy(float)
            ret25,dd25=equity_stats(net,.0025); ret50,dd50=equity_stats(net,.005)
            rows.append(dict(split=sp,rr=rr,cost_bps=cb,n=len(d),tp_rate=float((d.outcome=="TP").mean()),sl_rate=float((d.outcome=="SL").mean()),time_rate=float((d.outcome=="TIME_EXIT").mean()),gross_ev_R=float(d.gross_R.mean()),net_ev_R=float(d.net_R.mean()),profit_factor=pf(net),cum_net_R=float(d.net_R.sum()),max_consecutive_losses=max_consecutive_loss(net),max_dd_R=max_dd_r(net),mean_mfe_R=float(d.mfe_R.mean()),mean_mae_R=float(d.mae_R.mean()),median_duration_h=float(d.duration_h.median()),max_overlap=int(ov),risk_load_025_pct=float(ov*.25),risk_load_050_pct=float(ov*.50),equity_return_025_pct=ret25,equity_maxdd_025_pct=dd25,equity_return_050_pct=ret50,equity_maxdd_050_pct=dd50))
    return pd.DataFrame(rows)

def gate(summary,split,col,rr=PRIMARY_RR,cost=PRIMARY_COST):
    q=summary[(summary.split==split)&(summary.rr==rr)&(summary.cost_bps==cost)]
    return q.iloc[0][col] if len(q) else np.nan

def verdict(summary):
    b="BRIDGE_2025"; o="OOS_2026"
    gates={
      "bridge_filled_ge_15":int(gate(summary,b,"n"))>=15,
      "oos_filled_ge_10":int(gate(summary,o,"n"))>=10,
      "bridge_net_ev_positive":float(gate(summary,b,"net_ev_R"))>0,
      "oos_net_ev_positive":float(gate(summary,o,"net_ev_R"))>0,
      "bridge_pf_gt_1":float(gate(summary,b,"profit_factor"))>1,
      "oos_pf_gt_1":float(gate(summary,o,"profit_factor"))>1,
      "oos_max_consecutive_losses_le_8":int(gate(summary,o,"max_consecutive_losses"))<=8,
      "oos_equity_maxdd_050_lt_5pct":float(gate(summary,o,"equity_maxdd_050_pct"))<5,
      "oos_overlap_risk_050_lt_4pct":float(gate(summary,o,"risk_load_050_pct"))<4,
    }
    n=sum(bool(v) for v in gates.values()); pos=gates["bridge_net_ev_positive"] and gates["oos_net_ev_positive"]
    if n==9: v="PASS_PROP_ECONOMICS_SCREEN"
    elif n>=7 and pos: v="WATCH_PROP_ECONOMICS"
    else: v="FAIL_RR15_PROP_ECONOMICS"
    return {"verdict":v,"gates_passed":int(n),"gates_total":len(gates),"gates":gates}

def fmt(x,pct=False):
    if pd.isna(x): return "—"
    if np.isinf(x): return "inf"
    return f"{x:.3f}"+("%" if pct else "")

def report(summary,v,meta):
    p=summary[(summary.rr==PRIMARY_RR)&(summary.cost_bps==PRIMARY_COST)].copy()
    lines=[f"# {LAB}","",f"**Verdict:** **{v['verdict']}**",f"", "Role: frozen LAB005 limit-entry first-hit / prop-economics screen; not a live strategy.","","## Frozen setup",f"- Selector/entry: exact LAB005 REV selector + `LIMIT_R0.50_T60`.","- 1R = 1.00 × parent event M15 range from filled limit.","- Primary TP = 1.5R; secondary audit = 2.0R.","- Ambiguous same M15 SL+TP = SL-first.","- Primary cost stress = 5 bps round trip; 0/2/10 bps are sensitivity.",f"- Frozen router q80: **{meta['router_q80']:.6f}**.","","## Primary RR1.5 / 5bps", "","| Split | N | TP | SL | TIME | Net EV R | PF | Cum R | Max DD R | Max consec L | MFE R | MAE R | 0.5% eq return | 0.5% max DD | Max overlap | Risk load |","|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _,r in p.iterrows():
        lines.append(f"| {r.split} | {int(r.n)} | {r.tp_rate*100:.1f}% | {r.sl_rate*100:.1f}% | {r.time_rate*100:.1f}% | {r.net_ev_R:+.3f} | {fmt(r.profit_factor)} | {r.cum_net_R:+.2f} | {r.max_dd_R:.2f} | {int(r.max_consecutive_losses)} | {r.mean_mfe_R:.2f} | {r.mean_mae_R:.2f} | {r.equity_return_050_pct:+.2f}% | {r.equity_maxdd_050_pct:.2f}% | {int(r.max_overlap)} | {r.risk_load_050_pct:.2f}% |")
    lines += ["","## Cost sensitivity — RR1.5","","| Split | Cost | Net EV R | PF | Cum R |","|---|---:|---:|---:|---:|"]
    for _,r in summary[summary.rr==1.5].iterrows():
        lines.append(f"| {r.split} | {r.cost_bps:.0f} bps | {r.net_ev_R:+.3f} | {fmt(r.profit_factor)} | {r.cum_net_R:+.2f} |")
    lines += ["","## RR2.0 audit at 5bps","","| Split | N | TP | SL | TIME | Net EV R | PF | Cum R |","|---|---:|---:|---:|---:|---:|---:|---:|"]
    for _,r in summary[(summary.rr==2.0)&(summary.cost_bps==5.0)].iterrows():
        lines.append(f"| {r.split} | {int(r.n)} | {r.tp_rate*100:.1f}% | {r.sl_rate*100:.1f}% | {r.time_rate*100:.1f}% | {r.net_ev_R:+.3f} | {fmt(r.profit_factor)} | {r.cum_net_R:+.2f} |")
    lines += ["","## Gates"]
    for k,val in v["gates"].items(): lines.append(f"- {'PASS' if val else 'FAIL'} — `{k}`")
    lines += ["",f"**Score {v['gates_passed']}/{v['gates_total']} -> {v['verdict']}**","","## Caveats","","- 5 bps is a frozen stress assumption, not a claim about the exact current FTMO BTC CFD all-in cost.","- Closed-equity DD understates a prop firm's floating intraday DD. Max concurrent initial risk is reported separately.","- Sample sizes remain small, especially 2026; this LAB screens monetization geometry, not final production readiness.","- No 2026 tuning of selector, limit distance, TTL, SL distance, RR, or cost gate is authorized after this run."]
    return "\n".join(lines)+"\n"

def main():
    x=L5.make_panel(L5.load(L5.downloads())); e,meta=L5.freeze_selector(L5.make_events(x)); sel=e[e.selected_rev].copy()
    rows=[]
    for idx,row in sel.iterrows():
        row=row.copy(); row.name=idx
        for rr in RRS:
            z=first_hit(x,row,rr)
            if z is not None: rows.append(z)
    trades=pd.DataFrame(rows).sort_values(["fill_time","rr"])
    summary=summarize(trades); v=verdict(summary)
    trades.to_csv(OUT/"trades_first_hit.csv",index=False); summary.to_csv(OUT/"economics_summary.csv",index=False)
    (OUT/"verdict.json").write_text(json.dumps(v,indent=2,allow_nan=True),encoding="utf-8")
    (OUT/"REPORT.md").write_text(report(summary,v,meta),encoding="utf-8")
    print(json.dumps(v,indent=2)); print((OUT/"REPORT.md").read_text())
if __name__=="__main__": main()
