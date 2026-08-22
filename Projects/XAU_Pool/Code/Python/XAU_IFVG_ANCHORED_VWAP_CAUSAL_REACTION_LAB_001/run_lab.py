#!/usr/bin/env python3
"""XAU_IFVG_ANCHORED_VWAP_CAUSAL_REACTION_LAB_001 v001.

Causal event study for confirmed inverse fair-value gaps (iFVG) conditioned on
an 18:00 New-York / 01:00 FTMO-platform anchored VWAP state.

Research status: experimental / preregistered. This is not an EA.
Default data embargo stops before 2025-07-01. Holdout requires an explicit flag.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

LAB = "XAU_IFVG_ANCHORED_VWAP_CAUSAL_REACTION_LAB_001"
VERSION = "v001"
CANONICAL_MEMBER = "XAUUSD_M1_20220601_20260723_TICK_NATIVE.csv"
CANONICAL_SHA256 = "db47a0cef1e666fdf27a67a23fcc290eee1bd2be2c651ecd8e080b99bf177b9b"
HOLDOUT_START = pd.Timestamp("2025-07-01 00:00:00")
DISCOVERY_END = pd.Timestamp("2024-01-01 00:00:00")
ANCHOR_HOUR_PLATFORM = 1
BAND_K = 1.618
NEAR_ATR = 0.10
SIDE_CLOSE_ATR = 0.03
RECOVERY_TOUCH_ATR = 0.05
ACCEPT_WINDOW = 5
ACCEPT_MIN = 4
RECOVERY_LOOKBACK = 15
IFVG_RETEST_MAX_MIN = 30
FVG_LIFETIME_MIN = 240
MIN_MINUTES_TO_ANCHOR = 60
RISK_ATR = 0.75
TARGET_R_VALUES = (1.5, 2.0)


@dataclass
class FVG:
    born: int
    side: int
    lower: float
    upper: float
    inverted: int | None = None


def _find_col(df: pd.DataFrame, names: Iterable[str]) -> str | None:
    lookup = {c.lower(): c for c in df.columns}
    for name in names:
        if name.lower() in lookup:
            return lookup[name.lower()]
    return None


def load_frame(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        df = pd.read_parquet(path)
    elif path.suffix.lower() == ".zip":
        df = pd.read_csv(path, compression="zip")
    else:
        df = pd.read_csv(path)

    aliases = {
        "time": ["time", "timestamp", "datetime", "date_time", "<date>"],
        "open": ["open", "bid_open", "<open>"],
        "high": ["high", "bid_high", "<high>"],
        "low": ["low", "bid_low", "<low>"],
        "close": ["close", "bid_close", "<close>"],
        "ask_high": ["ask_high", "high_ask"],
        "ask_low": ["ask_low", "low_ask"],
        "ask_close": ["ask_close", "close_ask"],
        "tick_volume": ["tick_volume", "tickvolume", "tick_vol", "ticks", "volume", "<tickvol>"],
        "spread_mean": ["spread_mean", "spread", "spread_price"],
    }
    out = pd.DataFrame()
    for dst, choices in aliases.items():
        src = _find_col(df, choices)
        if src is not None:
            out[dst] = df[src]

    required = ["time", "open", "high", "low", "close"]
    missing = [c for c in required if c not in out]
    if missing:
        raise ValueError(f"Missing required columns: {missing}; got {list(df.columns)}")

    out["time"] = pd.to_datetime(out["time"], errors="coerce")
    for c in out.columns:
        if c != "time":
            out[c] = pd.to_numeric(out[c], errors="coerce")
    out = out.dropna(subset=required).sort_values("time").drop_duplicates("time", keep="last").reset_index(drop=True)
    if (out.high < out.low).any():
        raise ValueError("OHLC integrity failure: high < low")
    return out


def wilder_atr(h: pd.Series, l: pd.Series, c: pd.Series, n: int = 14) -> pd.Series:
    pc = c.shift(1)
    tr = pd.concat([(h-l), (h-pc).abs(), (l-pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1/n, adjust=False, min_periods=n).mean()


def add_completed_m15_atr(df: pd.DataFrame) -> pd.DataFrame:
    x = df.set_index("time")
    m15 = x.resample("15min", label="left", closed="left").agg(
        open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last")
    ).dropna()
    m15["atr_m15"] = wilder_atr(m15.high, m15.low, m15.close, 14)
    avail = m15[["atr_m15"]].reset_index()
    avail["available_time"] = avail["time"] + pd.Timedelta(minutes=15)
    avail = avail[["available_time", "atr_m15"]].dropna().sort_values("available_time")
    out = pd.merge_asof(df.sort_values("time"), avail, left_on="time", right_on="available_time", direction="backward")
    return out.drop(columns=["available_time"], errors="ignore")


def session_key(t: pd.Series) -> pd.Series:
    return (t - pd.Timedelta(hours=ANCHOR_HOUR_PLATFORM)).dt.floor("D")


def add_anchor_lines(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["session_key"] = session_key(out.time)
    p = (out.high + out.low + out.close) / 3.0
    out["typical"] = p
    if "tick_volume" in out and out.tick_volume.notna().any() and (out.tick_volume.fillna(0) > 0).any():
        v = out.tick_volume.fillna(0).clip(lower=0)
        gv = v.groupby(out.session_key).cumsum()
        gpv = (p*v).groupby(out.session_key).cumsum()
        gp2v = ((p*p)*v).groupby(out.session_key).cumsum()
        vw = gpv / gv.replace(0, np.nan)
        var = (gp2v/gv.replace(0, np.nan) - vw*vw).clip(lower=0)
        sd = np.sqrt(var)
        out["vwap"] = vw
        out["vwap_sd"] = sd
        out["vwap_upper"] = vw + BAND_K*sd
        out["vwap_lower"] = vw - BAND_K*sd
    else:
        for c in ["vwap", "vwap_sd", "vwap_upper", "vwap_lower"]:
            out[c] = np.nan

    cnt = out.groupby("session_key").cumcount() + 1
    c1 = p.groupby(out.session_key).cumsum()
    c2 = (p*p).groupby(out.session_key).cumsum()
    mean = c1/cnt
    var = (c2/cnt - mean*mean).clip(lower=0)
    sd = np.sqrt(var)
    out["mean_anchor"] = mean
    out["mean_sd"] = sd
    out["mean_upper"] = mean + BAND_K*sd
    out["mean_lower"] = mean - BAND_K*sd
    return out


def build_ifvg_events(df: pd.DataFrame) -> pd.DataFrame:
    """Standard 3-candle FVG -> close through far edge -> first confirming retest."""
    h, l, c = df.high.to_numpy(float), df.low.to_numpy(float), df.close.to_numpy(float)
    n=len(df); rows=[]
    bull_idx=np.flatnonzero(l[2:] > h[:-2]) + 2
    bear_idx=np.flatnonzero(h[2:] < l[:-2]) + 2

    for born in bull_idx:
        lower=float(h[born-2]); upper=float(l[born])
        e=min(n, born+1+FVG_LIFETIME_MIN)
        inv_rel=np.flatnonzero(c[born+1:e] < lower)
        if not len(inv_rel): continue
        inv=born+1+int(inv_rel[0])
        r_end=min(n, inv+1+IFVG_RETEST_MAX_MIN)
        mask=(h[inv+1:r_end] >= lower) & (l[inv+1:r_end] <= upper) & (c[inv+1:r_end] < lower)
        rr=np.flatnonzero(mask)
        if len(rr):
            i=inv+1+int(rr[0]); rows.append((i,-1,int(born),int(inv),lower,upper))

    for born in bear_idx:
        lower=float(h[born]); upper=float(l[born-2])
        e=min(n, born+1+FVG_LIFETIME_MIN)
        inv_rel=np.flatnonzero(c[born+1:e] > upper)
        if not len(inv_rel): continue
        inv=born+1+int(inv_rel[0])
        r_end=min(n, inv+1+IFVG_RETEST_MAX_MIN)
        mask=(l[inv+1:r_end] <= upper) & (h[inv+1:r_end] >= lower) & (c[inv+1:r_end] > upper)
        rr=np.flatnonzero(mask)
        if len(rr):
            i=inv+1+int(rr[0]); rows.append((i,+1,int(born),int(inv),lower,upper))

    if not rows:
        return pd.DataFrame(columns=["i","dir","fvg_born_i","invert_i","gap_lower","gap_upper"])
    out=pd.DataFrame(rows,columns=["i","dir","fvg_born_i","invert_i","gap_lower","gap_upper"])
    out["gap_width"]=out.gap_upper-out.gap_lower
    out=out.sort_values(["i","dir","gap_width","fvg_born_i"]).drop_duplicates(["i","dir"],keep="first")
    return out.drop(columns="gap_width").reset_index(drop=True)


def _lines_for_kind(kind: str) -> tuple[str, str, str]:
    if kind == "VWAP_VOLUME":
        return "vwap", "vwap_upper", "vwap_lower"
    return "mean_anchor", "mean_upper", "mean_lower"


def classify_context(df: pd.DataFrame, events: pd.DataFrame, kind: str) -> pd.DataFrame:
    center_c, upper_c, lower_c = _lines_for_kind(kind)
    out = []
    for e in events.itertuples(index=False):
        i = int(e.i); d = int(e.dir)
        atr = float(df.at[i, "atr_m15"]) if np.isfinite(df.at[i, "atr_m15"]) else np.nan
        if not np.isfinite(atr) or atr <= 0:
            continue
        price = float(df.at[i, "close"])
        levels = {"CENTER": df.at[i, center_c], "UPPER": df.at[i, upper_c], "LOWER": df.at[i, lower_c]}
        levels = {k: float(v) for k,v in levels.items() if np.isfinite(v)}
        if not levels:
            continue
        nearest = min(levels, key=lambda k: abs(price-levels[k]))
        dist_atr = abs(price-levels[nearest])/atr
        near = dist_atr <= NEAR_ATR
        state = "FAR"
        if near:
            state = "NEAR"
            line_col = {"CENTER": center_c, "UPPER": upper_c, "LOWER": lower_c}[nearest]
            j0 = max(0, i-RECOVERY_LOOKBACK)
            hist = df.iloc[j0:i+1]
            lev = hist[line_col].to_numpy(float)
            closes = hist.close.to_numpy(float)
            highs = hist.high.to_numpy(float)
            lows = hist.low.to_numpy(float)
            atr_hist = hist.atr_m15.to_numpy(float)
            s = d*(closes-lev)/atr_hist
            accepted = False
            if len(s) >= ACCEPT_WINDOW + 3:
                pre = s[:-3]
                for k in range(max(0, len(pre)-10), len(pre)-ACCEPT_WINDOW+1):
                    w = pre[k:k+ACCEPT_WINDOW]
                    if np.isfinite(w).all() and (w > 0).sum() >= ACCEPT_MIN:
                        accepted = True
            tail = slice(max(0, len(hist)-3), len(hist))
            if d > 0:
                recovery_touch = np.any(lows[tail] <= lev[tail] + RECOVERY_TOUCH_ATR*atr_hist[tail])
            else:
                recovery_touch = np.any(highs[tail] >= lev[tail] - RECOVERY_TOUCH_ATR*atr_hist[tail])
            final_hold = np.isfinite(s[-1]) and s[-1] >= SIDE_CLOSE_ATR
            if accepted and recovery_touch and final_hold:
                state = "FAILED_RECOVERY"
            elif accepted and final_hold:
                state = "ACCEPT_HOLD"
            elif recovery_touch and final_hold:
                state = "REJECTION"
        out.append({**e._asdict(), "anchor_kind": kind, "level": nearest, "distance_atr": dist_atr, "state": state})
    return pd.DataFrame(out)


def next_anchor_time(t: pd.Timestamp) -> pd.Timestamp:
    base = t.normalize() + pd.Timedelta(hours=ANCHOR_HOUR_PLATFORM)
    if t >= base:
        return base + pd.Timedelta(days=1)
    return base


def simulate_outcomes(df: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    T = df.time.to_numpy(dtype="datetime64[ns]")
    bh, bl, bc = df.high.to_numpy(), df.low.to_numpy(), df.close.to_numpy()
    have_ask = all(c in df.columns for c in ["ask_high", "ask_low", "ask_close"])
    if have_ask:
        ah, al, ac = df.ask_high.to_numpy(), df.ask_low.to_numpy(), df.ask_close.to_numpy()
    else:
        ah, al, ac = bh, bl, bc
    rows = []
    for e in events.itertuples(index=False):
        i=int(e.i); d=int(e.dir); atr=float(df.at[i,"atr_m15"])
        if not np.isfinite(atr) or atr<=0: continue
        decision_t = pd.Timestamp(df.at[i,"time"])
        end_t = next_anchor_time(decision_t)
        mins_left = (end_t-decision_t).total_seconds()/60.0
        if mins_left < MIN_MINUTES_TO_ANCHOR: continue
        a=i+1
        b=int(np.searchsorted(T, np.datetime64(end_t), side="left"))
        if a>=b or a>=len(df): continue
        entry = float(df.at[i,"ask_close"]) if d>0 and "ask_close" in df else float(df.at[i,"close"])
        risk = RISK_ATR*atr
        base = e._asdict() | {"decision_time": decision_t, "entry": entry, "risk": risk,
                              "minutes_to_anchor": mins_left, "quote_side": bool(have_ask)}
        terminal = ((bc[b-1]-entry)/risk) if d>0 else ((entry-ac[b-1])/risk)
        for tr in TARGET_R_VALUES:
            tp = entry + d*tr*risk
            sl = entry - d*risk
            if d>0:
                hit_tp=np.flatnonzero(bh[a:b] >= tp); hit_sl=np.flatnonzero(bl[a:b] <= sl)
            else:
                hit_tp=np.flatnonzero(al[a:b] <= tp); hit_sl=np.flatnonzero(ah[a:b] >= sl)
            p=int(hit_tp[0]) if len(hit_tp) else 10**9
            q=int(hit_sl[0]) if len(hit_sl) else 10**9
            if p==q and p<10**9:
                outcome="AMBIGUOUS"; payoff=np.nan
            elif p<q:
                outcome="WIN"; payoff=tr
            elif q<p:
                outcome="LOSS"; payoff=-1.0
            else:
                outcome="NO_HIT"; payoff=float(np.clip(terminal,-1.0,tr))
            key=str(tr).replace('.', 'p')
            base[f"outcome_{key}"]=outcome
            base[f"R_{key}"]=payoff
        rows.append(base)
    return pd.DataFrame(rows)


def add_split(x: pd.DataFrame) -> pd.DataFrame:
    out=x.copy()
    t=pd.to_datetime(out.decision_time)
    out["split"]=np.where(t<DISCOVERY_END,"DISCOVERY",np.where(t<HOLDOUT_START,"CONFIRMATION","HOLDOUT"))
    out["week"]=(t-pd.to_timedelta(t.dt.weekday,unit="D")).dt.floor("D")
    return out


def summary_table(x: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    group_cols=["split","anchor_kind","state"]
    for keys,g in x.groupby(group_cols,dropna=False):
        row=dict(zip(group_cols,keys)); row["n"]=len(g)
        row["buy_n"]=(g.dir==1).sum(); row["sell_n"]=(g.dir==-1).sum()
        for tr in TARGET_R_VALUES:
            key=str(tr).replace('.', 'p'); o=g[f"outcome_{key}"]
            resolved=o.isin(["WIN","LOSS"])
            row[f"resolved_{key}"]=int(resolved.sum())
            row[f"win_rate_{key}"]=float((o[resolved]=="WIN").mean()) if resolved.any() else np.nan
            row[f"no_hit_rate_{key}"]=float((o=="NO_HIT").mean())
            row[f"ev_session_R_{key}"]=float(g[f"R_{key}"].mean())
        rows.append(row)
    return pd.DataFrame(rows).sort_values(group_cols).reset_index(drop=True)


def weekly_lift(x: pd.DataFrame, target_r: float=1.5) -> dict:
    key=str(target_r).replace('.', 'p'); col=f"R_{key}"
    v=x[(x.anchor_kind=="VWAP_VOLUME") & (x.state=="FAILED_RECOVERY") & (x.level=="CENTER")]
    f=x[(x.anchor_kind=="VWAP_VOLUME") & (x.state=="FAR")]
    a=v.groupby(["week","dir"])[col].mean().rename("sel")
    b=f.groupby(["week","dir"])[col].mean().rename("far")
    z=pd.concat([a,b],axis=1).dropna(); z["lift"]=z.sel-z.far
    if len(z)<8:
        return {"n_week_dir":int(len(z)),"mean_lift_R":np.nan,"ci95":[np.nan,np.nan]}
    rng=np.random.default_rng(20260822)
    vals=z.lift.to_numpy()
    boots=np.array([rng.choice(vals,size=len(vals),replace=True).mean() for _ in range(2000)])
    return {"n_week_dir":int(len(z)),"mean_lift_R":float(vals.mean()),
            "ci95":[float(np.quantile(boots,.025)),float(np.quantile(boots,.975))]}


def gates(x: pd.DataFrame) -> dict:
    conf=x[x.split=="CONFIRMATION"]
    sel=conf[(conf.anchor_kind=="VWAP_VOLUME")&(conf.state=="FAILED_RECOVERY")&(conf.level=="CENTER")]
    disc=x[(x.split=="DISCOVERY")&(x.anchor_kind=="VWAP_VOLUME")&(x.state=="FAILED_RECOVERY")&(x.level=="CENTER")]
    lift15=weekly_lift(conf,1.5); lift20=weekly_lift(conf,2.0)
    g={
        "G0_VOLUME_PROXY_PRESENT": bool((x.anchor_kind=="VWAP_VOLUME").any()),
        "G1_CONFIRMATION_POWER": bool(len(sel)>=150 and (sel.dir==1).sum()>=40 and (sel.dir==-1).sum()>=40),
        "G2_CONFIRMATION_EV_1P5_POSITIVE": bool(len(sel)>0 and sel.R_1p5.mean()>0),
        "G3_WEEK_CLUSTER_LIFT_1P5_CI_POSITIVE": bool(np.isfinite(lift15["ci95"][0]) and lift15["ci95"][0]>0),
        "G4_SPLIT_SIGN_1P5": bool(len(sel)>0 and len(disc)>0 and sel.R_1p5.mean()>0 and disc.R_1p5.mean()>0),
        "G5_2R_NOT_NEGATIVE": bool(len(sel)>0 and sel.R_2p0.mean()>=0),
    }
    place=conf[(conf.anchor_kind=="ANCHOR_MEAN")&(conf.state=="FAILED_RECOVERY")&(conf.level=="CENTER")]
    g["G6_VOLUME_ABLATION"] = bool(len(sel)>=50 and len(place)>=50 and sel.R_1p5.mean() >= place.R_1p5.mean())
    return {"gates":g,"lift_1p5":lift15,"lift_2p0":lift20,
            "selected_confirmation_n":int(len(sel)),
            "selected_confirmation_ev_1p5":float(sel.R_1p5.mean()) if len(sel) else None,
            "selected_confirmation_ev_2p0":float(sel.R_2p0.mean()) if len(sel) else None}


def run(path: Path, outdir: Path, open_holdout: bool=False) -> dict:
    df=load_frame(path)
    if not open_holdout:
        df=df[df.time < HOLDOUT_START].copy()
    df=add_completed_m15_atr(df)
    df=add_anchor_lines(df)
    ev=build_ifvg_events(df)
    if ev.empty:
        raise RuntimeError("No confirmed iFVG events detected")
    parts=[]
    for kind in ["VWAP_VOLUME","ANCHOR_MEAN"]:
        if kind=="VWAP_VOLUME" and df.vwap.isna().all():
            continue
        parts.append(classify_context(df,ev,kind))
    ctx=pd.concat(parts,ignore_index=True)
    res=simulate_outcomes(df,ctx)
    res=add_split(res)
    outdir.mkdir(parents=True,exist_ok=True)
    res.to_parquet(outdir/"events.parquet",index=False)
    summ=summary_table(res); summ.to_csv(outdir/"summary.csv",index=False)
    verdict=gates(res)
    audit={
        "lab":LAB,"version":VERSION,"input":str(path),"input_rows":int(len(df)),
        "period_start":str(df.time.min()),"period_end":str(df.time.max()),
        "canonical_expected_member":CANONICAL_MEMBER,"canonical_expected_sha256":CANONICAL_SHA256,
        "holdout_opened":bool(open_holdout),"ifvg_events":int(len(ev)),"context_rows":int(len(ctx)),
        "outcome_rows":int(len(res)),"volume_proxy_present":bool(not df.vwap.isna().all()),
        "quote_side_available":bool(all(c in df for c in ["ask_high","ask_low","ask_close"])),
        "anchor_platform_hour":ANCHOR_HOUR_PLATFORM,"band_k":BAND_K,
    }
    (outdir/"audit.json").write_text(json.dumps(audit,indent=2,default=str),encoding="utf-8")
    (outdir/"verdict.json").write_text(json.dumps(verdict,indent=2,default=str),encoding="utf-8")
    return {"audit":audit,"verdict":verdict,"summary":summ}


def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("input",type=Path,help="canonical XAU M1 parquet/csv/zip")
    ap.add_argument("--outdir",type=Path,default=Path("XAU_IFVG_ANCHORED_VWAP_CAUSAL_REACTION_LAB_001_v001"))
    ap.add_argument("--open-holdout",action="store_true",help="EXPLICIT one-time holdout read; do not use during internal work")
    args=ap.parse_args()
    r=run(args.input,args.outdir,args.open_holdout)
    print(json.dumps(r["audit"],indent=2,default=str))
    print(json.dumps(r["verdict"],indent=2,default=str))

if __name__=="__main__":
    main()
