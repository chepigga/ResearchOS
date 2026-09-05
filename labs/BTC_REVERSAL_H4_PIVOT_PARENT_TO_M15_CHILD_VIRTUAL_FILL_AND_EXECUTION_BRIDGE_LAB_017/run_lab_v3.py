#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
SRC=HERE/"run_lab.py"
spec=importlib.util.spec_from_file_location("lab017_base",SRC)
L17=importlib.util.module_from_spec(spec); spec.loader.exec_module(L17)

LAB16_OUT=HERE.parent/"BTC_REVERSAL_ORTHOGONAL_H4_PARENT_AND_NONOVERLAP_FAMILY_LAB_016"/"output"
LAB15_OUT=HERE.parent/"BTC_REVERSAL_P975_T25_CONFIRMATION_AND_SECOND_PARENT_FAMILY_DISCOVERY_LAB_015"/"output"
T25=0.31308988842751206


def parse_time_cols(d):
    for c in ["event_time","fill_time","exit_time","signal_time","parent_time"]:
        if c in d.columns:
            d[c]=pd.to_datetime(d[c],utc=True,errors="coerce")
    for c in ["filled","vf1_mature","real_fill"]:
        if c in d.columns and d[c].dtype==object:
            d[c]=d[c].astype(str).str.lower().map({"true":True,"false":False}).fillna(False).astype(bool)
    return d


def load_frozen_parents(x):
    parents=parse_time_cols(pd.read_csv(LAB16_OUT/"H4_7D_PIVOT_SWEEP_RECLAIM_nonoverlap_selected.csv"))
    pre=parse_time_cols(pd.read_csv(LAB16_OUT/"H4_7D_PIVOT_SWEEP_RECLAIM_t25_pre_orthogonality.csv"))
    raw=parse_time_cols(pd.read_csv(LAB16_OUT/"H4_7D_PIVOT_SWEEP_RECLAIM_all_parents.csv"))
    canon=parse_time_cols(pd.read_csv(LAB15_OUT/"part_a_p975_t25_signal_stream.csv"))
    # Event identity is timestamp. Re-map persisted event timestamps to current L7 panel indices.
    pos=pd.Series(np.arange(len(x),dtype=int),index=x.index)
    idx=[]
    missing=[]
    for t in parents.event_time:
        if t not in pos.index:
            missing.append(str(t)); idx.append(-1)
        else:
            idx.append(int(pos.loc[t]))
    if missing:
        raise RuntimeError(f"Frozen LAB016 parent timestamps missing from L7 panel: {missing[:5]} total={len(missing)}")
    parents=parents.copy(); parents["event_i"]=idx
    # Hard lineage asserts from valid LAB016 v2 report/artifact.
    if len(parents)!=213: raise RuntimeError(f"Expected 213 frozen orthogonal pivot parents, got {len(parents)}")
    h2=((parents.event_time>=pd.Timestamp("2025-07-01",tz="UTC"))&(parents.event_time<pd.Timestamp("2026-01-01",tz="UTC"))).sum()
    y26=((parents.event_time>=pd.Timestamp("2026-01-01",tz="UTC"))&(parents.event_time<pd.Timestamp("2026-08-01",tz="UTC"))).sum()
    if int(h2)!=22 or int(y26)!=21:
        raise RuntimeError(f"Frozen recent parent parity failed: H2={h2}, 2026={y26}; expected 22/21")
    removed=len(pre)-len(parents)
    if removed!=81: raise RuntimeError(f"Expected 81 removed-by-orthogonality pivot parents, got {removed}")
    return parents,pre,raw,canon


def load_frozen_canonical_stream():
    d=parse_time_cols(pd.read_csv(LAB15_OUT/"part_a_p975_t25_signal_stream.csv"))
    for c in ["real_R","signal_net_R"]:
        if c in d.columns: d[c]=pd.to_numeric(d[c],errors="coerce").fillna(0.0)
    return d


def main():
    x,_,_=L17.L7.load_panel()
    parents,pre,raw,canon=load_frozen_parents(x)
    streams={}; tabs=[]; hist=[]
    for rule in L17.RULES:
        ch=L17.make_children(x,parents,rule)
        s=L17.execute_child_virtual(x,ch)
        streams[rule]=s
        tabs.append(L17.summarize_rule(rule,parents,s,L17.WINS))
        hist.append(L17.summarize_rule(rule,parents,s,L17.HIST_WINS))
        if len(s): s.to_csv(L17.OUT/f"stream_{rule.lower()}.csv",index=False)
    tab=pd.concat(tabs,ignore_index=True); htab=pd.concat(hist,ignore_index=True)
    canon_s=load_frozen_canonical_stream()
    union=L17.union_summary(canon_s,streams[L17.PRIMARY])
    v=L17.primary_verdict(tab,union)
    meta=dict(
        t25_cutoff=T25,
        raw_h4_parents=len(raw),
        t25_pre=len(pre),
        removed_24h=len(pre)-len(parents),
        orthogonal_parents=len(parents),
        canonical_stream_rows=len(canon_s),
        frozen_parent_artifact="LAB016/H4_7D_PIVOT_SWEEP_RECLAIM_nonoverlap_selected.csv",
        frozen_canonical_artifact="LAB015/part_a_p975_t25_signal_stream.csv",
        loader="L7.load_panel"
    )
    tab.to_csv(L17.OUT/"child_bridge_summary.csv",index=False)
    htab.to_csv(L17.OUT/"historical_summary.csv",index=False)
    union.to_csv(L17.OUT/"canonical_plus_child_union.csv",index=False)
    parents.to_csv(L17.OUT/"frozen_orthogonal_h4_parents.csv",index=False)
    (L17.OUT/"verdict.json").write_text(json.dumps({**v,"meta":meta},indent=2,allow_nan=True),encoding="utf-8")
    (L17.OUT/"REPORT.md").write_text(L17.report(tab,htab,union,v,meta),encoding="utf-8")
    print(json.dumps({**v,"meta":meta},indent=2)); print((L17.OUT/"REPORT.md").read_text())

if __name__=="__main__": main()
