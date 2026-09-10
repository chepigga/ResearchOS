#!/usr/bin/env python3
# Computation-only split of preregistered LAB062. No research logic/gates changed.
import importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('lab062',HERE/'run_lab.py'); M=importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
OUT=M.OUT

f22,h41,r43=M.load_sources()
src_start=f22.signal_time.min(); src_end=f22.signal_time.max(); raw_start=src_start-M.FLOW_LOOKBACK-pd.Timedelta(days=5); fut_start=raw_start-pd.Timedelta(days=35); fut_end=src_end+pd.Timedelta(hours=12)
print('CORE source',src_start,src_end,flush=True)
m=M.download_metrics(raw_start,src_end); print('CORE metrics',len(m),flush=True)
fut=M.download_futures(fut_start,fut_end); M.FUT_GLOBAL=fut; print('CORE futures',len(fut),flush=True)
scan_start=max(src_start,m.index.min()+M.FLOW_LOOKBACK); scan_end=min(src_end,fut.index.max()-pd.Timedelta(hours=12))
base_all=M.build_frozen_flow(m,fut,scan_start-pd.Timedelta(hours=24),scan_end); base_all=base_all[base_all.signal_time>=scan_start].reset_index(drop=True)
persisted=f22[(f22.signal_time>=scan_start)&(f22.signal_time<=scan_end)][['signal_time','side']].copy(); parity=M.union_match(persisted,base_all)
base_short=base_all[base_all.side==-1].copy(); onset=M.build_onsets(m,fut,scan_start,scan_end)
print('CORE candidates base/onset',len(base_short),len(onset),'parity',parity,flush=True)
a_base=M.classify_frozen_router(M.activation(base_short,fut),h41); print('CORE base activation',len(a_base),flush=True)
a_fr=M.classify_frozen_router(M.activation(onset,fut),h41); print('CORE onset frozen',len(a_fr),flush=True)
a_nat=M.classify_native_router(M.activation(onset,fut)); print('CORE onset native',len(a_nat),flush=True)
cmp=a_base[['signal_time','state','response_router']].merge(r43[r43.side==-1][['signal_time','state','response_router']],on='signal_time',suffixes=('_new','_persisted'))
router_match=float(((cmp.state_new.astype(str)==cmp.state_persisted.astype(str))&(cmp.response_router_new.astype(str)==cmp.response_router_persisted.astype(str))).mean()) if len(cmp) else np.nan
parity['router_overlap_n']=int(len(cmp));parity['router_state_match']=router_match
ex_base=pd.DataFrame([M.simulate(r,fut) for r in a_base.itertuples(index=False)]); print('CORE sim base',flush=True)
ex_fr=pd.DataFrame([M.simulate(r,fut) for r in a_fr.itertuples(index=False)]); print('CORE sim fr',flush=True)
ex_nat=pd.DataFrame([M.simulate(r,fut) for r in a_nat.itertuples(index=False)]); print('CORE sim nat',flush=True)
full_start=scan_start;full_end=scan_end;conf_start=max(pd.Timestamp('2025-01-01',tz='UTC'),full_start)
sm=[];yrs=[]
for name,a,ex in [('FROZEN_FIRST_HIT_12H',a_base,ex_base),('SHORT_RUN_ONSET_FROZEN_ROUTER',a_fr,ex_fr),('SHORT_RUN_ONSET_NATIVE_ROUTER',a_nat,ex_nat)]:
    sm.append({**M.summarize(name,a,ex,full_start,full_end),'slice':'FULL'});sm.append({**M.summarize(name,a,ex,conf_start,full_end),'slice':'2025_PLUS_REUSED'});yrs.append(M.yearly(name,ex,full_start,full_end))
sm=pd.DataFrame(sm);sm.to_csv(OUT/'summary_core.csv',index=False);ydf=pd.concat(yrs,ignore_index=True);ydf.to_csv(OUT/'yearly_core.csv',index=False)
print('CORE fragility',flush=True);frag=M.fragility(m,base_all,scan_start,scan_end);frag.to_csv(OUT/'first_hit_single_state_deletion_fragility_core.csv',index=False)
fragmetrics={'n':int(len(frag)),'alter_ge1_share':float(frag.changes_ge1.mean()) if len(frag) else np.nan,'alter_ge2_share':float(frag.changes_ge2.mean()) if len(frag) else np.nan,'changed_event_count_72h':M.qstats(frag.changed_event_count_72h if len(frag) else []),'resync_hours':M.qstats(frag.resync_hours if len(frag) else [])}
def row(sel):
    q=sm[(sm.selector==sel)&(sm['slice']=='2025_PLUS_REUSED')];return None if q.empty else q.iloc[0]
rb=row('FROZEN_FIRST_HIT_12H');rf=row('SHORT_RUN_ONSET_FROZEN_ROUTER');rn=row('SHORT_RUN_ONSET_NATIVE_ROUTER')
yfull=ydf.groupby('selector').apply(lambda g: float((g.ev5>0).mean()) if len(g) else np.nan,include_groups=False).to_dict()
b_ratio=(float(rf.ev_5bps)/float(rb.ev_5bps)) if rb is not None and np.isfinite(rb.ev_5bps) and rb.ev_5bps>0 else np.nan;n_ratio=(float(rn.ev_5bps)/float(rb.ev_5bps)) if rn is not None and rb is not None and np.isfinite(rb.ev_5bps) and rb.ev_5bps>0 else np.nan
b={'n_ge30':bool(rf is not None and rf.accept_trade_n>=30),'ev5_gt0':bool(rf is not None and rf.ev_5bps>0),'pf5_ge1_20':bool(rf is not None and rf.pf_5bps>=1.20),'ev10_gt0':bool(rf is not None and rf.ev_10bps>0),'dd025_le4':bool(rf is not None and rf.dd_pct_025<=4),'ev5_ge70pct_baseline':bool(np.isfinite(b_ratio) and b_ratio>=.70),'positive_year_share_ge60':bool(yfull.get('SHORT_RUN_ONSET_FROZEN_ROUTER',0)>=.60),'max_concurrent_le4':bool(rf is not None and rf.max_concurrent<=4)}
n={'n_ge30':bool(rn is not None and rn.accept_trade_n>=30),'ev5_gt0':bool(rn is not None and rn.ev_5bps>0),'pf5_ge1_20':bool(rn is not None and rn.pf_5bps>=1.20),'ev10_gt0':bool(rn is not None and rn.ev_10bps>0),'dd025_le4':bool(rn is not None and rn.dd_pct_025<=4),'ev5_ge60pct_baseline':bool(np.isfinite(n_ratio) and n_ratio>=.60),'positive_year_share_ge60':bool(yfull.get('SHORT_RUN_ONSET_NATIVE_ROUTER',0)>=.60),'max_concurrent_le4':bool(rn is not None and rn.max_concurrent<=4)}
baseline_ok=parity['union_match']>=.995 and (pd.isna(router_match) or router_match>=.995)
if not baseline_ok:v='FAIL_BASELINE_REPLICATION'
elif rf is None or rf.accept_trade_n<30:v='INSUFFICIENT_DATA'
elif all(b.values()) and all(n.values()):v='CLOCK_FREE_NATIVE_SUPPORTED'
elif all(b.values()):v='CLOCK_FREE_EQUIVALENT_SUPPORTED'
elif rf.ev_5bps<=0 or rf.pf_5bps<1 or rf.dd_pct_025>4:v='CLOCK_IS_ECONOMICALLY_MATERIAL'
else:v='WATCH_CLOCK_FREE_PROMISING_NOT_EQUIVALENT'
metrics={'lab':M.LAB,'runner':'CORE_SPLIT_SAME_PREREG','formal_range':[scan_start,scan_end],'baseline_parity':parity,'information_fragility':fragmetrics,'positive_year_share':yfull,'frozen_router_2025':None if rb is None else rb.to_dict(),'onset_frozen_router_2025':None if rf is None else rf.to_dict(),'onset_native_router_2025':None if rn is None else rn.to_dict(),'onset_frozen_ev_ratio_to_baseline':b_ratio,'onset_native_ev_ratio_to_baseline':n_ratio,'frozen_router_gates':b,'native_router_gates':n,'verdict':v,'frozen_short_v1_changed':False,'live_allocation':0,'no_tuning':True}
(OUT/'metrics_core.json').write_text(json.dumps(M.j(metrics),indent=2));print(json.dumps(M.j(metrics),indent=2),flush=True)
