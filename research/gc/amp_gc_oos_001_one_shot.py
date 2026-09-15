#!/usr/bin/env python3
"""AMP_GC_OOS_001 — ONE-SHOT UNTOUCHED REPLICATION

This script applies the frozen GC AEIF signal/transfer rules to AMP_GC_OOS_001.
It is intentionally NOT an optimizer and exposes no strategy parameters.

PRE-REGISTERED BRIDGE CHOICE BEFORE RUN:
AMP prints carrying BOTH BUY and SELL flags are excluded from directional
aggressor volume. Rationale: canonical Rithmic aggressor is mutually exclusive
BUY or SELL. This uses the already-exported *_only columns and is not selected
from AMP performance.

Historical branch distinction preserved:
- 30m cooldown is evaluated as the frozen historical baseline diagnostic branch.
- confirmation/GC->XAU transfer is built from all frozen CORE events, matching
  the historical 105 -> 61 confirmation lineage and 53 -> 51 XAU mapping.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("research/gc")
AMP = ROOT / "AMP_GC_OOS_001_M5_FOOTPRINT.csv"
AMP_MANIFEST = ROOT / "AMP_GC_OOS_001_MANIFEST.json"
RITH_CORE = ROOT / "RITHMIC_AEIF_FROZEN_RECONSTRUCTION_001_CORE_EVENTS.csv"
RITH_CONF = ROOT / "RITHMIC_AEIF_FROZEN_RECONSTRUCTION_001_CONFIRMED_EVENTS.csv"
XAU = Path("XAUUSD_M1_2026.csv")

OUT_CORE = ROOT / "AMP_GC_OOS_001_CORE_EVENTS.csv"
OUT_CONF = ROOT / "AMP_GC_OOS_001_CONFIRMED_EVENTS.csv"
OUT_REPORT = ROOT / "AMP_GC_OOS_001_ONE_SHOT_REPORT.md"
OUT_JSON = ROOT / "AMP_GC_OOS_001_ONE_SHOT_RESULT.json"

M5 = pd.Timedelta(minutes=5)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def build_amp_bars() -> pd.DataFrame:
    manifest = json.loads(AMP_MANIFEST.read_text(encoding="utf-8"))
    expected = manifest["m5_footprint_sha256"]
    got = sha256_file(AMP)
    if got != expected:
        raise SystemExit(f"AMP footprint SHA mismatch: {got} != {expected}")

    b = pd.read_csv(AMP)
    required = {
        "bar_start_msc","open","high","low","close","true_range",
        "buy_only_volume","sell_only_volume","delta_exclusive",
        "delta_frac_exclusive","sell_only_concentration_lower20",
        "buy_only_concentration_upper20"
    }
    missing = required - set(b.columns)
    if missing:
        raise SystemExit(f"AMP footprint missing columns: {sorted(missing)}")

    b["bar"] = pd.to_datetime(b.bar_start_msc.astype("int64"), unit="ms", utc=True)
    b = b.sort_values("bar", kind="mergesort").reset_index(drop=True)

    # Frozen aggressor bridge: exclusive-only directional side semantics.
    b["buy_vol"] = b.buy_only_volume.astype(float)
    b["sell_vol"] = b.sell_only_volume.astype(float)
    b["delta"] = b.delta_exclusive.astype(float)
    den = b.buy_vol + b.sell_vol
    b["delta_frac"] = np.where(den > 0, b.delta / den, 0.0)
    b["sell_loc"] = b.sell_only_concentration_lower20.astype(float)
    b["buy_loc"] = b.buy_only_concentration_upper20.astype(float)

    # Match canonical Rithmic ATR implementation exactly.
    tr = b.true_range.astype(float).copy()
    if len(tr):
        tr.iloc[0] = np.nan
    b["atr14_wilder"] = tr.ewm(alpha=1/14, adjust=False, min_periods=14).mean()

    # Frozen prior-240 completed traded M5-bar references; current bar excluded.
    b["q10_prior240"] = b.delta_frac.shift(1).rolling(240, min_periods=240).quantile(0.10)
    b["q90_prior240"] = b.delta_frac.shift(1).rolling(240, min_periods=240).quantile(0.90)
    b["q75_sell_loc_prior240"] = b.sell_loc.shift(1).rolling(240, min_periods=240).quantile(0.75)
    b["q75_buy_loc_prior240"] = b.buy_loc.shift(1).rolling(240, min_periods=240).quantile(0.75)

    b["dn_eff"] = (b.open - b.close).clip(lower=0) / b.atr14_wilder
    b["up_eff"] = (b.close - b.open).clip(lower=0) / b.atr14_wilder
    return b


def build_core(b: pd.DataFrame) -> pd.DataFrame:
    lm = (
        (b.delta_frac <= b.q10_prior240)
        & (b.sell_loc >= b.q75_sell_loc_prior240)
        & (b.dn_eff <= 0.15)
    )
    sm = (
        (b.delta_frac >= b.q90_prior240)
        & (b.buy_loc >= b.q75_buy_loc_prior240)
        & (b.up_eff <= 0.15)
    )
    if bool((lm & sm).any()):
        raise SystemExit("Unexpected simultaneous LONG and SHORT core on same AMP bar")

    s = b.loc[lm | sm].copy()
    s["side"] = np.where(lm[lm | sm].to_numpy(), "LONG", "SHORT")
    s["directional_impact_atr"] = np.where(s.side.eq("LONG"), s.dn_eff, s.up_eff)

    keep=[]; last=None
    for t in s.bar:
        ok = last is None or t-last >= pd.Timedelta(minutes=30)
        keep.append(int(ok))
        if ok: last=t
    s["cooldown30_keep"] = keep

    out = pd.DataFrame({
        "core_bar_utc": s.bar.map(lambda x:x.isoformat()),
        "side": s.side,
        "open":s.open,"high":s.high,"low":s.low,"close":s.close,
        "atr14_wilder":s.atr14_wilder,
        "delta_frac":s.delta_frac,
        "q10_prior240":s.q10_prior240,"q90_prior240":s.q90_prior240,
        "sell_loc":s.sell_loc,"q75_sell_loc_prior240":s.q75_sell_loc_prior240,
        "buy_loc":s.buy_loc,"q75_buy_loc_prior240":s.q75_buy_loc_prior240,
        "directional_impact_atr":s.directional_impact_atr,
        "cooldown30_keep":s.cooldown30_keep.astype(int),
    })
    return out


def build_confirmations(b: pd.DataFrame, core: pd.DataFrame) -> pd.DataFrame:
    idx = {t:i for i,t in enumerate(b.bar)}
    rows=[]
    for e in core.itertuples(index=False):
        ct=pd.Timestamp(e.core_bar_utc)
        i=idx[ct]
        for off in (1,2):
            if i+off >= len(b): break
            c=b.iloc[i+off]
            # Never jump across a missing clock M5 bar.
            if c.bar != ct + off*M5: break
            ok=(e.side=="LONG" and c.close>c.open and c.delta>0) or \
               (e.side=="SHORT" and c.close<c.open and c.delta<0)
            if ok:
                rows.append({
                    "core_bar_utc":ct.isoformat(),"side":e.side,
                    "confirm_bar_utc":c.bar.isoformat(),"confirm_offset_bars":off,
                    "confirm_open":float(c.open),"confirm_close":float(c.close),
                    "confirm_delta":float(c.delta),
                    "entry_eligible_utc":(c.bar+M5).isoformat(),
                })
                break
    return pd.DataFrame(rows)


def event_set(df: pd.DataFrame, time_col: str) -> set[tuple[str,str]]:
    if len(df)==0: return set()
    t=pd.to_datetime(df[time_col],utc=True)
    return set(zip(t.map(lambda x:x.isoformat()), df.side.astype(str)))


def parity(candidate: pd.DataFrame, reference: pd.DataFrame, c_time: str, r_time: str,
           start: pd.Timestamp, end: pd.Timestamp) -> dict:
    c=candidate.copy(); r=reference.copy()
    ct=pd.to_datetime(c[c_time],utc=True); rt=pd.to_datetime(r[r_time],utc=True)
    c=c.loc[(ct>=start)&(ct<=end)].copy()
    r=r.loc[(rt>=start)&(rt<=end)].copy()
    cs=event_set(c,c_time); rs=event_set(r,r_time)
    inter=cs&rs; union=cs|rs
    return {
        "window_start":start.isoformat(),"window_end":end.isoformat(),
        "amp_n":len(cs),"rithmic_n":len(rs),"matched":len(inter),
        "amp_only":len(cs-rs),"rithmic_only":len(rs-cs),
        "jaccard": (len(inter)/len(union) if union else 1.0),
        "exact_set_match": cs==rs,
        "amp_only_events":[{"time":t,"side":s} for t,s in sorted(cs-rs)],
        "rithmic_only_events":[{"time":t,"side":s} for t,s in sorted(rs-cs)],
    }


def read_xau() -> pd.DataFrame | None:
    if not XAU.exists(): return None
    x=pd.read_csv(XAU,sep=';')
    x["file_time"]=pd.to_datetime(x["time"],format="%Y.%m.%d %H:%M")
    return x.sort_values("file_time").reset_index(drop=True)


def map_xau(conf: pd.DataFrame, xau: pd.DataFrame | None) -> tuple[pd.DataFrame,dict]:
    c=conf.copy()
    if xau is None or not len(c):
        return c,{"available":False}
    times=set(xau.file_time)
    xmin=xau.file_time.iloc[0]; xmax=xau.file_time.iloc[-1]
    eligible=pd.to_datetime(c.entry_eligible_utc,utc=True)
    c["xau_target_file_time"]=(eligible.dt.tz_convert(None)+pd.Timedelta(hours=2))
    c["xau_history_in_range"]=(c.xau_target_file_time>=xmin)&(c.xau_target_file_time<=xmax)
    c["xau_exact_timestamp_eligible"]=c.xau_target_file_time.isin(times) & c.xau_history_in_range
    inr=c[c.xau_history_in_range]
    ex=inr[inr.xau_exact_timestamp_eligible]
    return c,{
        "available":True,"xau_rows":len(xau),"xau_min_file_clock":str(xmin),"xau_max_file_clock":str(xmax),
        "candidate_confirmations_in_xau_history_range":int(len(inr)),
        "exact_timestamp_transfers":int(len(ex)),
        "exact_long":int((ex.side=="LONG").sum()),"exact_short":int((ex.side=="SHORT").sum()),
        "missing_exact_timestamp":int((~inr.xau_exact_timestamp_eligible).sum()),
    }


def main() -> None:
    b=build_amp_bars()
    core=build_core(b)
    conf=build_confirmations(b,core)
    core.to_csv(OUT_CORE,index=False)
    conf_mapped,xau_stats=map_xau(conf,read_xau())
    conf_mapped.to_csv(OUT_CONF,index=False)

    first_valid=b.loc[b.q10_prior240.notna(),"bar"].iloc[0]
    amp_end=b.bar.iloc[-1]

    rc=pd.read_csv(RITH_CORE); rf=pd.read_csv(RITH_CONF)
    r_core_times=pd.to_datetime(rc.core_bar_utc,utc=True)
    r_conf_times=pd.to_datetime(rf.core_bar_utc,utc=True)
    r_end=max(r_core_times.max(),r_conf_times.max())
    overlap_end=min(amp_end,r_end)

    core_par=parity(core,rc,"core_bar_utc","core_bar_utc",first_valid,overlap_end)
    conf_par=parity(conf,rf,"core_bar_utc","core_bar_utc",first_valid,overlap_end)

    result={
        "lab":"AMP_GC_OOS_001_ONE_SHOT",
        "status":"COMPLETED_UNTOUCHED",
        "strategy_parameters_optimized":False,
        "amp_footprint_sha256":sha256_file(AMP),
        "bridge_policy":"EXCLUSIVE_SIDE_ONLY; BOTH BUY+SELL prints excluded from directional aggressor volume",
        "amp_bars":int(len(b)),
        "amp_first_bar":b.bar.iloc[0].isoformat(),"amp_last_bar":amp_end.isoformat(),
        "valid_after_240bar_warmup":first_valid.isoformat(),
        "core":{"n":int(len(core)),"long":int((core.side=='LONG').sum()),"short":int((core.side=='SHORT').sum()),
                "cooldown30_kept":int(core.cooldown30_keep.sum())},
        "confirmation":{"n":int(len(conf)),"long":int((conf.side=='LONG').sum()),"short":int((conf.side=='SHORT').sum())},
        "same_date_rithmic_core_parity":core_par,
        "same_date_rithmic_confirmation_parity":conf_par,
        "historical_xau_mapping":xau_stats,
        "note":"XAU historical file ends 2026-09-08 file clock; later AMP confirmations are not scored as failed transfers.",
    }
    OUT_JSON.write_text(json.dumps(result,indent=2,sort_keys=True),encoding='utf-8')

    verdict = "EXACT_FEED_SIGNAL_PARITY" if core_par['exact_set_match'] and conf_par['exact_set_match'] else "FEED_SIGNAL_DIVERGENCE"
    lines=[
        "# AMP_GC_OOS_001 — ONE-SHOT UNTOUCHED REPLICATION",
        "",f"## Verdict: **{verdict}**","",
        "No parameter sweep, threshold change, session filter, or AMP-performance-based selection was performed.","",
        f"- AMP M5 bars: **{len(b):,}**",
        f"- evaluation starts after frozen 240-bar warmup: **{first_valid.isoformat()}**",
        f"- AMP CORE: **{len(core)} = {(core.side=='LONG').sum()} LONG / {(core.side=='SHORT').sum()} SHORT**",
        f"- 30m cooldown baseline branch kept: **{int(core.cooldown30_keep.sum())}**",
        f"- AMP confirmations: **{len(conf)} = {(conf.side=='LONG').sum()} LONG / {(conf.side=='SHORT').sum()} SHORT**",
        "",
        "## Same-date Rithmic source-parity window", "",
        f"Window: `{first_valid.isoformat()}` → `{overlap_end.isoformat()}`",
        f"- CORE: AMP **{core_par['amp_n']}**, Rithmic **{core_par['rithmic_n']}**, matched **{core_par['matched']}**, AMP-only **{core_par['amp_only']}**, Rithmic-only **{core_par['rithmic_only']}**, Jaccard **{core_par['jaccard']:.4f}**",
        f"- Confirmation: AMP **{conf_par['amp_n']}**, Rithmic **{conf_par['rithmic_n']}**, matched **{conf_par['matched']}**, AMP-only **{conf_par['amp_only']}**, Rithmic-only **{conf_par['rithmic_only']}**, Jaccard **{conf_par['jaccard']:.4f}**",
        "",
        "## Historical XAU timestamp mapping (coverage-limited)","",
    ]
    if xau_stats.get('available'):
        lines += [
            f"XAU history: `{xau_stats['xau_min_file_clock']}` → `{xau_stats['xau_max_file_clock']}` file clock (UTC+2 mapping).",
            f"- AMP confirmations whose scheduled XAU time is inside available history: **{xau_stats['candidate_confirmations_in_xau_history_range']}**",
            f"- exact-timestamp eligible transfers: **{xau_stats['exact_timestamp_transfers']} = {xau_stats['exact_long']} LONG / {xau_stats['exact_short']} SHORT**",
            f"- missing exact XAU timestamp inside available history: **{xau_stats['missing_exact_timestamp']}**",
        ]
    lines += ["","## Frozen bridge implementation","",
              "AMP mixed BUY+SELL prints are excluded from directional aggressor volume to preserve mutually-exclusive Rithmic aggressor semantics. This choice was preregistered before the run.",
              "","The 30-minute cooldown and confirmation-transfer path are reported as separate historical branches: confirmation is generated from frozen CORE directly, matching the historical 105→61 lineage; cooldown remains the frozen 105→92 baseline diagnostic branch.",
              "","No later XAU confirmations are treated as failures merely because the release XAU file ends on September 8."]
    OUT_REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(OUT_REPORT.read_text(encoding='utf-8'))
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__ == '__main__':
    main()
