#!/usr/bin/env python3
# Parity/accounting-only fix: preserve frozen LAB030 rules, include failures at original +12h as terminal NO_REACCEPT.
import importlib.util, json
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('L',HERE/'run_lab.py')
L=importlib.util.module_from_spec(spec); spec.loader.exec_module(L)

def simulate_v2(price,d):
    pos=pd.Series(np.arange(len(price),dtype=int),index=price.index)
    rows=[]
    for r in d.itertuples():
        if not bool(r.origin_close2_trigger) or pd.isna(r.origin_close2_time):continue
        sig_t=pd.Timestamp(r.signal_time); fail_t=pd.Timestamp(r.origin_close2_time); end_t=sig_t+pd.Timedelta(hours=12)
        if fail_t not in pos.index or end_t not in pos.index or fail_t>end_t:continue
        side=int(r.side); sig=float(r.signal_close); entry=float(r.entry); atr=float(r.atr14)
        if not np.isfinite(atr) or atr<=0:continue
        fail_close=float(price.loc[fail_t,'close']); end_close=float(price.loc[end_t,'close'])
        rec_t=pd.NaT; rec_px=np.nan; rea_t=pd.NaT; rea_px=np.nan; adv=[]; fav=[]; extra_bad=0
        if fail_t<end_t:
            i=int(pos.loc[fail_t])+1
            if i<len(price):
                start=price.index[i]; path=price.loc[(price.index>=start)&(price.index<=end_t)]
                if len(path):
                    rec_t,rec_px=L.first_close(path,side,sig); rea_t,rea_px=L.first_close(path,side,entry)
                    for t,z in path.iterrows():
                        a=max(0.0,fail_close-float(z.low)) if side>0 else max(0.0,float(z.high)-fail_close)
                        f=max(0.0,float(z.high)-fail_close) if side>0 else max(0.0,fail_close-float(z.low))
                        adv.append(a/atr); fav.append(f/atr)
                    for t,z in path.iterrows():
                        if pd.notna(rea_t) and t>rea_t:break
                        if side*(float(z.close)-sig)<=0:extra_bad+=1
        origin_reclaim=bool(pd.notna(rec_t)); full_reaccept=bool(pd.notna(rea_t))
        if full_reaccept and origin_reclaim and rea_t<rec_t:raise RuntimeError('geometry error')
        reaccept_resid=float(side*(end_close-rea_px)/atr) if full_reaccept else np.nan
        failure_to_end=float(side*(end_close-fail_close)/atr)
        origin_reclaim_resid=float(side*(end_close-rec_px)/atr) if origin_reclaim else np.nan
        reentry_net=float(reaccept_resid-(rea_px*(L.COST_BPS/10000.0))/atr) if full_reaccept else np.nan
        rows.append(dict(flow_id=int(r.flow_id),signal_time=sig_t,side=side,signal_close=sig,entry=entry,atr14=atr,
          failure_time=fail_t,failure_close=fail_close,origin_reclaim=origin_reclaim,origin_reclaim_time=rec_t,
          full_reaccept=full_reaccept,full_reaccept_time=rea_t,
          origin_reclaim_h=float((rec_t-fail_t).total_seconds()/3600) if origin_reclaim else np.nan,
          full_reaccept_h=float((rea_t-fail_t).total_seconds()/3600) if full_reaccept else np.nan,
          failure_to_end_atr=failure_to_end,origin_reclaim_residual_atr=origin_reclaim_resid,reaccept_residual_atr=reaccept_resid,
          reentry_net_atr=reentry_net,post_failure_mae_atr=float(max(adv)) if adv else 0.0,post_failure_mfe_atr=float(max(fav)) if fav else 0.0,
          extra_bad_closes_before_reaccept=int(extra_bad),frozen_time_only_net_atr=float(r.time_only_net_atr),frozen_close2_net_atr=float(r.origin_close2_net_atr),
          terminal_failure_at_horizon=bool(fail_t==end_t)))
    return pd.DataFrame(rows).sort_values('signal_time').reset_index(drop=True)

def main():
    price=L.L23.load_price(); lin=L.load_lineage(); d=simulate_v2(price,lin); d.to_csv(L.OUT/'failure_recovery_stream.csv',index=False)
    pre=d[d.signal_time<L.PRE]
    raw_pre=lin[lin.signal_time<L.PRE]; raw_trig_pre=int(raw_pre.origin_close2_trigger.sum())
    tabs=[]
    for name,(a,b) in L.WINS.items():
        q=d[(d.signal_time>=pd.Timestamp(a,tz=L.UTC))&(d.signal_time<pd.Timestamp(b,tz=L.UTC))]; tabs.append(L.state_metrics(q,name))
    tab=pd.DataFrame(tabs); tab.to_csv(L.OUT/'recovery_by_window.csv',index=False)
    side=pd.DataFrame([L.state_metrics(pre[pre.side==1],'LONG'),L.state_metrics(pre[pre.side==-1],'SHORT')]); side.to_csv(L.OUT/'recovery_by_side.csv',index=False)
    boot=L.bootstrap(d); (L.OUT/'bootstrap_7d.json').write_text(json.dumps(boot,indent=2),encoding='utf-8')
    get=lambda n: tab[tab['sample']==n].iloc[0]
    allm=get('ALL_PRE_AUG'); hist=get('HIST'); rec=get('RECENT')
    y22=d[(d.signal_time>=pd.Timestamp('2022-01-01',tz=L.UTC))&(d.signal_time<pd.Timestamp('2023-01-01',tz=L.UTC))&(d.side==-1)]
    y22m=L.state_metrics(y22,'2022_SHORT'); longm=side[side['sample']=='LONG'].iloc[0]; shortm=side[side['sample']=='SHORT'].iloc[0]
    recent_condition=(rec.full_reaccept_rate>=hist.full_reaccept_rate+.05) or (rec.reaccept_resid>=hist.reaccept_resid+.25)
    exact=(len(lin)==1501 and len(raw_pre)==1496 and len(pre)==raw_trig_pre and raw_trig_pre>=900)
    gates={
      'exact_lab029_lineage_and_failure_n_ge_900':bool(exact),
      'full_reaccept_n_ge_200':bool(allm.full_reaccept_n>=200),
      'full_reaccept_residual_positive':bool(allm.reaccept_resid>0),
      'residual_gap_ge_0_50atr':bool(allm.residual_gap>=.50),
      'bootstrap_ci_lower_gt_zero':bool(boot['ci_lo']>0),
      'no_reaccept_nonpositive_or_gap_ge_0_50':bool(allm.no_reaccept_resid<=0 or allm.residual_gap>=.50),
      'recent_full_reaccept_n_ge_40':bool(rec.full_reaccept_n>=40),
      'recent_full_reaccept_residual_positive':bool(rec.reaccept_resid>0),
      'recent_reaccept_gt_no_reaccept':bool(rec.reaccept_resid>rec.no_reaccept_resid),
      'recent_recovery_shift_support':bool(recent_condition),
      'stress_2022_short_reaccept_n20_residual_positive':bool(y22m['full_reaccept_n']>=20 and y22m['reaccept_resid']>0),
      'long_and_short_reaccept_residual_positive':bool(longm.reaccept_resid>0 and shortm.reaccept_resid>0)}
    critical=['exact_lab029_lineage_and_failure_n_ge_900','full_reaccept_residual_positive','residual_gap_ge_0_50atr','bootstrap_ci_lower_gt_zero','recent_full_reaccept_n_ge_40','recent_full_reaccept_residual_positive','recent_reaccept_gt_no_reaccept']
    score=sum(gates.values())
    if score>=10 and all(gates[k] for k in critical):verdict='PASS_FAILURE_RECOVERY_REACCEPTANCE_MECHANISM'
    elif gates['full_reaccept_residual_positive'] and gates['residual_gap_ge_0_50atr']:verdict='WATCH_REACCEPTANCE_DISCRIMINATIVE_BUT_TRANSFER_INCOMPLETE'
    else:verdict='FAIL_NO_ROBUST_FAILURE_RECOVERY_MECHANISM'
    meta=dict(verdict=verdict,lineage_n=len(lin),accept_pre=len(raw_pre),raw_failure_n_pre=raw_trig_pre,failure_n_pre=len(pre),terminal_failures_pre=int(pre.terminal_failure_at_horizon.sum()),
      median_reclaim_h=float(pre.loc[pre.origin_reclaim,'origin_reclaim_h'].median()),median_reaccept_h=float(pre.loc[pre.full_reaccept,'full_reaccept_h'].median()),median_extra_bad=float(pre.loc[pre.full_reaccept,'extra_bad_closes_before_reaccept'].median()),y22_short=y22m)
    (L.OUT/'verdict.json').write_text(json.dumps({'meta':meta,'bootstrap':boot,'gates':gates},indent=2,allow_nan=True),encoding='utf-8')
    rep=L.report(tab,side,boot,gates,meta)
    rep=rep.replace(f"- LAB029 rows: **{meta['lineage_n']}**; triggered failures pre-Aug: **{meta['failure_n_pre']}**",f"- LAB029 rows: **{meta['lineage_n']}** (pre-Aug ACCEPT **{meta['accept_pre']}**); triggered failures pre-Aug: **{meta['failure_n_pre']}**; terminal-at-horizon: **{meta['terminal_failures_pre']}**")
    (L.OUT/'REPORT.md').write_text(rep,encoding='utf-8'); print(rep)

if __name__=='__main__':main()
