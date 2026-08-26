import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import fisher_exact

import btc_unsupported_breakout_flow_sponsorship_common_support_lab012 as lab12

LAB = 'BTC_FLOW_SPONSORSHIP_PERSISTENCE_DIRECTIONAL_ABLATION_LAB_013'
INDEPENDENT_YEARS = [2020, 2022, 2023, 2024, 2025]
DISCOVERY_YEAR = 2021
FORWARD_YEAR = 2026
Q_LOW = 1.0 / 3.0
MIN_VETO_YEAR = 4
MIN_KEEP_YEAR = 8
MIN_VETO_POOLED = 20
MIN_VALID_YEARS = 4
STRONG_PASS_YEARS = 4
PARTIAL_PASS_YEARS = 3

# Predeclared persistence-only ablation. No price_response/flow, no new flow-size features.
SINGLE_LOW = {
    'P3_LOW': 'flow_persistence_3',
    'P6_LOW': 'flow_persistence_6',
    'P12_LOW': 'flow_persistence_12',
    'P24_LOW': 'flow_persistence_24',
    'SHIFT_3V12_LOW': 'persistence_shift_3v12',
    'SHIFT_6V24_LOW': 'persistence_shift_6v24',
    'SHIFT_3V24_LOW': 'persistence_shift_3v24',
    'ACCEL_3V6_LOW': 'persistence_accel_3v6',
    'ACCEL_6V12_LOW': 'persistence_accel_6v12',
}
COMPOSITES = [
    'P12_OR_SHIFT3V12_LOW',
    'P6_OR_SHIFT6V24_LOW',
    'PERSISTENCE_2OF4_LOW',
    'PERSISTENCE_3OF4_LOW',
]
RULES = list(SINGLE_LOW) + COMPOSITES


def num(s):
    return pd.to_numeric(s, errors='coerce').astype(float)


def enrich(base):
    z = base.copy()
    z['persistence_shift_6v24'] = num(z['flow_persistence_6']) - num(z['flow_persistence_24'])
    z['persistence_shift_3v24'] = num(z['flow_persistence_3']) - num(z['flow_persistence_24'])
    z['persistence_accel_3v6'] = num(z['flow_persistence_3']) - num(z['flow_persistence_6'])
    z['persistence_accel_6v12'] = num(z['flow_persistence_6']) - num(z['flow_persistence_12'])
    return z


def freeze_thresholds(train_dir):
    feats = sorted(set(SINGLE_LOW.values()) | {
        'flow_persistence_3', 'flow_persistence_6', 'flow_persistence_12', 'flow_persistence_24'
    })
    out = {}
    for f in feats:
        s = num(train_dir[f]).dropna()
        out[f] = float(s.quantile(Q_LOW)) if len(s) else np.nan
    return out


def apply_rules(df, thr):
    z = df.copy()
    low_flags = {}
    for rule, feat in SINGLE_LOW.items():
        t = thr.get(feat, np.nan)
        flag = (num(z[feat]) <= t) if np.isfinite(t) else pd.Series(False, index=z.index)
        z['veto_' + rule] = flag.astype(int)
        low_flags[rule] = flag

    p3 = num(z['flow_persistence_3']) <= thr['flow_persistence_3']
    p6 = num(z['flow_persistence_6']) <= thr['flow_persistence_6']
    p12 = num(z['flow_persistence_12']) <= thr['flow_persistence_12']
    p24 = num(z['flow_persistence_24']) <= thr['flow_persistence_24']
    s312 = num(z['persistence_shift_3v12']) <= thr['persistence_shift_3v12']
    s624 = num(z['persistence_shift_6v24']) <= thr['persistence_shift_6v24']

    z['veto_P12_OR_SHIFT3V12_LOW'] = (p12 | s312).astype(int)
    z['veto_P6_OR_SHIFT6V24_LOW'] = (p6 | s624).astype(int)
    cnt = p3.astype(int) + p6.astype(int) + p12.astype(int) + p24.astype(int)
    z['persistence_low_count_4'] = cnt
    z['veto_PERSISTENCE_2OF4_LOW'] = (cnt >= 2).astype(int)
    z['veto_PERSISTENCE_3OF4_LOW'] = (cnt >= 3).astype(int)
    return z


def summarize(df, rule, direction, year, fold_type):
    supported = df[df.common_support == 1].copy()
    veto = supported[supported['veto_' + rule] == 1]
    keep = supported[supported['veto_' + rule] == 0]
    def rate(x, c):
        return float(x[c].mean()) if len(x) else np.nan
    b_l = rate(supported, 'is_large'); b_f = rate(supported, 'is_fail')
    v_l = rate(veto, 'is_large'); v_f = rate(veto, 'is_fail')
    k_l = rate(keep, 'is_large'); k_f = rate(keep, 'is_fail')
    valid = len(veto) >= MIN_VETO_YEAR and len(keep) >= MIN_KEEP_YEAR
    pass_fold = bool(valid and np.isfinite(v_l) and np.isfinite(k_l) and np.isfinite(v_f) and np.isfinite(k_f)
                     and (v_l - k_l) <= -0.07 and (v_f - k_f) >= 0.05)
    return {
        'rule': rule, 'direction': int(direction), 'direction_name': 'BUY' if direction > 0 else 'SELL',
        'year': int(year), 'fold_type': fold_type,
        'test_n': int(len(df)), 'supported_n': int(len(supported)),
        'support_coverage': float(len(supported)/len(df)) if len(df) else np.nan,
        'baseline_large_rate': b_l, 'baseline_fail_rate': b_f,
        'veto_n': int(len(veto)), 'veto_share': float(len(veto)/len(supported)) if len(supported) else np.nan,
        'veto_large_rate': v_l, 'veto_fail_rate': v_f,
        'keep_n': int(len(keep)), 'keep_large_rate': k_l, 'keep_fail_rate': k_f,
        'veto_minus_keep_large_pp': 100*(v_l-k_l) if np.isfinite(v_l) and np.isfinite(k_l) else np.nan,
        'veto_minus_keep_fail_pp': 100*(v_f-k_f) if np.isfinite(v_f) and np.isfinite(k_f) else np.nan,
        'keep_minus_baseline_large_pp': 100*(k_l-b_l) if np.isfinite(k_l) and np.isfinite(b_l) else np.nan,
        'keep_minus_baseline_fail_pp': 100*(k_f-b_f) if np.isfinite(k_f) and np.isfinite(b_f) else np.nan,
        'large_retention': float(keep.is_large.sum()/supported.is_large.sum()) if supported.is_large.sum() else np.nan,
        'frequency_retention': float(len(keep)/len(supported)) if len(supported) else np.nan,
        'valid_year': valid, 'pass_year': pass_fold,
    }


def pooled_metrics(oof, rule, direction):
    s = oof[(oof.direction == direction) & (oof.common_support == 1)].copy()
    veto = s[s['veto_' + rule] == 1]; keep = s[s['veto_' + rule] == 0]
    def r(x,c): return float(x[c].mean()) if len(x) else np.nan
    vl, kl = r(veto,'is_large'), r(keep,'is_large')
    vf, kf = r(veto,'is_fail'), r(keep,'is_fail')
    try:
        odds_l, p_l = fisher_exact([[int(veto.is_large.sum()), int(len(veto)-veto.is_large.sum())],
                                    [int(keep.is_large.sum()), int(len(keep)-keep.is_large.sum())]], alternative='less') if len(veto) and len(keep) else (np.nan,np.nan)
    except Exception:
        odds_l,p_l=np.nan,np.nan
    try:
        odds_f, p_f = fisher_exact([[int(veto.is_fail.sum()), int(len(veto)-veto.is_fail.sum())],
                                    [int(keep.is_fail.sum()), int(len(keep)-keep.is_fail.sum())]], alternative='greater') if len(veto) and len(keep) else (np.nan,np.nan)
    except Exception:
        odds_f,p_f=np.nan,np.nan
    return {
        'rule': rule, 'direction': int(direction), 'direction_name': 'BUY' if direction>0 else 'SELL',
        'supported_n': int(len(s)), 'veto_n': int(len(veto)), 'keep_n': int(len(keep)),
        'veto_large_rate': vl, 'keep_large_rate': kl,
        'veto_fail_rate': vf, 'keep_fail_rate': kf,
        'veto_minus_keep_large_pp': 100*(vl-kl) if np.isfinite(vl) and np.isfinite(kl) else np.nan,
        'veto_minus_keep_fail_pp': 100*(vf-kf) if np.isfinite(vf) and np.isfinite(kf) else np.nan,
        'large_retention': float(keep.is_large.sum()/s.is_large.sum()) if s.is_large.sum() else np.nan,
        'frequency_retention': float(len(keep)/len(s)) if len(s) else np.nan,
        'fisher_large_less_p': float(p_l) if np.isfinite(p_l) else np.nan,
        'fisher_fail_greater_p': float(p_f) if np.isfinite(p_f) else np.nan,
        'fisher_large_odds': float(odds_l) if np.isfinite(odds_l) else np.nan,
        'fisher_fail_odds': float(odds_f) if np.isfinite(odds_f) else np.nan,
    }


def add_stability(pooled, yearly):
    rows=[]
    for _,p in pooled.iterrows():
        y=yearly[(yearly.rule==p.rule)&(yearly.direction==p.direction)&(yearly.fold_type=='INDEPENDENT_LOYO')]
        valid=y[y.valid_year==True]
        d=p.to_dict(); d['valid_years']=int(len(valid)); d['passing_years']=int(valid.pass_year.sum())
        d['negative_large_gap_years']=int((valid.veto_minus_keep_large_pp<0).sum())
        d['positive_fail_gap_years']=int((valid.veto_minus_keep_fail_pp>0).sum())
        pooled_pass = (d['veto_n']>=MIN_VETO_POOLED and np.isfinite(d['veto_minus_keep_large_pp']) and np.isfinite(d['veto_minus_keep_fail_pp'])
                       and d['veto_minus_keep_large_pp']<=-7 and d['veto_minus_keep_fail_pp']>=5 and d['large_retention']>=0.85)
        if pooled_pass and d['valid_years']>=MIN_VALID_YEARS and d['passing_years']>=STRONG_PASS_YEARS:
            cls='STRONG_DIRECTIONAL_REPLICATION'
        elif pooled_pass and d['valid_years']>=MIN_VALID_YEARS and d['passing_years']>=PARTIAL_PASS_YEARS:
            cls='PARTIAL_DIRECTIONAL_REPLICATION'
        else:
            cls='NO_RELIABLE_DIRECTIONAL_REPLICATION'
        d['classification']=cls; rows.append(d)
    return pd.DataFrame(rows)


def main():
    _, all_events, base = lab12.build_base()
    base=enrich(base)
    base=base[base.year.between(2020,2026)].copy().reset_index(drop=True)
    yearly=[]; oof=[]; thresholds=[]

    # Strict independent LOYO: 2021 never enters threshold/support training.
    for test_year in INDEPENDENT_YEARS:
        train=base[base.year.isin([y for y in INDEPENDENT_YEARS if y!=test_year])].copy()
        test=base[base.year==test_year].copy()
        for direction in (1,-1):
            tr=train[train.direction==direction].copy(); te=test[test.direction==direction].copy()
            if len(tr)<20 or len(te)==0: continue
            thr=freeze_thresholds(tr)
            sup=lab12.common_support(tr,te)
            rr=apply_rules(sup,thr)
            rr['eval_year']=test_year; rr['eval_fold_type']='INDEPENDENT_LOYO'
            oof.append(rr)
            for k,v in thr.items(): thresholds.append({'year':test_year,'fold_type':'INDEPENDENT_LOYO','direction':direction,'direction_name':'BUY' if direction>0 else 'SELL','feature':k,'q':Q_LOW,'threshold':v,'train_n':len(tr)})
            for rule in RULES: yearly.append(summarize(rr,rule,direction,test_year,'INDEPENDENT_LOYO'))

    oof_df=pd.concat(oof,ignore_index=True) if oof else pd.DataFrame()
    pooled=[]
    for direction in (1,-1):
        for rule in RULES: pooled.append(pooled_metrics(oof_df,rule,direction))
    pooled_df=add_stability(pd.DataFrame(pooled),pd.DataFrame(yearly))

    # 2021 diagnostic: train only on independent years.
    diag=[]
    train_ind=base[base.year.isin(INDEPENDENT_YEARS)].copy()
    for direction in (1,-1):
        tr=train_ind[train_ind.direction==direction].copy(); te=base[(base.year==DISCOVERY_YEAR)&(base.direction==direction)].copy()
        if len(tr)>=20 and len(te):
            thr=freeze_thresholds(tr); rr=apply_rules(lab12.common_support(tr,te),thr)
            for rule in RULES: diag.append(summarize(rr,rule,direction,DISCOVERY_YEAR,'DISCOVERY_2021_DIAGNOSTIC'))

    # 2026 pseudo-forward: thresholds/support estimated only from independent years, 2021 excluded.
    forward=[]; forward_events=[]
    for direction in (1,-1):
        tr=train_ind[train_ind.direction==direction].copy(); te=base[(base.year==FORWARD_YEAR)&(base.direction==direction)].copy()
        if len(tr)>=20 and len(te):
            thr=freeze_thresholds(tr); rr=apply_rules(lab12.common_support(tr,te),thr); rr['eval_year']=FORWARD_YEAR; rr['eval_fold_type']='PSEUDO_FORWARD_2026'; forward_events.append(rr)
            for rule in RULES: forward.append(summarize(rr,rule,direction,FORWARD_YEAR,'PSEUDO_FORWARD_2026'))

    yearly_df=pd.DataFrame(yearly); diag_df=pd.DataFrame(diag); fwd_df=pd.DataFrame(forward); th_df=pd.DataFrame(thresholds)
    rank=pooled_df.sort_values(['classification','passing_years','veto_minus_keep_large_pp'],ascending=[True,False,True]).copy()

    strong=pooled_df[pooled_df.classification=='STRONG_DIRECTIONAL_REPLICATION']
    partial=pooled_df[pooled_df.classification=='PARTIAL_DIRECTIONAL_REPLICATION']
    if len(strong): verdict_class='PERSISTENCE_DIRECTIONAL_FILTER_REPLICATES_STRONGLY'
    elif len(partial): verdict_class='PERSISTENCE_DIRECTIONAL_FILTER_REPLICATES_PARTIALLY'
    else: verdict_class='PERSISTENCE_DIRECTIONAL_FILTER_DOES_NOT_REPLICATE_RELIABLY'

    best=[]
    for direction in (1,-1):
        q=pooled_df[pooled_df.direction==direction].copy()
        if len(q):
            q=q.sort_values(['passing_years','veto_minus_keep_large_pp','veto_minus_keep_fail_pp'],ascending=[False,True,False])
            best.append(q.iloc[0].to_dict())

    verdict={
        'lab':LAB,
        'question':'Does pre-BOS aggressive-flow sponsorship persistence provide a stable directional veto inside LOW_ACTIVITY + FLOW_ALIGN states?',
        'base_selector':'LOW_ACTIVITY_SCORE>=2 AND FLOW_DELTA_12>0',
        'target':'clean MFE >= 2.5R within 32 M15 bars before structural SL',
        'causality':'all persistence windows end at i-1; BOS candle/post-BOS excluded',
        'independent_years':INDEPENDENT_YEARS,
        'discovery_year_excluded_from_training':DISCOVERY_YEAR,
        'pseudo_forward_year':FORWARD_YEAR,
        'threshold_policy':'all LOW cutoffs fixed at training-fold Q33 separately for BUY and SELL; no threshold search',
        'rules':RULES,
        'pass_policy':{'per_year':'veto_n>=4, keep_n>=8, LARGE gap<=-7pp, FAIL gap>=+5pp','pooled':'veto_n>=20, LARGE gap<=-7pp, FAIL gap>=+5pp, large retention>=85%','strong':'pooled pass + >=4/5 valid independent years pass','partial':'pooled pass + >=3/5 valid independent years pass'},
        'best_by_direction':best,
        'strong_rules':strong.to_dict('records'),
        'partial_rules':partial.to_dict('records'),
        'verdict_class':verdict_class,
        'warning':'Ablation/robustness study only. Historical years have been inspected in prior labs; true production admission still requires untouched forward/execution-cost validation.'
    }

    print('='*100); print(LAB); print('BASE',len(base),'ALL_EVENTS',len(all_events)); print('IMPORTANT: 2021 excluded from all independent threshold/support training. BOS/post-BOS excluded from features.')
    print('\nPOOLED DIRECTIONAL ABLATION');
    cols=['direction_name','rule','supported_n','veto_n','veto_large_rate','keep_large_rate','veto_minus_keep_large_pp','veto_fail_rate','keep_fail_rate','veto_minus_keep_fail_pp','large_retention','frequency_retention','valid_years','passing_years','classification']
    print(pooled_df.sort_values(['direction_name','passing_years','veto_minus_keep_large_pp'],ascending=[True,False,True])[cols].to_string(index=False))
    print('\nYEARLY INDEPENDENT'); print(yearly_df.to_string(index=False))
    print('\n2021 DIAGNOSTIC'); print(diag_df.to_string(index=False))
    print('\n2026 PSEUDO-FORWARD'); print(fwd_df.to_string(index=False))
    print('\nVERDICT'); print(json.dumps(verdict,indent=2))

    out=Path('lab013'); out.mkdir(exist_ok=True)
    base.to_csv(out/f'{LAB}_BASE_EVENTS.csv',index=False)
    oof_df.to_csv(out/f'{LAB}_INDEPENDENT_LOYO_EVENTS.csv',index=False)
    yearly_df.to_csv(out/f'{LAB}_YEARLY_ABLATION.csv',index=False)
    pooled_df.to_csv(out/f'{LAB}_POOLED_DIRECTIONAL_ABLATION.csv',index=False)
    diag_df.to_csv(out/f'{LAB}_2021_DIAGNOSTIC.csv',index=False)
    fwd_df.to_csv(out/f'{LAB}_2026_PSEUDO_FORWARD.csv',index=False)
    th_df.to_csv(out/f'{LAB}_FROZEN_THRESHOLDS.csv',index=False)
    if forward_events: pd.concat(forward_events,ignore_index=True).to_csv(out/f'{LAB}_2026_EVENTS.csv',index=False)
    (out/'verdict.json').write_text(json.dumps(verdict,indent=2),encoding='utf-8')
    report=[f'# {LAB}','','Persistence-only directional ablation. `2021` is excluded from all independent training. All candidate features end at `i-1`; BOS/post-BOS are excluded.','','## Pooled directional ablation','',pooled_df[cols].sort_values(['direction_name','passing_years','veto_minus_keep_large_pp'],ascending=[True,False,True]).to_markdown(index=False),'','## Independent yearly folds','',yearly_df.to_markdown(index=False),'','## 2021 diagnostic','',diag_df.to_markdown(index=False),'','## 2026 pseudo-forward','',fwd_df.to_markdown(index=False),'','## Verdict','',f'```json\n{json.dumps(verdict,indent=2)}\n```']
    (out/f'{LAB}_REPORT.md').write_text('\n'.join(report),encoding='utf-8')

if __name__=='__main__':
    main()
