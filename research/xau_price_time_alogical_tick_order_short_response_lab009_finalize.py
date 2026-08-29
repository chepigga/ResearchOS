#!/usr/bin/env python3
"""Finalize LAB009 from saved exact-tick partial artifact without replaying raw ticks."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd


def args():
 p=argparse.ArgumentParser(); p.add_argument('--summary',type=Path,required=True); p.add_argument('--candidates',type=Path,required=True); p.add_argument('--outdir',type=Path,required=True); return p.parse_args()

def combine(g):
 n=int(g.n.sum()); sm=float(g.sum_R.sum()); gp=gl=0.0
 for _,r in g.iterrows():
  pf=float(r.pf); s=float(r.sum_R)
  if np.isfinite(pf) and abs(pf-1)>1e-12:
   loss=s/(pf-1); gp+=pf*loss; gl+=loss
  elif s>=0: gp+=s
  else: gl+=-s
 return {'n':n,'mean_R':sm/n if n else None,'pf':gp/gl if gl>0 else None,'win_rate':float(np.average(g.win_rate,weights=g.n)) if n else None,'tp_rate':float(np.average(g.tp_rate,weights=g.n)) if n else None,'sl_rate':float(np.average(g.sl_rate,weights=g.n)) if n else None,'sum_R':sm}

def main():
 a=args(); a.outdir.mkdir(parents=True,exist_ok=True); s=pd.read_csv(a.summary); c=pd.read_csv(a.candidates)
 rows=[]
 for cfg,g in s.groupby('config_id',sort=True):
  tr=combine(g[g.year.isin([2023,2024])]); va=combine(g[g.year.eq(2025)]); fi=combine(g[g.year.eq(2026)])
  row={'config_id':cfg}
  for pre,z in [('train',tr),('val',va),('final',fi)]: row.update({f'{pre}_{k}':v for k,v in z.items()})
  rows.append(row)
 m=c.merge(pd.DataFrame(rows),on='config_id',how='left')
 m['discovery_pass']=(m.train_n>=80)&(m.train_mean_R>=0.03)&(m.train_pf>=1.05)
 m['validation_pass']=(m.val_n>=30)&(m.val_mean_R>0)&(m.val_pf>1.0)
 m['locked_before_2026']=m.discovery_pass&m.validation_pass
 m['final_2026_pass']=(m.final_n>=20)&(m.final_mean_R>0)&(m.final_pf>1.0)
 m=m.sort_values(['locked_before_2026','train_mean_R','val_mean_R'],ascending=[False,False,False]); m.to_csv(a.outdir/'candidate_transfer_exact.csv',index=False)
 best=m.iloc[0]
 # Conservative diagnostic: all exact TPs could at most be TP-first members of the M1 ambiguous pool.
 train_upper_amb_tpfirst=float(best.train_tp_rate/best.train_ambiguous_rate) if best.train_ambiguous_rate>0 else None
 val_upper_amb_tpfirst=float(best.val_tp_rate/best.val_ambiguous_rate) if best.val_ambiguous_rate>0 else None
 out={'lab':'XAU_PRICE_TIME_ALOGICAL_TICK_ORDER_SHORT_RESPONSE_LAB_009','source':'saved exact tick replay from failed postprocess run 33245644124','m1_pre2026_candidate_configs':int(len(m)),'locked_configs_before_2026':int(m.locked_before_2026.sum()),'positive_train_configs':int((m.train_mean_R>0).sum()),'positive_validation_configs':int((m.val_mean_R>0).sum()),'positive_final_2026_configs':int((m.final_mean_R>0).sum()),'best_exact_config':{'config_id':str(best.config_id),'qreq_train':float(best.qreq_train),'qreq_val':float(best.qreq_val),'train_n':int(best.train_n),'train_tp_rate':float(best.train_tp_rate),'train_mean_R':float(best.train_mean_R),'train_pf':float(best.train_pf),'validation_n':int(best.val_n),'validation_tp_rate':float(best.val_tp_rate),'validation_mean_R':float(best.val_mean_R),'validation_pf':float(best.val_pf),'final_2026_n':int(best.final_n),'final_2026_tp_rate':float(best.final_tp_rate),'final_2026_mean_R':float(best.final_mean_R),'final_2026_pf':float(best.final_pf),'train_ambiguous_tpfirst_fraction_upper_bound':train_upper_amb_tpfirst,'validation_ambiguous_tpfirst_fraction_upper_bound':val_upper_amb_tpfirst},'verdict':'FAIL_TICK_ORDER_DECISIVE'}
 (a.outdir/'verdict.json').write_text(json.dumps(out,indent=2)); print(json.dumps(out,indent=2))
if __name__=='__main__': main()
