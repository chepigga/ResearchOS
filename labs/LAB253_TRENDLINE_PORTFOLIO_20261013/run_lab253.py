#!/usr/bin/env python3
"""LAB253 rough BTC M5 portfolio replay. Research only; NOT MT5 parity.
Input signals: entry_time, side (+1/-1 or BUY/SELL), atr, source.
The events must be RAW pre-portfolio candidates; do not use accepted LAB151 trades.
"""
from __future__ import annotations
import argparse, importlib.util, json, sys, zipfile
from pathlib import Path
import numpy as np
import pandas as pd

PRIORITY = {"ENGINE_A": 0, "A": 0, "B3_HIGH": 1, "R48_HIGH": 2, "EARLY_EPISODE": 3, "TL_ADD": 4}
VARIANTS = ("BASE", "TL_FILTER", "TL_TRAIL", "TL_ADD", "COMBINED")

def load_prices(path):
    path = Path(path)
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as z:
            frames = []
            for f in z.namelist():
                if f.lower().endswith(".csv"):
                    with z.open(f) as handle:
                        frames.append(pd.read_csv(handle))
            if not frames:
                raise ValueError("No CSV found in price ZIP")
            d = pd.concat(frames, ignore_index=True)
    else:
        d = pd.read_csv(path)
    d.columns = [x.strip().lower() for x in d.columns]
    t = "time" if "time" in d.columns else "datetime"
    d[t] = pd.to_datetime(d[t], utc=True, errors="coerce")
    d = d.dropna(subset=[t]).drop_duplicates(t).sort_values(t).set_index(t)
    return d[["open", "high", "low", "close"]].astype(float)

def load_raw(path):
    d = pd.read_csv(path)
    required = {"entry_time", "side", "atr"}
    if not required.issubset(d.columns):
        raise ValueError(f"raw signals need columns {sorted(required)}; got {list(d.columns)}")
    d["entry_time"] = pd.to_datetime(d["entry_time"], utc=True)
    d["side"] = d["side"].replace({"BUY": 1, "SELL": -1, "LONG": 1, "SHORT": -1, "buy":1, "sell":-1}).astype(int)
    if "source" not in d:
        d["source"] = "ENGINE_A"
    d["pri"] = d["source"].map(PRIORITY).fillna(50)
    return d.sort_values(["entry_time", "pri"]).reset_index(drop=True)

def load_tl(module_path, price, offset):
    spec = importlib.util.spec_from_file_location("trendlines_lab253", str(module_path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    h1 = mod.resample_server_time(price, "1h", offset)
    h4 = mod.resample_server_time(price, "4h", offset)
    shift = pd.Timedelta(hours=offset)
    shifted = price.copy()
    shifted.index = shifted.index + shift
    main = mod.compute_main(h4)
    corr = mod.compute_corr(h1, main)
    cl = mod.cl_break_signals(shifted, corr, main)
    return mod, main, corr, cl, shift

def atr_h1(m5):
    h1 = m5.resample("1h").agg({"open":"first","high":"max","low":"min","close":"last"}).dropna()
    prev = h1.close.shift(1)
    tr = pd.concat([h1.high-h1.low, (h1.high-prev).abs(), (h1.low-prev).abs()],axis=1).max(axis=1)
    return tr.rolling(14).mean()

def main_dir(mod, main, time, shift):
    return mod.main_trend_at(main, pd.Timestamp(time) + shift)

def line_stop(corr, time, side, shift, entry, atr):
    t = pd.Timestamp(time) + shift
    j = corr.index.searchsorted(t, side="right") - 2
    if j < 0: return None
    r = corr.iloc[j]
    if int(r["valid"]) != 1 or int(r["dir"]) != side:
        return None
    val = float(r["A_price"]) + float(r["slope_per_sec"]) * (t - r["A_time"]).total_seconds()
    return val - side * .3 * atr

def assemble_events(raw, cl, price, shift, atrseries):
    d = raw.copy()
    if len(cl):
        add = cl.copy()
        add["entry_time"] = pd.to_datetime(add["time"], utc=True) - shift + pd.Timedelta(minutes=5)
        add["source"] = "TL_ADD"
        add["side"] = add["dir"].astype(int)
        add = add[["entry_time","source","side","atr"]]
        d = pd.concat([d,add],ignore_index=True)
    d["pri"] = d.source.map(PRIORITY).fillna(50)
    return d.sort_values(["entry_time","pri"]).reset_index(drop=True)

def simulate(price, events, mod, main, corr, shift, variant, cost_bps=7.5, risk_pct=.25):
    idx = price.index
    close=price.close.to_numpy(float); op=price.open.to_numpy(float)
    hi=price.high.to_numpy(float); lo=price.low.to_numpy(float)
    lookup={t:i for i,t in enumerate(idx)}
    events=events.copy()
    events["i"]=events.entry_time.map(lookup)
    events=events.dropna(subset=["i"])
    events["i"]=events["i"].astype(int)
    groups={int(i):g.sort_values("pri") for i,g in events.groupby("i")}
    realized=0.; peak=0.; maxdd=0.; worst_daily=0.
    active=[]; trades=[]; equity=[]; attempts=0; blocked=0
    trailing = variant in ("TL_TRAIL","COMBINED")
    filtering = variant in ("TL_FILTER","COMBINED")
    add_enabled = variant in ("TL_ADD","COMBINED")
    for i,t in enumerate(idx):
        # Exit before new entries: pessimistic SL if SL and TP both touched.
        keep=[]
        for pos in active:
            side=pos["side"]
            stop_hit=lo[i]<=pos["sl"] if side==1 else hi[i]>=pos["sl"]
            tp_hit=(hi[i]>=pos["tp"] if side==1 else lo[i]<=pos["tp"]) if pos["tp"] is not None else False
            reason=None; px=None
            if stop_hit:
                reason="SL";px=pos["sl"]
            elif tp_hit:
                reason="TP";px=pos["tp"]
            elif i-pos["i"]>=576:
                reason="TIME";px=close[i]
            if reason is not None:
                rr=side*(px-pos["entry"])/pos["risk"]-(cost_bps/10000)*pos["entry"]/pos["risk"]
                realized+=rr*risk_pct
                trades.append(dict(variant=variant,source=pos["source"],side=side,entry_time=pos["time"],exit_time=t,
                                   entry=pos["entry"],exit=px,exit_reason=reason,net_r=rr))
            else:
                keep.append(pos)
        active=keep
        # Trailing only after M5 completed bar, effective next bar, never widen SL.
        floating=0.
        for pos in active:
            floating += (pos["side"]*(close[i]-pos["entry"])/pos["risk"]-
                         (cost_bps/10000)*pos["entry"]/pos["risk"])*risk_pct
        eq=realized+floating
        peak=max(peak,eq);maxdd=max(maxdd,peak-eq)
        equity.append((t,eq))
        if i in groups:
            for _,r in groups[i].iterrows():
                attempts+=1
                side=int(r.side); source=str(r.source); atr=float(r.atr)
                if atr<=0 or not np.isfinite(atr):blocked+=1;continue
                if source=="TL_ADD" and not add_enabled:continue
                if filtering and source!="TL_ADD" and main_dir(mod,main,t,shift)!=side:
                    blocked+=1;continue
                if len(active)>=2:
                    blocked+=1;continue
                if active:
                    first=active[0]
                    mtm=first["side"]*(op[i]-first["entry"])/first["risk"]-(cost_bps/10000)*first["entry"]/first["risk"]
                    if side!=first["side"] or mtm<0:
                        blocked+=1;continue
                elif source=="TL_ADD":
                    blocked+=1;continue
                ent=op[i]; sl=ent-side*atr; risk=atr
                pos=dict(i=i,time=t,entry=ent,sl=sl,tp=None if trailing else ent+side*3*atr,
                         side=side,risk=risk,source=source,atr=atr)
                active.append(pos)
        if trailing and i+1<len(idx):
            for pos in active:
                candidate=line_stop(corr,t,pos["side"],shift,pos["entry"],pos["atr"])
                if candidate is not None:
                    # Tighten SL only and do not make a stop invalid on update.
                    if pos["side"]==1 and pos["sl"]<candidate<close[i]:
                        pos["sl"]=candidate
                    if pos["side"]==-1 and pos["sl"]>candidate>close[i]:
                        pos["sl"]=candidate
    q=pd.DataFrame(trades)
    if q.empty:
        return dict(variant=variant,n=0,net_r=0.,ev=np.nan,pf=np.nan,dd_pct=maxdd,attempts=attempts,blocked=blocked),q,pd.DataFrame(equity,columns=["time","equity_pct"])
    x=q.net_r.to_numpy(float); positive=x[x>0].sum();negative=-x[x<0].sum()
    months=(idx[-1].year-idx[0].year)*12+idx[-1].month-idx[0].month+1
    stat=dict(variant=variant,n=len(q),trades_month=len(q)/months,net_r=x.sum(),r_month=x.sum()/months,
              ev=x.mean(),pf=positive/negative if negative>0 else np.inf,dd_pct=maxdd,
              attempts=attempts,blocked=blocked)
    return stat,q,pd.DataFrame(equity,columns=["time","equity_pct"])

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--price",required=True,help="BTC M5 CSV or ZIP")
    a.add_argument("--raw-signals",required=True,help="RAW pre-portfolio signals: entry_time,side,atr,source")
    a.add_argument("--trendlines",required=True,help="trendlines.py")
    a.add_argument("--server-offset",type=float,default=0)
    a.add_argument("--cost-bps",type=float,default=7.5)
    a.add_argument("--out",default="lab253_out")
    args=a.parse_args()
    price=load_prices(args.price)
    raw=load_raw(args.raw_signals)
    mod,main_state,corr,cl,shift=load_tl(args.trendlines,price,args.server_offset)
    events=assemble_events(raw,cl,price,shift,None)
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    stats=[]; trade_parts=[]
    for v in VARIANTS:
        stat,t,eq=simulate(price,events,mod,main_state,corr,shift,v,args.cost_bps)
        stats.append(stat);trade_parts.append(t)
        eq.to_csv(out/f"equity_{v}.csv",index=False)
    pd.DataFrame(stats).to_csv(out/"summary.csv",index=False)
    pd.concat(trade_parts,ignore_index=True).to_csv(out/"trades.csv",index=False)
    cl.to_csv(out/"cl_breaks.csv",index=False)
    corr.to_csv(out/"correction_states.csv")
    (out/"metadata.json").write_text(json.dumps(dict(caveat="rough research replay; not EA MT5 parity",
        costs_bps=args.cost_bps,server_offset=args.server_offset,raw_input_rows=len(raw),
        corrections="No DST adjustment; no original EMA-retest shared cooldown; fixed 0.25% initial risk"),indent=2))
    print(pd.DataFrame(stats).to_string(index=False))

if __name__=="__main__":
    main()
