#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

LAB="BTC_REVERSAL_H4_TWO_BAR_DIRECTIONAL_ASYMMETRY_AND_BUY_ONLY_CAUSAL_REPLICATION_LAB_019"
HERE=Path(__file__).resolve().parent
OUT=HERE/"output"; OUT.mkdir(parents=True,exist_ok=True)
ROOT=HERE.parent
STREAM=ROOT/"BTC_REVERSAL_H4_PIVOT_M15_TWO_BAR_CONFIRM_FORMAL_REPLICATION_AND_CANONICAL_UNION_LAB_018"/"output"/"two_bar_confirm_vf1_stream.csv"
CANON=ROOT/"BTC_REVERSAL_P975_T25_CONFIRMATION_AND_SECOND_PARENT_FAMILY_DISCOVERY_LAB_015"/"output"/"part_a_p975_t25_signal_stream.csv"
SEED=20260905
BOOT=5000

UTC="UTC"
WINS={
 "2021":(pd.Timestamp("2021-01-01",tz=UTC),pd.Timestamp("2022-01-01",tz=UTC),12.0),
 "2022":(pd.Timestamp("2022-01-01",tz=UTC),pd.Timestamp("2023-01-01",tz=UTC),12.0),
 "2023":(pd.Timestamp("2023-01-01",tz=UTC),pd.Timestamp("2024-01-01",tz=UTC),12.0),
 "2024":(pd.Timestamp("2024-01-01",tz=UTC),pd.Timestamp("2025-01-01",tz=UTC),12.0),
 "2025_H1":(pd.Timestamp("2025-01-01",tz=UTC),pd.Timestamp("2025-07-01",tz=UTC),6.0),
 "2025_H2":(pd.Timestamp("2025-07-01",tz=UTC),pd.Timestamp("2026-01-01",tz=UTC),6.0),
 "2026_JAN_JUL":(pd.Timestamp("2026-01-01",tz=UTC),pd.Timestamp("2026-08-01",tz=UTC),7.0),
 "POOLED_RECENT":(pd.Timestamp("2025-07-01",tz=UTC),pd.Timestamp("2026-08-01",tz=UTC),13.0),
 "HIST_PRE_RECENT":(pd.Timestamp("2021-01-01",tz=UTC),pd.Timestamp("2025-07-01",tz=UTC),54.0),
 "ALL_PRE_AUG":(pd.Timestamp("2021-01-01",tz=UTC),pd.Timestamp("2026-08-01",tz=UTC),67.0),
 "AUG2026_REUSED_AUDIT":(pd.Timestamp("2026-08-01",tz=UTC),pd.Timestamp("2026-09-01",tz=UTC),1.0),
}
RECENT_MONTHS=pd.period_range("2025-07","2026-07",freq="M").astype(str).tolist()
HIST_NAMES=["2021","2022","2023","2024","2025_H1"]


def b(v):
    if isinstance(v,(bool,np.bool_)): return bool(v)
    return str(v).strip().lower() in {"true","1","yes"}

def prep(d):
    for c in ["parent_time","signal_time","event_time","fill_time","exit_time"]:
        if c in d.columns: d[c]=pd.to_datetime(d[c],utc=True,errors="coerce")
    for c in ["filled","vf1_mature","real_fill"]:
        if c in d.columns: d[c]=d[c].map(b)
    for c in ["real_R","signal_net_R","impulse_dir"]:
        if c in d.columns: d[c]=pd.to_numeric(d[c],errors="coerce").fillna(0.0)
    return d

def pf(a):
    a=np.asarray(a,float); pos=float(a[a>0].sum()); neg=float(-a[a<0].sum())
    if neg==0: return np.inf if pos>0 else np.nan
    return pos/neg

def maxdd(a):
    a=np.asarray(a,float)
    if len(a)==0:return 0.0
    eq=np.cumsum(a); peak=np.maximum.accumulate(np.r_[0.0,eq]); dd=peak[1:]-eq
    return float(dd.max()) if len(dd) else 0.0

def max_consec_loss(a):
    m=cur=0
    for x in np.asarray(a,float):
        if x<0: cur+=1; m=max(m,cur)
        else: cur=0
    return int(m)

def episode_stats(d):
    if len(d)==0:return dict(episodes=0,positive_episodes=0,negative_episodes=0,loeo=np.nan,worst_episode=np.nan)
    ep=d.groupby("episode_7d",sort=True).real_R.sum().astype(float)
    total=float(ep.sum())
    loeo=float((total-ep).min()) if len(ep) else np.nan
    return dict(episodes=int(len(ep)),positive_episodes=int((ep>0).sum()),negative_episodes=int((ep<0).sum()),loeo=loeo,worst_episode=float(ep.min()) if len(ep) else np.nan)

def summarize_side(stream,side,w,a,b_,months):
    d=stream[(stream.parent_time>=a)&(stream.parent_time<b_)&(stream.side==side)&(stream.real_fill)].copy().sort_values("fill_time")
    r=d.real_R.to_numpy(float)
    es=episode_stats(d)
    return dict(window=w,side=side,real_fills=len(d),fills_per_month=float(len(d)/months),cum_R=float(r.sum()) if len(r) else 0.0,mean_R=float(r.mean()) if len(r) else np.nan,profit_factor=pf(r),max_dd_R=maxdd(r),max_consecutive_losses=max_consec_loss(r),**es)

def cluster_boot_buy(stream):
    a,b_,_=WINS["POOLED_RECENT"]
    d=stream[(stream.parent_time>=a)&(stream.parent_time<b_)&(stream.side=="BUY")&(stream.real_fill)].copy()
    groups=[q.real_R.to_numpy(float) for _,q in d.groupby("episode_7d",sort=True) if len(q)]
    if not groups:return dict(n_episodes=0,low=np.nan,median=np.nan,high=np.nan)
    rng=np.random.default_rng(SEED); vals=[]
    n=len(groups)
    for _ in range(BOOT):
        idx=rng.integers(0,n,size=n)
        arr=np.concatenate([groups[i] for i in idx])
        vals.append(float(arr.mean()) if len(arr) else np.nan)
    q=np.nanpercentile(vals,[2.5,50,97.5])
    return dict(n_episodes=n,low=float(q[0]),median=float(q[1]),high=float(q[2]))

def monthly_buy(stream):
    a,b_,_=WINS["POOLED_RECENT"]
    d=stream[(stream.parent_time>=a)&(stream.parent_time<b_)&(stream.side=="BUY")&(stream.real_fill)].copy()
    d["month"]=d.parent_time.dt.to_period("M").astype(str)
    rows=[]
    for m in RECENT_MONTHS:
        q=d[d.month==m]; r=q.real_R.to_numpy(float)
        rows.append(dict(month=m,fills=len(q),cum_R=float(r.sum()) if len(r) else 0.0,mean_R=float(r.mean()) if len(r) else np.nan,profit_factor=pf(r)))
    tab=pd.DataFrame(rows); total=float(tab.cum_R.sum())
    tab["leave_month_out_remaining_R"]=total-tab.cum_R
    return tab,float(tab.leave_month_out_remaining_R.min()),int((tab.cum_R>0).sum())

def historical_window_loo(side_tab):
    q=side_tab[(side_tab.side=="BUY")&(side_tab.window.isin(HIST_NAMES))].copy()
    total=float(q.cum_R.sum()); q["leave_window_out_remaining_R"]=total-q.cum_R
    return q,float(q.leave_window_out_remaining_R.min()) if len(q) else np.nan,int((q.cum_R>0).sum())

def equity_stats(a,risk):
    eq=peak=1.0; dd=0.0
    for x in np.asarray(a,float):
        eq*=max(0.0,1.0+risk*x); peak=max(peak,eq); dd=max(dd,(peak-eq)/peak)
    return (eq-1)*100.0,dd*100.0

def max_concurrent(d):
    q=d.dropna(subset=["fill_time","exit_time"]).copy()
    if len(q)==0:return 0
    starts=pd.to_datetime(q.fill_time,utc=True).to_numpy(); ends=pd.to_datetime(q.exit_time,utc=True).to_numpy(); mx=0
    for t in starts: mx=max(mx,int(np.sum((starts<=t)&(ends>t))))
    return int(mx)

def canon_prep():
    c=prep(pd.read_csv(CANON))
    # conservative concurrency endpoint because persisted canonical artifact lacks actual exit timestamp
    c["exit_time"]=c.event_time+pd.Timedelta(hours=24)
    return c

def union_metrics(canon,stream,w,a,b_,months):
    c=canon[(canon.event_time>=a)&(canon.event_time<b_)&(canon.real_fill)].copy(); c["src"]="CANON"
    h=stream[(stream.parent_time>=a)&(stream.parent_time<b_)&(stream.real_fill)&(stream.side=="BUY")].copy(); h["src"]="H4_BUY"
    cols=["src","fill_time","exit_time","real_R"]
    z=pd.concat([c[cols],h[cols]],ignore_index=True).sort_values("fill_time")
    r=z.real_R.to_numpy(float); mc=max_concurrent(z); er25,ed25=equity_stats(r,.0025); er50,ed50=equity_stats(r,.005)
    return dict(window=w,real_fills=len(z),fills_per_month=float(len(z)/months),canonical_fills=int((z.src=="CANON").sum()),h4_buy_fills=int((z.src=="H4_BUY").sum()),cum_R=float(r.sum()),mean_R=float(r.mean()) if len(r) else np.nan,profit_factor=pf(r),max_dd_R=maxdd(r),max_concurrent=mc,risk_load_025_pct=.25*mc,risk_load_050_pct=.50*mc,equity_return_025_pct=er25,equity_dd_025_pct=ed25,equity_return_050_pct=er50,equity_dd_050_pct=ed50),z

def canon_metrics(canon,w,a,b_,months):
    d=canon[(canon.event_time>=a)&(canon.event_time<b_)&(canon.real_fill)].copy().sort_values("fill_time"); r=d.real_R.to_numpy(float)
    return dict(window=w,real_fills=len(d),fills_per_month=len(d)/months,cum_R=float(r.sum()),mean_R=float(r.mean()) if len(r) else np.nan,profit_factor=pf(r),max_dd_R=maxdd(r))

def fmt(x):
    if pd.isna(x):return "—"
    if np.isinf(x):return "inf"
    return f"{x:.3f}"

def main():
    stream=prep(pd.read_csv(STREAM)); canon=canon_prep()
    stream["side"]=np.where(stream.impulse_dir<0,"BUY","SELL")

    # exact persisted lineage/parity from LAB018 report
    a25,b25,_=WINS["2025_H2"]; a26,b26,_=WINS["2026_JAN_JUL"]
    h2=stream[(stream.parent_time>=a25)&(stream.parent_time<b25)&(stream.real_fill)]
    y26=stream[(stream.parent_time>=a26)&(stream.parent_time<b26)&(stream.real_fill)]
    lineage=(stream.parent_id.nunique()==213 and len(h2)==11 and len(y26)==7 and int((h2.side=="BUY").sum())==8 and int((h2.side=="SELL").sum())==3 and int((y26.side=="BUY").sum())==6 and int((y26.side=="SELL").sum())==1)
    if not lineage:
        raise RuntimeError(f"LAB018 stream parity failed: parents={stream.parent_id.nunique()}, h2={len(h2)}, y26={len(y26)}, h2 sides={h2.side.value_counts().to_dict()}, y26 sides={y26.side.value_counts().to_dict()}")

    side_rows=[]
    for w,(a,b_,m) in WINS.items():
        for side in ["BUY","SELL"]: side_rows.append(summarize_side(stream,side,w,a,b_,m))
    sides=pd.DataFrame(side_rows)

    monthly,month_lo,positive_months=monthly_buy(stream)
    hist_table,hist_loo,hist_positive=historical_window_loo(sides)
    boot=cluster_boot_buy(stream)

    unions=[]; utrades=[]; canrows=[]
    for w in ["2025_H2","2026_JAN_JUL","POOLED_RECENT"]:
        a,b_,m=WINS[w]; u,z=union_metrics(canon,stream,w,a,b_,m); unions.append(u); z["window"]=w; utrades.append(z); canrows.append(canon_metrics(canon,w,a,b_,m))
    union=pd.DataFrame(unions); ctab=pd.DataFrame(canrows)

    def sr(side,w): return sides[(sides.side==side)&(sides.window==w)].iloc[0]
    bh2=sr("BUY","2025_H2"); by26=sr("BUY","2026_JAN_JUL"); br=sr("BUY","POOLED_RECENT")
    sh2=sr("SELL","2025_H2"); sy26=sr("SELL","2026_JAN_JUL")
    hist=sr("BUY","HIST_PRE_RECENT")
    up=union[union.window=="POOLED_RECENT"].iloc[0]

    gates={
      "lineage_exact":bool(lineage),
      "buy_h2_fills_ge_6":int(bh2.real_fills)>=6,
      "buy_2026_fills_ge_5":int(by26.real_fills)>=5,
      "buy_cumR_positive_both_recent":float(bh2.cum_R)>0 and float(by26.cum_R)>0,
      "buy_meanR_ge_0_30_both_recent":float(bh2.mean_R)>=.30 and float(by26.mean_R)>=.30,
      "buy_pf_gt_1_50_both_recent":float(bh2.profit_factor)>1.50 and float(by26.profit_factor)>1.50,
      "buy_sell_mean_delta_positive_both_recent":float(bh2.mean_R)>float(sh2.mean_R) and float(by26.mean_R)>float(sy26.mean_R),
      "sell_cumR_negative_both_recent":float(sh2.cum_R)<0 and float(sy26.cum_R)<0,
      "buy_recent_loeo_positive":bool(np.isfinite(br.loeo) and float(br.loeo)>0),
      "buy_recent_cluster_bootstrap_low_gt_0":bool(np.isfinite(boot["low"]) and boot["low"]>0),
      "hist_buy_cumR_positive":float(hist.cum_R)>0,
      "hist_buy_pf_gt_1_20":bool(np.isfinite(hist.profit_factor) and float(hist.profit_factor)>1.20),
      "hist_buy_positive_windows_ge_3_of_5":hist_positive>=3,
      "hist_buy_leave_one_window_out_positive":bool(np.isfinite(hist_loo) and hist_loo>0),
      "union_freq_ge_2_75_per_month":float(up.fills_per_month)>=2.75,
      "union_cumR_gt_all_direction_union_21_67R":float(up.cum_R)>21.67,
      "union_pf_ge_2_50":float(up.profit_factor)>=2.50,
      "union_maxdd_le_3_75R":float(up.max_dd_R)<=3.75,
      "union_riskload_050_lt_4pct":float(up.risk_load_050_pct)<4.0,
    }
    n=int(sum(bool(v) for v in gates.values()))
    recent_critical=["lineage_exact","buy_cumR_positive_both_recent","buy_meanR_ge_0_30_both_recent","buy_pf_gt_1_50_both_recent","buy_sell_mean_delta_positive_both_recent","sell_cumR_negative_both_recent","buy_recent_loeo_positive"]
    hist_critical=["hist_buy_cumR_positive","hist_buy_pf_gt_1_20","hist_buy_positive_windows_ge_3_of_5","hist_buy_leave_one_window_out_positive"]
    union_critical=["union_freq_ge_2_75_per_month","union_cumR_gt_all_direction_union_21_67R","union_pf_ge_2_50","union_maxdd_le_3_75R","union_riskload_050_lt_4pct"]
    if n>=16 and all(gates[k] for k in recent_critical+hist_critical+union_critical): verdict="PASS_STRUCTURAL_BUY_DOMINANCE_REUSED"
    elif n>=14 and all(gates[k] for k in recent_critical+union_critical) and not all(gates[k] for k in hist_critical): verdict="PASS_RECENT_BUY_DOMINANCE_REUSED"
    elif gates["buy_cumR_positive_both_recent"] and gates["buy_sell_mean_delta_positive_both_recent"]: verdict="WATCH_RECENT_BUY_ASYMMETRY"
    else: verdict="FAIL_BUY_ONLY_DIRECTIONAL_REPLICATION"

    # Pooled asymmetry deltas
    asym=[]
    for w in ["2025_H2","2026_JAN_JUL","POOLED_RECENT","HIST_PRE_RECENT","ALL_PRE_AUG"]:
        bu=sr("BUY",w); se=sr("SELL",w)
        asym.append(dict(window=w,buy_fills=int(bu.real_fills),sell_fills=int(se.real_fills),buy_cum_R=float(bu.cum_R),sell_cum_R=float(se.cum_R),cumR_delta=float(bu.cum_R-se.cum_R),buy_mean_R=float(bu.mean_R) if np.isfinite(bu.mean_R) else np.nan,sell_mean_R=float(se.mean_R) if np.isfinite(se.mean_R) else np.nan,meanR_delta=float(bu.mean_R-se.mean_R) if np.isfinite(bu.mean_R) and np.isfinite(se.mean_R) else np.nan))
    asym=pd.DataFrame(asym)

    sides.to_csv(OUT/"directional_window_summary.csv",index=False)
    monthly.to_csv(OUT/"buy_recent_monthly.csv",index=False)
    hist_table.to_csv(OUT/"buy_historical_window_loo.csv",index=False)
    union.to_csv(OUT/"canonical_plus_h4_buy_union.csv",index=False)
    ctab.to_csv(OUT/"canonical_only_summary.csv",index=False)
    asym.to_csv(OUT/"directional_asymmetry.csv",index=False)
    pd.concat(utrades,ignore_index=True).to_csv(OUT/"buy_only_union_trades.csv",index=False)
    stream.to_csv(OUT/"frozen_two_bar_stream_with_side.csv",index=False)

    v={"verdict":verdict,"gates_passed":n,"gates_total":len(gates),"gates":gates,"bootstrap":boot,"positive_recent_buy_months":positive_months,"buy_recent_month_loo_worst_R":month_lo,"historical_positive_buy_windows":hist_positive,"historical_leave_one_window_out_worst_R":hist_loo,"lineage":{"parents":int(stream.parent_id.nunique()),"h2_fills":len(h2),"y26_fills":len(y26),"h2_buy":int((h2.side=="BUY").sum()),"h2_sell":int((h2.side=="SELL").sum()),"y26_buy":int((y26.side=="BUY").sum()),"y26_sell":int((y26.side=="SELL").sum())}}
    (OUT/"verdict.json").write_text(json.dumps(v,indent=2,allow_nan=True),encoding="utf-8")

    lines=[f"# {LAB}","",f"**Verdict: {verdict} — {n}/{len(gates)}**","","Frozen primary candidate: H4 `TWO_BAR_CONFIRM_12H + VF1`, real orders BUY-only (`impulse_dir < 0`); all directions remain active as shadow/virtual state.","","## Directional windows","","| Window | Side | Fills | Fills/mo | Cum R | Mean R | PF | DD R | LOEO worst |","|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for w in ["2021","2022","2023","2024","2025_H1","2025_H2","2026_JAN_JUL","POOLED_RECENT","HIST_PRE_RECENT","ALL_PRE_AUG","AUG2026_REUSED_AUDIT"]:
        for side in ["BUY","SELL"]:
            r=sr(side,w)
            lines.append(f"| {w} | {side} | {int(r.real_fills)} | {r.fills_per_month:.2f} | {r.cum_R:+.2f} | {r.mean_R:+.3f} | {fmt(r.profit_factor)} | {r.max_dd_R:.2f} | {r.loeo:+.2f} |" if r.real_fills else f"| {w} | {side} | 0 | 0.00 | +0.00 | — | — | 0.00 | — |")
    lines += ["","## Recent BUY robustness",f"- 7d episode bootstrap, {BOOT} draws: **[{boot['low']:+.3f}, {boot['median']:+.3f}, {boot['high']:+.3f}] R/fill**, episodes={boot['n_episodes']}.",f"- Positive BUY months: **{positive_months}/13**.",f"- Worst leave-one-month-out remaining R: **{month_lo:+.2f}R**.",f"- Historical positive BUY windows: **{hist_positive}/5**; worst leave-one-window-out remaining R: **{hist_loo:+.2f}R**.","","## Canonical + H4 BUY-only union","","| Window | Fills | Fills/mo | Canon | H4 BUY | Cum R | Mean R | PF | DD R | Max conc | Risk load @0.5% | Eq ret @0.25% | Eq DD @0.25% | Eq ret @0.5% | Eq DD @0.5% |","|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _,r in union.iterrows():
        lines.append(f"| {r.window} | {int(r.real_fills)} | {r.fills_per_month:.2f} | {int(r.canonical_fills)} | {int(r.h4_buy_fills)} | {r.cum_R:+.2f} | {r.mean_R:+.3f} | {fmt(r.profit_factor)} | {r.max_dd_R:.2f} | {int(r.max_concurrent)} | {r.risk_load_050_pct:.2f}% | {r.equity_return_025_pct:+.2f}% | {r.equity_dd_025_pct:.2f}% | {r.equity_return_050_pct:+.2f}% | {r.equity_dd_050_pct:.2f}% |")
    lines += ["", "LAB018 all-direction pooled benchmark: **41 fills, 3.15/month, +21.67R, PF 2.402, DD 3.75R**.","","## Gates"]
    for k,val in gates.items(): lines.append(f"- {'PASS' if val else 'FAIL'} — `{k}`")
    lines += ["","## Status","- This is a formal promotion/replication on **reused research windows**, not fresh OOS.","- August 2026 is consumed/reused audit only and cannot rescue the verdict.","- No SELL rescue, time filter, RR change, child-rule change or threshold change is allowed after this run.","- Canonical concurrency is conservatively bounded with `event_time + 24h` because its persisted artifact lacks actual exit timestamps; PnL/PF/DD-R are unaffected.","- Live allocation remains **0** pending fresh replication and execution/cost parity."]
    (OUT/"REPORT.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps(v,indent=2,allow_nan=True)); print((OUT/"REPORT.md").read_text())

if __name__=="__main__": main()
