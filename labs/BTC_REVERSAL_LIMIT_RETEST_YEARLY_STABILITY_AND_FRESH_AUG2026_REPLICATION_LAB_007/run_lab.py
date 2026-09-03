#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, io, json, time, zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import numpy as np
import pandas as pd
import requests

LAB="BTC_REVERSAL_LIMIT_RETEST_YEARLY_STABILITY_AND_FRESH_AUG2026_REPLICATION_LAB_007"
HERE=Path(__file__).resolve().parent
OUT=HERE/"output"; CACHE=HERE/"cache"
OUT.mkdir(parents=True,exist_ok=True); CACHE.mkdir(parents=True,exist_ok=True)

SRC6=HERE.parent/"BTC_REVERSAL_LIMIT_RETEST_RR15_FIRST_HIT_AND_PROP_ECONOMICS_LAB_006"/"run_lab.py"
spec6=importlib.util.spec_from_file_location("lab006",SRC6); L6=importlib.util.module_from_spec(spec6); spec6.loader.exec_module(L6)
L5=L6.L5
PRIMARY_RR=1.5; PRIMARY_COST=5.0
HIST_END="2026-07"
FRESH_START=pd.Timestamp("2026-08-01",tz="UTC")
FRESH_END=pd.Timestamp("2026-08-31 23:59:59",tz="UTC")
SUPPORT_END=pd.Timestamp("2026-09-01 23:59:59",tz="UTC")
DAILY_BASE="https://data.binance.vision/data/spot/daily/klines/BTCUSDT/15m"


def hist_paths():
    ms=[str(x) for x in pd.period_range("2021-01",HIST_END,freq="M")]
    out=[]
    with ThreadPoolExecutor(max_workers=8) as ex:
        fut={ex.submit(L5.get_one,m):m for m in ms}
        for f in as_completed(fut):
            p=f.result()
            if p is None: raise RuntimeError(f"missing historical month {fut[f]}")
            out.append(p)
    return sorted(out)


def daily_url(day):
    s=day.strftime("%Y-%m-%d")
    return f"{DAILY_BASE}/BTCUSDT-15m-{s}.zip"


def get_daily(day):
    s=day.strftime("%Y-%m-%d"); p=CACHE/f"BTCUSDT-15m-{s}.zip"
    if p.exists() and p.stat().st_size>100: return p
    for k in range(4):
        try:
            r=requests.get(daily_url(day),timeout=45)
            r.raise_for_status()
            if len(r.content)<100: raise RuntimeError("tiny response")
            p.write_bytes(r.content); return p
        except Exception:
            if k==3: raise
            time.sleep(1.5*(k+1))


def fresh_paths():
    days=pd.date_range("2026-08-01","2026-09-01",freq="D",tz="UTC")
    out=[]
    with ThreadPoolExecutor(max_workers=8) as ex:
        fut={ex.submit(get_daily,d):d for d in days}
        for f in as_completed(fut): out.append(f.result())
    return sorted(out)


def load_panel():
    hp=hist_paths(); hist=L5.load(hp)
    fps=fresh_paths(); fresh=pd.concat([L5.read_month(p) for p in fps],ignore_index=True).sort_values("time").drop_duplicates("time").set_index("time")
    b=pd.concat([hist,fresh]).sort_index(); b=b[~b.index.duplicated(keep="last")]
    b=b[b.index<=SUPPORT_END]
    return L5.make_panel(b),len(hp),len(fps)


def bucket(ts):
    if ts>=FRESH_START and ts<=FRESH_END: return "FRESH_AUG2026"
    if ts.year==2026: return "2026_JAN_JUL"
    return str(ts.year)


def selected_table(x):
    e,meta=L5.freeze_selector(L5.make_events(x))
    e=e[e.event_time<=FRESH_END].copy()
    e["bucket"]=e.event_time.map(bucket)
    e["is_fresh_aug"]=(e.bucket=="FRESH_AUG2026")
    return e,meta


def execute(x,e):
    rows=[]
    sel=e[e.selected_rev].copy()
    for idx,row in sel.iterrows():
        row=row.copy(); row.name=idx; row["split"]=row.bucket
        for rr in [1.5,2.0]:
            z=L6.first_hit(x,row,rr)
            if z is not None:
                z["bucket"]=row.bucket; z["event_time"]=row.event_time; rows.append(z)
    return pd.DataFrame(rows),sel


def summarize(trades,sel):
    buckets=["2021","2022","2023","2024","2025","2026_JAN_JUL","FRESH_AUG2026"]
    rows=[]
    for b in buckets:
        signals=int((sel.bucket==b).sum())
        for rr in [1.5,2.0]:
            d=trades[(trades.bucket==b)&(trades.rr==rr)].sort_values("fill_time").copy()
            n=len(d); fill=n/signals if signals else np.nan
            if n:
                d["cost_R"]=(PRIMARY_COST/10000.0)/d.stop_frac
                d["net_R"]=d.gross_R-d.cost_R
                net=d.net_R.to_numpy(float)
                ret25,dd25=L6.equity_stats(net,.0025); ret50,dd50=L6.equity_stats(net,.005)
                pf=L6.pf(net); mdd=L6.max_dd_r(net); cons=L6.max_consecutive_loss(net); ov=L6.overlap_max(d)
                tp=float((d.outcome=="TP").mean()); sl=float((d.outcome=="SL").mean()); tm=float((d.outcome=="TIME_EXIT").mean())
                ev=float(d.net_R.mean()); cum=float(d.net_R.sum())
            else:
                ret25=dd25=ret50=dd50=pf=mdd=ev=cum=tp=sl=tm=np.nan; cons=ov=0
            rows.append(dict(bucket=b,rr=rr,cost_bps=PRIMARY_COST,selected_rev=signals,filled=n,fill_rate=fill,tp_rate=tp,sl_rate=sl,time_rate=tm,net_ev_R=ev,profit_factor=pf,cum_net_R=cum,max_dd_R=mdd,max_consecutive_losses=cons,equity_return_025_pct=ret25,equity_maxdd_025_pct=dd25,equity_return_050_pct=ret50,equity_maxdd_050_pct=dd50,max_overlap=ov,risk_load_050_pct=ov*.50))
    return pd.DataFrame(rows)


def val(s,b,col,rr=1.5):
    q=s[(s.bucket==b)&(s.rr==rr)]
    return q.iloc[0][col] if len(q) else np.nan


def make_verdict(s):
    dev_pos=sum(float(val(s,str(y),"net_ev_R"))>0 for y in [2021,2022,2023,2024])
    fresh_sel=int(val(s,"FRESH_AUG2026","selected_rev")); fresh_fill=int(val(s,"FRESH_AUG2026","filled"))
    fresh_ev=float(val(s,"FRESH_AUG2026","net_ev_R")) if fresh_fill else np.nan
    fresh_pf=float(val(s,"FRESH_AUG2026","profit_factor")) if fresh_fill else np.nan
    gates={
      "dev_positive_years_ge_3_of_4":dev_pos>=3,
      "year_2025_positive":float(val(s,"2025","net_ev_R"))>0,
      "y2026_jan_jul_positive":float(val(s,"2026_JAN_JUL","net_ev_R"))>0,
      "recent_pf_gt_1":float(val(s,"2025","profit_factor"))>1 and float(val(s,"2026_JAN_JUL","profit_factor"))>1,
      "recent_closed_dd_050_lt_5pct":float(val(s,"2025","equity_maxdd_050_pct"))<5 and float(val(s,"2026_JAN_JUL","equity_maxdd_050_pct"))<5,
      "fresh_selected_rev_ge_3":fresh_sel>=3,
      "fresh_filled_ge_3":fresh_fill>=3,
      "fresh_net_ev_positive":bool(fresh_fill and fresh_ev>0),
      "fresh_pf_gt_1":bool(fresh_fill and fresh_pf>1),
      "fresh_closed_dd_050_lt_5pct":bool(fresh_fill and float(val(s,"FRESH_AUG2026","equity_maxdd_050_pct"))<5),
    }
    hist=all(gates[k] for k in list(gates)[:5]); fresh_n=gates["fresh_selected_rev_ge_3"] and gates["fresh_filled_ge_3"]; fresh_quality=all(gates[k] for k in list(gates)[7:])
    if hist and fresh_n and fresh_quality: verdict="PASS_FRESH_AUG_REPLICATION_AND_YEARLY_STABILITY"
    elif hist and not fresh_n: verdict="WATCH_FRESH_SAMPLE_TOO_SMALL"
    elif fresh_n and fresh_quality and not hist: verdict="WATCH_MIXED_YEARLY_STABILITY"
    elif fresh_n and (not gates["fresh_net_ev_positive"] or not gates["fresh_pf_gt_1"]): verdict="FAIL_FRESH_REPLICATION"
    else: verdict="FAIL_YEARLY_STABILITY"
    return {"verdict":verdict,"gates_passed":int(sum(gates.values())),"gates_total":len(gates),"gates":gates,"dev_positive_years":int(dev_pos),"fresh_selected_rev":fresh_sel,"fresh_filled":fresh_fill}


def fmtpf(x):
    if pd.isna(x): return "—"
    if np.isinf(x): return "inf"
    return f"{x:.3f}"


def report(s,v,meta,hist_files,fresh_files,x):
    p=s[s.rr==1.5]
    lines=[f"# {LAB}","",f"**Verdict:** **{v['verdict']}**","","Role: frozen LAB006 yearly stability + one-shot fresh August 2026 replication; not a live strategy.","","## Frozen setup","- Exact LAB006 selector + `LIMIT_R0.50_T60` + SL 1.0× event M15 range + TP 1.5R.","- Same-bar ambiguity = SL-first; no market fallback.","- Primary cost stress = 5 bps round trip.",f"- Frozen router q80: **{meta['router_q80']:.6f}**.","","## Data integrity",f"- Historical monthly files through 2026-07: **{hist_files}**.",f"- Fresh daily files loaded: **{fresh_files}** (2026-08-01…2026-09-01; Sep 1 is outcome support only).",f"- Combined completed-bar coverage: **{x.index.min()} → {x.index.max()}**.","- August 2026 is consumed once here as the fresh holdout.","","## Primary RR1.5 / 5bps by year","","| Bucket | Selected REV | Filled | Fill | TP | SL | TIME | Net EV R | PF | Cum R | Max DD R | Max consec L | 0.5% eq return | 0.5% max DD |","|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _,r in p.iterrows():
        lines.append(f"| {r.bucket} | {int(r.selected_rev)} | {int(r.filled)} | {r.fill_rate*100:.1f}% | {r.tp_rate*100:.1f}% | {r.sl_rate*100:.1f}% | {r.time_rate*100:.1f}% | {r.net_ev_R:+.3f} | {fmtpf(r.profit_factor)} | {r.cum_net_R:+.2f} | {r.max_dd_R:.2f} | {int(r.max_consecutive_losses)} | {r.equity_return_050_pct:+.2f}% | {r.equity_maxdd_050_pct:.2f}% |" if r.filled else f"| {r.bucket} | {int(r.selected_rev)} | 0 | 0.0% | — | — | — | — | — | — | — | — | — | — |")
    lines += ["","## RR2.0 audit / 5bps","","| Bucket | Filled | Net EV R | PF | Cum R |","|---|---:|---:|---:|---:|"]
    for _,r in s[s.rr==2.0].iterrows():
        lines.append(f"| {r.bucket} | {int(r.filled)} | {r.net_ev_R:+.3f} | {fmtpf(r.profit_factor)} | {r.cum_net_R:+.2f} |" if r.filled else f"| {r.bucket} | 0 | — | — | — |")
    lines += ["","## Gates"]
    for k,z in v["gates"].items(): lines.append(f"- {'PASS' if z else 'FAIL'} — `{k}`")
    lines += ["",f"**Score {v['gates_passed']}/{v['gates_total']} → {v['verdict']}**","","## Interpretation rules","- If fresh selected or filled N < 3, August sign is descriptive only and cannot promote.","- RR2.0 remains audit-only regardless of its result.","- August 2026 is no longer fresh for any later hypothesis generated after this report."]
    return "\n".join(lines)+"\n"


def main():
    x,hf,ff=load_panel(); e,meta=selected_table(x); trades,sel=execute(x,e); s=summarize(trades,sel); v=make_verdict(s)
    e.to_csv(OUT/"all_events_with_frozen_selector.csv",index=False)
    sel.to_csv(OUT/"selected_rev_events.csv",index=False)
    trades.to_csv(OUT/"filled_first_hit_trades.csv",index=False)
    s.to_csv(OUT/"yearly_summary.csv",index=False)
    (OUT/"verdict.json").write_text(json.dumps(v,indent=2,allow_nan=True),encoding="utf-8")
    rep=report(s,v,meta,hf,ff,x); (OUT/"REPORT.md").write_text(rep,encoding="utf-8")
    print(json.dumps(v,indent=2)); print(rep)

if __name__=="__main__": main()
