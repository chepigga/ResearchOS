#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import re
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

LAB='XAU_CONTEXT_COMPRESSION_CONCORDANCE_FRESH_OOS_REPLICATION_LAB_015'
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
LAB8_PATH=ROOT/'labs'/'XAU_CONTEXT_STATE_TIMESCALE_AND_LABEL_PURIFICATION_LAB_008'/'run_lab.py'
LAB9_PATH=ROOT/'labs'/'XAU_CONTEXT_TEMPORAL_ROLE_AND_STATE_AGE_REDESIGN_LAB_009'/'run_lab.py'
LAB10_PATH=ROOT/'labs'/'XAU_CONTEXT_REVERSAL_ACTIVATION_AND_RANGE_DEFINITION_REDESIGN_LAB_010'/'run_lab.py'
LAB13_PATH=ROOT/'labs'/'XAU_CONTEXT_COMPRESSION_BREAKOUT_DIRECTION_AND_RESOLUTION_LAB_013'/'run_lab.py'
ARCHIVE_SHA='31f9548204fa99c29ce7d09e5b64e01ff75f5e8e3efab6f747cbd410cf34fd2e'
OOS_START=pd.Timestamp('2026-07-24 00:00:00')
WARMUP_START=pd.Timestamp('2025-01-01 00:00:00')
ARCHIVE_END=pd.Timestamp('2026-08-27 23:59:59.999')
BOOT_N=5000
SEED=2026091215
MEMBER_RE=re.compile(r'^CAUSAL_XAU_RAW_XAUUSD_(\d{8})\.csv$')


def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):
            h.update(b)
    return h.hexdigest()


def load_module(path:Path,name:str):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def week_col(s:pd.Series)->pd.Series:
    return pd.to_datetime(s).dt.to_period('W-SUN').astype(str)


def parse_manifest(z:zipfile.ZipFile)->dict:
    name='CAUSAL_XAU_RAW_MANIFEST.csv'
    if name not in z.namelist():
        raise RuntimeError('Manifest missing')
    x=pd.read_csv(z.open(name))
    if not {'field','value'}.issubset(x.columns):
        raise RuntimeError('Manifest schema mismatch')
    return {str(k):str(v) for k,v in zip(x.field,x.value)}


def raw_ticks_to_m1(archive:Path)->tuple[pd.DataFrame,dict]:
    actual=sha256(archive)
    if actual!=ARCHIVE_SHA:
        raise RuntimeError(f'Archive SHA mismatch: {actual}')
    frames=[]; processed=[]; raw_rows=0; valid_rows=0
    with zipfile.ZipFile(archive) as z:
        manifest=parse_manifest(z)
        if manifest.get('symbol')!='XAUUSD' or manifest.get('server')!='FTMO-Demo':
            raise RuntimeError(f'Unexpected manifest source: {manifest.get("symbol")} / {manifest.get("server")}')
        selected=[]
        for info in z.infolist():
            m=MEMBER_RE.match(info.filename)
            if not m: continue
            dt=pd.Timestamp(m.group(1))
            if WARMUP_START.normalize()<=dt<=pd.Timestamp('2026-08-27'):
                selected.append((dt,info.filename))
        selected.sort()
        if not selected:
            raise RuntimeError('No selected daily raw members')
        for dt,name in selected:
            with z.open(name) as f:
                try:
                    x=pd.read_csv(f,usecols=['time_msc','bid'])
                except pd.errors.EmptyDataError:
                    continue
            raw_rows += len(x)
            if x.empty:
                processed.append(name); continue
            tm=pd.to_numeric(x['time_msc'],errors='coerce')
            bid=pd.to_numeric(x['bid'],errors='coerce')
            mask=tm.notna()&bid.notna()&np.isfinite(bid)&bid.gt(0)
            if not mask.any():
                processed.append(name); continue
            q=pd.DataFrame({'time':pd.to_datetime(tm[mask].astype('int64'),unit='ms',utc=True).dt.tz_localize(None),
                            'bid':bid[mask].astype(float).to_numpy()})
            q=q.sort_values('time')
            valid_rows += len(q)
            q['minute']=q.time.dt.floor('min')
            g=q.groupby('minute',sort=True).bid.agg(['first','max','min','last','size']).reset_index()
            g.columns=['time','open','high','low','close','volume']
            frames.append(g)
            processed.append(name)
    if not frames:
        raise RuntimeError('No M1 bars reconstructed')
    m1=pd.concat(frames,ignore_index=True).sort_values('time')
    # Daily files are non-overlapping by construction; keep last defensively if duplicates occur.
    m1=m1.drop_duplicates('time',keep='last').reset_index(drop=True)
    meta={
        'archive_sha256':actual,
        'manifest':manifest,
        'processed_member_count':len(processed),
        'processed_member_first':processed[0] if processed else None,
        'processed_member_last':processed[-1] if processed else None,
        'raw_rows':int(raw_rows),'valid_bid_rows':int(valid_rows),
        'm1_rows':int(len(m1)),
        'm1_first':str(m1.time.min()),'m1_last':str(m1.time.max())
    }
    return m1,meta


def week_breakdown(q:pd.DataFrame)->pd.DataFrame:
    z=q.copy()
    z['week']=week_col(z.available_time)
    rows=[]
    for w,g in z.groupby('week',sort=True):
        h=g[g.D14_CONCORDANCE.ne(0)&g.target_dir.isin([-1,1])]
        acc=float((h.D14_CONCORDANCE==h.target_dir).mean()) if len(h) else np.nan
        f=g.loc[g.D14_CONCORDANCE.ne(0),'D14_signed24'].dropna()
        rows.append({'week':w,'population':int(len(g)),'resolved_d14_n':int(len(h)),
                     'accuracy':acc,'follow24_n':int(len(f)),
                     'mean_signed24_atr':float(f.mean()) if len(f) else np.nan})
    return pd.DataFrame(rows)


def side_table(primary:pd.DataFrame)->pd.DataFrame:
    rows=[]
    for sign,name in [(1,'BULL'),(-1,'BEAR')]:
        s=primary[primary.D14_CONCORDANCE.eq(sign)]
        rows.append({'side':name,'n_resolved':int(len(s)),
                     'accuracy':float(s.correct.mean()) if len(s) else np.nan,
                     'mean_signed24_atr':float(pd.to_numeric(s.D14_signed24,errors='coerce').mean()) if len(s) else np.nan})
    return pd.DataFrame(rows)


def h4_continuity_boot(lab10,d:pd.DataFrame,metric:str,a:pd.Series,b:pd.Series,seed:int):
    return lab10.cluster_bootstrap_masks(d,metric,a,b,seed)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--archive',required=True)
    ap.add_argument('--out',required=True)
    args=ap.parse_args()
    out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    archive=Path(args.archive)

    lab8=load_module(LAB8_PATH,'lab8_015')
    lab9=load_module(LAB9_PATH,'lab9_015')
    lab10=load_module(LAB10_PATH,'lab10_015')
    lab13=load_module(LAB13_PATH,'lab13_015')

    m1,source_meta=raw_ticks_to_m1(archive)
    h4=lab8.to_h4(m1)
    router=lab8.load_router_module()
    ctx=router.add_router(h4)
    ctx=lab8.add_forward_metrics(ctx)
    ctx=ctx.dropna(subset=['available_time','atr14']).copy()
    allbars,onset=lab8.make_episodes(ctx)
    d=lab9.add_roles(allbars)
    d=lab10.add_components_and_candidates(d)
    d=lab13.add_prediction_candidates(d)
    d['D14_CONCORDANCE']=np.where((d.D1_HTF_BIAS==d.D2_TREND_PRESSURE)&d.D1_HTF_BIAS.ne(0),d.D1_HTF_BIAS,0).astype(int)

    # Fresh OOS population only. Warm-up rows can influence backward-looking indicators, never outcomes.
    fresh=d.available_time.ge(OOS_START)
    if fresh.any() and pd.Timestamp(d.loc[fresh,'available_time'].min())<OOS_START:
        raise RuntimeError('Freshness boundary violation')
    pop=fresh & d.regime.eq('PULLBACK') & d.G1_VOL_COMPRESSION.fillna(False)

    # Exact M1 first-passage for G1 population. Exclude rows whose full 8h window extends beyond data tail.
    fp=lab13.exact_first_passage(m1,d,pop)
    d=d.join(fp,how='left')
    m1_last=pd.Timestamp(m1.time.max())
    d['full_8h_available']=d.available_time.add(pd.Timedelta(hours=8)).le(m1_last+pd.Timedelta(minutes=1))
    d.loc[pop & ~d.full_8h_available,['resolution','target_dir','touch_time','time_to_touch_min']]=[np.nan,np.nan,pd.NaT,np.nan]

    q=d.loc[pop].copy()
    q['D14_signed24']=q.D14_CONCORDANCE*pd.to_numeric(q.close_ret_atr_24h,errors='coerce')
    total=int(len(q)); directional=q.D14_CONCORDANCE.ne(0)
    resolved=q.target_dir.isin([-1,1])
    primary=q[directional&resolved].copy()
    primary['correct']=(primary.D14_CONCORDANCE==primary.target_dir).astype(float)

    # Leakage audit: all primary observations are fresh and scans start no earlier than available_time by construction.
    if len(primary) and pd.Timestamp(primary.available_time.min())<OOS_START:
        raise RuntimeError('H1 pre-freeze leakage')
    follow=q[q.D14_CONCORDANCE.ne(0)&q.D14_signed24.notna()].copy()
    if len(follow) and pd.Timestamp(follow.available_time.min())<OOS_START:
        raise RuntimeError('H2 pre-freeze leakage')

    acc_boot=lab13.cluster_boot_mean(primary,'correct',SEED+1)
    coverage=float(directional.mean()) if total else np.nan
    weeks=week_breakdown(q)
    weeks_with_resolved=int((weeks.resolved_d14_n>0).sum()) if len(weeks) else 0
    weeks_ge3=weeks[weeks.resolved_d14_n>=3]
    week_positive_share=float((weeks_ge3.accuracy>0.5).mean()) if len(weeks_ge3) else np.nan
    h1_eligible=bool(len(primary)>=20 and coverage>=0.30 and weeks_with_resolved>=3 and len(weeks_ge3)>=2)
    h1=bool(h1_eligible and acc_boot['observed']>0.5 and np.isfinite(acc_boot['ci_lo']) and acc_boot['ci_lo']>0.5)

    follow_boot=lab13.cluster_boot_mean(follow,'D14_signed24',SEED+2)
    follow_weeks=int(week_col(follow.available_time).nunique()) if len(follow) else 0
    h2_eligible=bool(len(follow)>=20 and follow_weeks>=3)
    h2=bool(h2_eligible and follow_boot['observed']>0 and np.isfinite(follow_boot['ci_lo']) and follow_boot['ci_lo']>0)

    sides=side_table(primary)
    bull=sides[sides.side.eq('BULL')].iloc[0]; bear=sides[sides.side.eq('BEAR')].iloc[0]
    h3_eligible=bool(bull.n_resolved>=5 and bear.n_resolved>=5)
    h3=bool(h3_eligible and bull.accuracy>=0.5 and bear.accuracy>=0.5 and abs(bull.accuracy-bear.accuracy)<=0.20)
    side_bad=bool((bull.n_resolved>=5 and bull.accuracy<0.45) or (bear.n_resolved>=5 and bear.accuracy<0.45))

    # Parent compression breakout-risk continuity inside fresh Pullback.
    fresh_pb=fresh & d.regime.eq('PULLBACK')
    fp_pb=lab13.exact_first_passage(m1,d,fresh_pb)
    # Do not collide with G1 target columns; map separately.
    breakout=pd.Series(np.nan,index=d.index,dtype=float)
    if len(fp_pb):
        full8=d.loc[fp_pb.index,'available_time'].add(pd.Timedelta(hours=8)).le(m1_last+pd.Timedelta(minutes=1))
        labels=fp_pb.resolution
        vals=labels.isin(['BULL_FIRST','BEAR_FIRST','AMBIGUOUS']).astype(float)
        vals=vals.where(full8.to_numpy(),np.nan)
        breakout.loc[fp_pb.index]=vals.to_numpy()
    d['fresh_breakout_any_1atr_8h']=breakout
    valid8=fresh_pb & d.fresh_breakout_any_1atr_8h.notna()
    a8=valid8 & d.G1_VOL_COMPRESSION.fillna(False)
    b8=valid8 & ~d.G1_VOL_COMPRESSION.fillna(False)
    h4_break=h4_continuity_boot(lab10,d,'fresh_breakout_any_1atr_8h',a8,b8,SEED+3)

    valid24=fresh_pb & pd.to_numeric(d.range_atr_24h,errors='coerce').notna()
    a24=valid24 & d.G1_VOL_COMPRESSION.fillna(False)
    b24=valid24 & ~d.G1_VOL_COMPRESSION.fillna(False)
    h4_range=h4_continuity_boot(lab10,d,'range_atr_24h',a24,b24,SEED+4)
    h4_eligible=bool(int(a8.sum())>=20 and int(a24.sum())>=20)
    h4_pass=bool(h4_eligible and h4_break['observed']>0 and h4_range['observed']>0)

    if len(primary)<5 or len(follow)<5:
        verdict='FRESH_OOS_NO_TESTABLE_EVENTS'
    elif h1 and h2 and h3:
        verdict='FRESH_OOS_CONCORDANCE_REPLICATED'
    elif h1 and h2 and not h3_eligible:
        verdict='FRESH_OOS_DIRECTION_AND_PERSISTENCE_SUPPORTED_SIDE_UNDERPOWERED'
    elif ((not h1_eligible) or (not h2_eligible)) and len(primary)>=5 and len(follow)>=5 and \
         float(acc_boot['observed'])>0.5 and float(follow_boot['observed'])>0 and not side_bad:
        verdict='FRESH_OOS_DIRECTIONALLY_CONSISTENT_UNDERPOWERED'
    else:
        verdict='FRESH_OOS_NOT_REPLICATED'

    # Descriptive counts.
    resolution_counts=q.resolution.value_counts(dropna=False).to_dict()
    target=q[q.target_dir.isin([-1,1])]
    target_balance={'bull_first':int((target.target_dir==1).sum()),
                    'bear_first':int((target.target_dir==-1).sum()),
                    'bull_share':float((target.target_dir==1).mean()) if len(target) else np.nan,
                    'resolved_total':int(len(target)),
                    'no_breakout':int((q.resolution=='NO_BREAKOUT').sum()),
                    'ambiguous':int((q.resolution=='AMBIGUOUS').sum())}

    oos_times=d.loc[fresh,'available_time']
    source_meta.update({'h4_rows':int(len(h4)),'context_rows':int(len(d)),
                        'fresh_context_rows':int(fresh.sum()),
                        'fresh_available_first':str(oos_times.min()) if len(oos_times) else None,
                        'fresh_available_last':str(oos_times.max()) if len(oos_times) else None})

    weeks.to_csv(out/'fresh_week_breakdown.csv',index=False)
    sides.to_csv(out/'fresh_side_symmetry.csv',index=False)
    q[['available_time','close','atr14','bias','D1_HTF_BIAS','D2_TREND_PRESSURE','D14_CONCORDANCE',
       'resolution','target_dir','touch_time','time_to_touch_min','close_ret_atr_24h','D14_signed24','full_8h_available']].to_csv(out/'fresh_concordance_events.csv',index=False)
    (out/'source_manifest.json').write_text(json.dumps(source_meta,indent=2,default=str))

    summary={
        'lab':LAB,'verdict':verdict,'oos_start':str(OOS_START),
        'fresh_available_first':source_meta['fresh_available_first'],'fresh_available_last':source_meta['fresh_available_last'],
        'population_pullback_g1':total,'directional_predictions':int(directional.sum()),'coverage':coverage,
        'resolved_directional_n':int(len(primary)),'accuracy':float(acc_boot['observed']) if np.isfinite(acc_boot['observed']) else None,
        'accuracy_ci_lo':float(acc_boot['ci_lo']) if np.isfinite(acc_boot['ci_lo']) else None,
        'accuracy_ci_hi':float(acc_boot['ci_hi']) if np.isfinite(acc_boot['ci_hi']) else None,
        'weeks_with_resolved':weeks_with_resolved,'weeks_ge3':int(len(weeks_ge3)),'week_positive_share_ge3':week_positive_share,
        'h1_eligible':h1_eligible,'h1_pass':h1,
        'follow_n':int(len(follow)),'mean_signed24_atr':float(follow_boot['observed']) if np.isfinite(follow_boot['observed']) else None,
        'signed24_ci_lo':float(follow_boot['ci_lo']) if np.isfinite(follow_boot['ci_lo']) else None,
        'signed24_ci_hi':float(follow_boot['ci_hi']) if np.isfinite(follow_boot['ci_hi']) else None,
        'follow_weeks':follow_weeks,'h2_eligible':h2_eligible,'h2_pass':h2,
        'h3_eligible':h3_eligible,'h3_pass':h3,'target_balance':target_balance,
        'resolution_counts':{str(k):int(v) for k,v in resolution_counts.items()},
        'h4_eligible':h4_eligible,'h4_pass':h4_pass,
        'h4_breakout_premium':h4_break,'h4_range24_premium':h4_range,
        'archive_sha256':source_meta['archive_sha256']
    }
    (out/'summary.json').write_text(json.dumps(summary,indent=2,default=str))

    def fmt(x,nd=3):
        return 'NA' if x is None or not np.isfinite(float(x)) else f'{float(x):.{nd}f}'
    report=[f'# {LAB}','',f'**Verdict: {verdict}**','',
            '> Genuine post-freeze OOS semantic replication on FTMO-Demo raw ticks. No trading edge or execution claim.','',
            f'- Fresh OOS available_time: **{source_meta["fresh_available_first"]} -> {source_meta["fresh_available_last"]}**',
            f'- Fresh Pullback + G1 bars: **{total}**',
            f'- D14 directional coverage: **{coverage:.1%}** ({int(directional.sum())}/{total})' if total else '- D14 directional coverage: NA',
            f'- Exact resolved D14 predictions: **{len(primary)}**',
            f'- 24h D14 follow-through observations: **{len(follow)}**','',
            '## Primary fresh gates','',
            '| Gate | Eligible | Effect | 95% CI | Pass |','|---|---|---:|---:|---|',
            f'| H1 first-passage accuracy | {"YES" if h1_eligible else "NO"} | {fmt(acc_boot["observed"])} | [{fmt(acc_boot["ci_lo"])}, {fmt(acc_boot["ci_hi"])}] | {"PASS" if h1 else "FAIL"} |',
            f'| H2 signed 24h ATR | {"YES" if h2_eligible else "NO"} | {fmt(follow_boot["observed"])} | [{fmt(follow_boot["ci_lo"])}, {fmt(follow_boot["ci_hi"])}] | {"PASS" if h2 else "FAIL"} |',
            f'| H3 BULL/BEAR symmetry | {"YES" if h3_eligible else "NO"} | {fmt(bull.accuracy)} / {fmt(bear.accuracy)} | — | {"PASS" if h3 else "FAIL"} |',
            f'| H4 parent compression continuity | {"YES" if h4_eligible else "NO"} | breakout {fmt(h4_break["observed"])}; range24 {fmt(h4_range["observed"])} | breakout [{fmt(h4_break["ci_lo"])}, {fmt(h4_break["ci_hi"])}] | {"PASS" if h4_pass else "FAIL"} |','',
            '## Side symmetry','',sides.to_markdown(index=False),'',
            '## Fresh-week breakdown','',weeks.to_markdown(index=False),'',
            '## Source / leakage audit','',
            f'- Archive SHA256: `{source_meta["archive_sha256"]}`',
            f'- Source: **{source_meta["manifest"].get("server")} / {source_meta["manifest"].get("symbol")}**',
            f'- Processed raw members: **{source_meta["processed_member_count"]}** ({source_meta["processed_member_first"]} -> {source_meta["processed_member_last"]})',
            f'- Reconstructed M1 rows: **{source_meta["m1_rows"]:,}**, H4 rows: **{source_meta["h4_rows"]:,}**',
            f'- M1 range: **{source_meta["m1_first"]} -> {source_meta["m1_last"]}**','',
            '## Interpretation constraints','',
            '- No pre-2026-07-24 Context observation enters H1/H2/H3.',
            '- D1, D2, D14, G1, ±1 ATR barrier and 8h/24h horizons were frozen before outcomes.',
            '- BID is the only price used; ask/spread cannot affect this semantic test.',
            '- A positive verdict validates human-facing Context semantics only; it does not authorize automated entries or risk changes.']
    (out/'REPORT.md').write_text('\n'.join(report)+'\n')
    print(json.dumps(summary,indent=2,default=str))

if __name__=='__main__':
    main()
