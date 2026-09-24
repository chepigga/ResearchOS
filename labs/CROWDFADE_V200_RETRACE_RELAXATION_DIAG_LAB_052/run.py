from pathlib import Path
import io, zipfile, json, time
import numpy as np, pandas as pd
import requests

ROOT=Path("labs/CROWDFADE_V200_RETRACE_RELAXATION_DIAG_LAB_052")
DATA=ROOT/"data"; OUT=ROOT/"output"; OUT.mkdir(parents=True,exist_ok=True)
SETUPS=pd.read_csv(ROOT/"setups_2026-09-24.csv")
SERVER_UTC_OFFSET_H=3
CUTOFF_SERVER=pd.Timestamp("2026-09-24 22:44:00")
CUTOFF_UTC=CUTOFF_SERVER-pd.Timedelta(hours=SERVER_UTC_OFFSET_H)
TTL=pd.Timedelta(minutes=20)
VARIANTS={"R060":0.60,"R040":0.40,"R020":0.20,"R000":0.00}

def load_symbol(sym):
    # Current-day daily ZIP may not exist yet, so fetch the completed path directly
    # from the official Binance USD-M klines endpoint up to our frozen cutoff.
    start=int(pd.Timestamp("2026-09-24 00:00:00").timestamp()*1000)
    end=int(CUTOFF_UTC.timestamp()*1000)
    rows=[]; cur=start
    url="https://data-api.binance.vision/api/v3/klines"
    while cur<=end:
        resp=requests.get(url,params={"symbol":sym,"interval":"1m","startTime":cur,"endTime":end,"limit":1500},timeout=20)
        resp.raise_for_status()
        batch=resp.json()
        if not batch: break
        rows.extend(batch)
        nxt=int(batch[-1][0])+60000
        if nxt<=cur: break
        cur=nxt
        time.sleep(0.05)
    if not rows: raise RuntimeError(f"no Binance klines for {sym}")
    r=pd.DataFrame(rows)
    out=pd.DataFrame({
        "t":pd.to_datetime(pd.to_numeric(r.iloc[:,0],errors="coerce"),unit="ms",utc=True).dt.tz_localize(None),
        "o":pd.to_numeric(r.iloc[:,1],errors="coerce"),
        "h":pd.to_numeric(r.iloc[:,2],errors="coerce"),
        "l":pd.to_numeric(r.iloc[:,3],errors="coerce"),
        "c":pd.to_numeric(r.iloc[:,4],errors="coerce"),
    }).dropna().sort_values("t").drop_duplicates("t")
    return out.reset_index(drop=True)

PX={s:load_symbol(s) for s in sorted(SETUPS.symbol.unique())}

rows=[]
for sid,r in SETUPS.reset_index(drop=True).iterrows():
    sym=r.symbol; side=int(r.side); atr=float(r.atr); cref=float(r.confirm_ref)
    setup_server=pd.Timestamp(r.open_time_server)
    setup_utc=setup_server-pd.Timedelta(hours=SERVER_UTC_OFFSET_H)
    px=PX[sym].copy()
    # use the minute containing setup to anchor broker-vs-Binance basis
    minute=setup_utc.floor("min")
    anchor=px[px.t==minute]
    if anchor.empty:
        raise RuntimeError(f"no anchor {sym} {minute}")
    basis=cref-float(anchor.iloc[0].c)
    for col in ["o","h","l","c"]: px[col]=px[col]+basis

    for name,retrace in VARIANTS.items():
        entry=cref-side*retrace*atr
        sl=entry-side*4.5*atr
        tp=entry+side*10.0*atr

        if retrace==0.0:
            fill_time=setup_utc
            filled=True
        else:
            w=px[(px.t>=minute)&(px.t<=setup_utc+TTL)]
            if side>0:
                hits=w[w.l<=entry]
            else:
                hits=w[w.h>=entry]
            filled=not hits.empty
            fill_time=hits.iloc[0].t if filled else pd.NaT

        status="NO_FILL"; exit_time=pd.NaT; exit_px=np.nan; R=np.nan; mtm_R=np.nan; mfe_R=np.nan; mae_R=np.nan
        if filled:
            path=px[(px.t>=pd.Timestamp(fill_time).floor("min"))&(px.t<=CUTOFF_UTC.floor("min"))].copy()
            if path.empty:
                raise RuntimeError("empty post-fill path")
            risk=4.5*atr
            peak_fav=0.0; peak_adv=0.0
            status="OPEN"
            for _,b in path.iterrows():
                if side>0:
                    fav=max(0.0,float(b.h)-entry); adv=max(0.0,entry-float(b.l))
                    stop_hit=float(b.l)<=sl; tp_hit=float(b.h)>=tp
                else:
                    fav=max(0.0,entry-float(b.l)); adv=max(0.0,float(b.h)-entry)
                    stop_hit=float(b.h)>=sl; tp_hit=float(b.l)<=tp
                peak_fav=max(peak_fav,fav); peak_adv=max(peak_adv,adv)
                # conservative same-minute ordering: SL before TP
                if stop_hit:
                    status="SL"; exit_time=b.t; exit_px=sl; break
                if tp_hit:
                    status="TP"; exit_time=b.t; exit_px=tp; break
            mfe_R=peak_fav/risk; mae_R=peak_adv/risk
            if status in ("SL","TP"):
                R=side*(exit_px-entry)/risk
                mtm_R=R
            else:
                last=float(path.iloc[-1].c)
                mtm_R=side*(last-entry)/risk

        rows.append({
            "setup_id":sid+1,"setup_server":str(setup_server),"setup_utc":str(setup_utc),
            "symbol":sym,"side":"BUY" if side>0 else "SELL","actual_state":r.actual_state,
            "variant":name,"retrace_ATR":retrace,"atr":atr,"confirm_ref":cref,"basis":basis,
            "entry":entry,"sl":sl,"tp":tp,"filled":bool(filled),
            "fill_time_utc":None if pd.isna(fill_time) else str(fill_time),
            "status":status,"exit_time_utc":None if pd.isna(exit_time) else str(exit_time),
            "exit_px":exit_px,"R_realized":R,"R_mtm_cutoff":mtm_R,"MFE_R":mfe_R,"MAE_R":mae_R
        })

tr=pd.DataFrame(rows)
tr.to_csv(OUT/"trade_counterfactual.csv",index=False)

summary=[]
for name,g in tr.groupby("variant",sort=False):
    filled=g[g.filled]
    summary.append({
        "variant":name,
        "retrace_ATR":float(g.retrace_ATR.iloc[0]),
        "fills":int(g.filled.sum()),
        "fill_rate":float(g.filled.mean()),
        "SL":int((g.status=="SL").sum()),
        "TP":int((g.status=="TP").sum()),
        "OPEN":int((g.status=="OPEN").sum()),
        "NO_FILL":int((g.status=="NO_FILL").sum()),
        "sum_R_realized_closed":float(g.R_realized.fillna(0).sum()),
        "sum_R_mtm_cutoff_filled":float(g.R_mtm_cutoff.fillna(0).sum()),
        "mean_MFE_R_filled":float(filled.MFE_R.mean()) if len(filled) else None,
        "mean_MAE_R_filled":float(filled.MAE_R.mean()) if len(filled) else None,
    })
sm=pd.DataFrame(summary)
base=float(sm.loc[sm.variant=="R060","sum_R_mtm_cutoff_filled"].iloc[0])
sm["delta_R_mtm_vs_R060"]=sm.sum_R_mtm_cutoff_filled-base
sm.to_csv(OUT/"summary.csv",index=False)

actual_expected=SETUPS.actual_state.eq("filled").sum()
proxy_fills=int(sm.loc[sm.variant=="R060","fills"].iloc[0])
out={
 "lab":"CROWDFADE_V200_RETRACE_RELAXATION_DIAG_LAB_052",
 "cutoff_server":str(CUTOFF_SERVER),"server_utc_offset_h":SERVER_UTC_OFFSET_H,
 "actual_report_fills_R060":int(actual_expected),
 "proxy_fills_R060":proxy_fills,
 "proxy_fill_parity":proxy_fills==int(actual_expected),
 "summary":summary,
 "note":"One-day diagnostic only; not sufficient to change V200 production parameters."
}
(OUT/"summary.json").write_text(json.dumps(out,indent=2))
print(sm.to_string(index=False))
print(json.dumps(out,indent=2))
