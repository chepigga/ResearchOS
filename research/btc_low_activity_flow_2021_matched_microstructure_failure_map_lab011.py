import json
from pathlib import Path
import numpy as np
import pandas as pd
import btc_low_activity_flow_alignment_flip_lab008 as lab8
import btc_low_activity_flow_2021_failure_regime_causal_map_lab010 as lab10

LAB='BTC_LOW_ACTIVITY_FLOW_2021_MATCHED_MICROSTRUCTURE_FAILURE_MAP_LAB_011'
FAIL_YEAR=2021
REF_YEARS=[2020,2022,2023,2024,2025]
W=(3,6,12,24); K=3; B=4000; SEED=20260826
MATCH=['rv_7d_daily_pct','rv_prev23d_daily_pct','rv_7d_vs_prev23d','trend_eff_7d','trend_signed_7d_atr','directional_position_30d','flow_delta_prev23d','break_distance_atr','stop_atr','atr_regime_ratio']
PAIRS=[('price_response_per_flow_6','aligned_flow_no_result_share_6'),('flow_churn_12','price_efficiency_12'),('flow_persistence_12','price_response_per_flow_12'),('future_wick_ratio_12','aligned_flow_no_result_share_12'),('flow_flip_rate_12','price_response_per_flow_12'),('response_shift_3v12','no_result_shift_3v12')]

def wm(x,w):
    x=np.asarray(x,float); w=np.asarray(w,float); q=np.isfinite(x)&np.isfinite(w)&(w>=0)
    return float(np.sum(x[q]*w[q])/np.sum(w[q])) if q.any() and np.sum(w[q])>0 else np.nan

def mw(m,i,d,atr,n):
    if i-n<2 or not np.isfinite(atr) or atr<=0:return {}
    x=m.iloc[i-n:i]; O=x.open.to_numpy(float); H=x.high.to_numpy(float); L=x.low.to_numpy(float); C=x.close.to_numpy(float); V=x.volume.to_numpy(float); Q=np.clip(x.taker_ratio.to_numpy(float),0,1); R=np.maximum(H-L,1e-12)
    bf=d*(2*Q-1); tv=max(float(V.sum()),1e-12); fd=float(np.sum(V*bf)/tv); effort=float(np.sum(V*np.abs(bf))/tv)
    prog=float(d*(C[-1]-C[0])/atr); path=float(np.abs(np.diff(C)).sum()/atr); eff=prog/path if path>1e-12 else 0.0
    body=d*(C-O)/atr; br=d*(C-O)/R; aligned=bf>0
    pers=wm(aligned.astype(float),V); flips=float(np.mean((np.sign(bf[1:])*np.sign(bf[:-1])<0).astype(float))) if len(bf)>1 else 0.0
    churn=min(20.,effort/max(abs(fd),.02)); resp=float(np.clip(prog/max(abs(fd),.02),-20,20)); epp=float(np.clip(effort/max(abs(prog),.10),0,20))
    nores=wm((body<=0).astype(float)[aligned],V[aligned]) if aligned.any() else 0.0; adverse=wm(np.maximum(-body[aligned],0),V[aligned]) if aligned.any() else 0.0
    corr=float(np.corrcoef(bf,body)[0,1]) if np.std(bf)>1e-12 and np.std(body)>1e-12 else 0.0
    uw=np.maximum(H-np.maximum(O,C),0)/R; lw=np.maximum(np.minimum(O,C)-L,0)/R; fw=uw if d>0 else lw; cw=lw if d>0 else uw; cl=(C-L)/R if d>0 else (H-C)/R
    fp=[]; fwp=[]
    for k in range(2,len(C)):
        if bf[k]<=0:continue
        fail=C[k]<=max(C[k-1],C[k-2]) if d>0 else C[k]>=min(C[k-1],C[k-2]); fp.append(float(fail)); fwp.append(float(V[k]))
    fps=wm(fp,fwp) if fp else 0.0; bodyresp=wm(br,V); div=float(fd-(bodyresp if np.isfinite(bodyresp) else 0.0))
    return {f'flow_delta_micro_{n}':fd,f'flow_persistence_{n}':pers,f'flow_flip_rate_{n}':flips,f'flow_churn_{n}':churn,f'price_progress_atr_{n}':prog,f'price_efficiency_{n}':eff,f'price_response_per_flow_{n}':resp,f'flow_effort_per_progress_{n}':epp,f'aligned_flow_no_result_share_{n}':nores,f'aligned_flow_adverse_body_atr_{n}':adverse,f'flow_price_bar_corr_{n}':corr,f'future_wick_ratio_{n}':float(np.mean(fw)),f'counter_wick_ratio_{n}':float(np.mean(cw)),f'directional_body_range_{n}':float(np.mean(br)),f'directional_close_location_{n}':float(np.mean(cl)),f'failed_push_share_{n}':fps,f'flow_price_divergence_{n}':div}

def add_micro(m,e):
    rows=[]
    for r in e.itertuples():
        z={}
        for n in W:z.update(mw(m,int(r.bar_index),int(r.direction),float(r.atr),n))
        z.update(response_shift_3v12=z['price_response_per_flow_3']-z['price_response_per_flow_12'],response_shift_6v24=z['price_response_per_flow_6']-z['price_response_per_flow_24'],no_result_shift_3v12=z['aligned_flow_no_result_share_3']-z['aligned_flow_no_result_share_12'],persistence_shift_3v12=z['flow_persistence_3']-z['flow_persistence_12'],churn_shift_3v12=z['flow_churn_3']-z['flow_churn_12'],efficiency_shift_3v12=z['price_efficiency_3']-z['price_efficiency_12'],failed_push_shift_3v12=z['failed_push_share_3']-z['failed_push_share_12'],wick_shift_3v12=z['future_wick_ratio_3']-z['future_wick_ratio_12']); rows.append(z)
    x=e.reset_index(drop=True).copy(); z=pd.DataFrame(rows)
    for c in z.columns:x[c]=z[c].to_numpy()
    return x

def mfeatures(cols):
    p=('flow_delta_micro_','flow_persistence_','flow_flip_rate_','flow_churn_','price_progress_atr_','price_efficiency_','price_response_per_flow_','flow_effort_per_progress_','aligned_flow_no_result_share_','aligned_flow_adverse_body_atr_','flow_price_bar_corr_','future_wick_ratio_','counter_wick_ratio_','directional_body_range_','directional_close_location_','failed_push_share_','flow_price_divergence_')
    extra={'response_shift_3v12','response_shift_6v24','no_result_shift_3v12','persistence_shift_3v12','churn_shift_3v12','efficiency_shift_3v12','failed_push_shift_3v12','wick_shift_3v12'}
    return [c for c in cols if c.startswith(p) or c in extra]

def refscale(r,fs):
    med={}; sd={}
    for f in fs:
        z=pd.to_numeric(r[f],errors='coerce'); med[f]=float(z.median()); s=float(z.std(ddof=0)); sd[f]=s if np.isfinite(s) and s>1e-9 else 1.
    return med,sd

def vec(row,fs,med,sd):
    return np.array([((float(row[f]) if np.isfinite(row[f]) else med[f])-med[f])/sd[f] for f in fs],float)

def match(f,r):
    med,sd=refscale(r,MATCH); R=np.vstack([vec(x,MATCH,med,sd) for _,x in r.iterrows()]); ri=r.index.to_numpy(); out=[]
    for fi,x in f.iterrows():
        mask=(r.direction.to_numpy(int)==int(x.direction))&(r.low_activity_score.to_numpy(int)==int(x.low_activity_score)); fb=0
        if mask.sum()<K:mask=r.direction.to_numpy(int)==int(x.direction); fb=1
        pos=np.where(mask)[0]; dist=np.sqrt(np.mean((R[pos]-vec(x,MATCH,med,sd))**2,axis=1)); take=np.argsort(dist)[:min(K,len(pos))]
        for rank,q in enumerate(take,1):out.append(dict(fail_index=int(fi),control_index=int(ri[pos[q]]),rank=rank,distance=float(dist[q]),fallback_direction_only=fb))
    return pd.DataFrame(out)

def control_mean(matches,r,f):
    return {int(fi):float(pd.to_numeric(r.loc[g.control_index.to_numpy(int),f],errors='coerce').mean()) for fi,g in matches.groupby('fail_index')}

def bh(p):
    p=np.asarray(p,float); q=np.full(len(p),np.nan); idx=np.where(np.isfinite(p))[0]
    if not len(idx):return q
    order=idx[np.argsort(p[idx])]; raw=np.array([p[j]*len(order)/(i+1) for i,j in enumerate(order)]); raw=np.minimum.accumulate(raw[::-1])[::-1]
    for j,v in zip(order,np.clip(raw,0,1)):q[j]=v
    return q

def paired(f,r,mt,fs):
    rng=np.random.default_rng(SEED); rows=[]
    for feat in fs:
        cm=control_mean(mt,r,feat); dif=[]; av=[]; cv=[]
        for fi,x in f.iterrows():
            a=float(x[feat]) if pd.notna(x[feat]) else np.nan; c=cm.get(int(fi),np.nan)
            if np.isfinite(a) and np.isfinite(c):dif.append(a-c); av.append(a); cv.append(c)
        dif=np.asarray(dif,float)
        if len(dif)<8:continue
        bm=np.array([np.mean(dif[rng.integers(0,len(dif),len(dif))]) for _ in range(B)]); p=min(1.,2*min(np.mean(bm<=0),np.mean(bm>=0))); rsd=float(pd.to_numeric(r[feat],errors='coerce').std(ddof=0)); md=float(dif.mean())
        rows.append(dict(feature=feat,n_pairs=len(dif),fail_mean=float(np.mean(av)),matched_control_mean=float(np.mean(cv)),mean_diff=md,median_pair_diff=float(np.median(dif)),effect_z=md/rsd if rsd>1e-12 else np.nan,boot_ci_lo=float(np.quantile(bm,.025)),boot_ci_hi=float(np.quantile(bm,.975)),boot_p_two_sided=p))
    z=pd.DataFrame(rows)
    if len(z):z['fdr_q']=bh(z.boot_p_two_sided); z['abs_effect_z']=z.effect_z.abs(); z=z.sort_values(['fdr_q','abs_effect_z'],ascending=[True,False])
    return z

def match_diag(f,r,mt):
    rows=[]
    for feat in MATCH:
        a=pd.to_numeric(f[feat],errors='coerce').to_numpy(float); b=pd.to_numeric(r[feat],errors='coerce').to_numpy(float); cm=control_mean(mt,r,feat); c=np.array([cm.get(int(i),np.nan) for i in f.index]); sd=np.nanstd(b); pre=(np.nanmean(a)-np.nanmean(b))/sd; post=(np.nanmean(a)-np.nanmean(c))/sd
        rows.append(dict(feature=feat,pre_smd=pre,post_smd=post,abs_pre_smd=abs(pre),abs_post_smd=abs(post)))
    return pd.DataFrame(rows)

def outcome(f,r,mt):
    cl=[]; cf=[]
    for _,g in mt.groupby('fail_index'):
        idx=g.control_index.to_numpy(int); cl.append(float(r.loc[idx,'is_large'].mean())); cf.append(float(r.loc[idx,'is_fail'].mean()))
    return dict(failure_n=len(f),failure_large=int(f.is_large.sum()),failure_large_rate=float(f.is_large.mean()),failure_fail_rate=float(f.is_fail.mean()),reference_n=len(r),reference_large_rate=float(r.is_large.mean()),reference_fail_rate=float(r.is_fail.mean()),matched_units=len(cl),matched_control_large_rate=float(np.mean(cl)),matched_control_fail_rate=float(np.mean(cf)),matched_large_gap_pp=100*(float(f.is_large.mean())-float(np.mean(cl))))

def cuts(r,fs):
    out={}
    for feat in fs:
        z=pd.to_numeric(r[feat],errors='coerce').dropna()
        if len(z)>=10:out[feat]=(float(z.quantile(1/3)),float(z.quantile(2/3)))
    return out

def binv(v,c):return 'NA' if not np.isfinite(v) else ('LOW' if v<=c[0] else 'MID' if v<=c[1] else 'HIGH')

def decomp(f,r,fs,cs):
    actual=float(f.is_large.mean()); rr=float(r.is_large.mean()); gap=rr-actual; maps=[]; dec=[]
    for feat in fs:
        if feat not in cs:continue
        fb=pd.Series([binv(float(v),cs[feat]) for v in f[feat]],index=f.index); rb=pd.Series([binv(float(v),cs[feat]) for v in r[feat]],index=r.index); exp=0.; cov=0
        for cell in ('LOW','MID','HIGH'):
            fm=fb==cell; rm=rb==cell; fn=int(fm.sum()); rn=int(rm.sum()); fr=float(f.loc[fm,'is_large'].mean()) if fn else np.nan; cr=float(r.loc[rm,'is_large'].mean()) if rn else np.nan
            maps.append(dict(feature=feat,cell=cell,fail_n=fn,ref_n=rn,fail_occupancy=fn/len(f),ref_occupancy=rn/len(r),fail_large_rate=fr,ref_large_rate=cr,conditional_gap_pp=100*(fr-cr) if np.isfinite(fr) and np.isfinite(cr) else np.nan,cut_lo=cs[feat][0],cut_hi=cs[feat][1]))
            if fn and rn:exp+=(fn/len(f))*cr; cov+=fn
        if cov:
            coverage=cov/len(f); ex=exp/coverage; dec.append(dict(family=feat,dimensions=1,fail_rate=actual,ref_rate=rr,expected_fail_rate_if_ref_cell_rates=ex,occupancy_effect_pp=100*(ex-rr),residual_failure_pp=100*(actual-ex),total_failure_gap_pp=100*(actual-rr),occupancy_explained_fraction=(rr-ex)/gap if abs(gap)>1e-12 else np.nan,fail_coverage=coverage))
    z=pd.DataFrame(dec); z=z.sort_values('occupancy_explained_fraction',ascending=False) if len(z) else z
    return pd.DataFrame(maps),z

def pair_decomp(f,r,cs):
    actual=float(f.is_large.mean()); rr=float(r.is_large.mean()); gap=rr-actual; maps=[]; dec=[]
    for a,b in PAIRS:
        if a not in cs or b not in cs:continue
        fa=pd.Series([binv(float(v),cs[a]) for v in f[a]],index=f.index); fb=pd.Series([binv(float(v),cs[b]) for v in f[b]],index=f.index); ra=pd.Series([binv(float(v),cs[a]) for v in r[a]],index=r.index); rb=pd.Series([binv(float(v),cs[b]) for v in r[b]],index=r.index); exp=0.; cov=0; fam=a+'__X__'+b
        for ca in ('LOW','MID','HIGH'):
            for cb in ('LOW','MID','HIGH'):
                fm=(fa==ca)&(fb==cb); rm=(ra==ca)&(rb==cb); fn=int(fm.sum()); rn=int(rm.sum()); fr=float(f.loc[fm,'is_large'].mean()) if fn else np.nan; cr=float(r.loc[rm,'is_large'].mean()) if rn else np.nan
                maps.append(dict(family=fam,cell=ca+'|'+cb,fail_n=fn,ref_n=rn,fail_occupancy=fn/len(f),ref_occupancy=rn/len(r),fail_large_rate=fr,ref_large_rate=cr,conditional_gap_pp=100*(fr-cr) if np.isfinite(fr) and np.isfinite(cr) else np.nan))
                if fn and rn>=5:exp+=(fn/len(f))*cr; cov+=fn
        if cov:
            coverage=cov/len(f); ex=exp/coverage; dec.append(dict(family=fam,dimensions=2,fail_rate=actual,ref_rate=rr,expected_fail_rate_if_ref_cell_rates=ex,occupancy_effect_pp=100*(ex-rr),residual_failure_pp=100*(actual-ex),total_failure_gap_pp=100*(actual-rr),occupancy_explained_fraction=(rr-ex)/gap if abs(gap)>1e-12 else np.nan,fail_coverage=coverage))
    z=pd.DataFrame(dec); z=z.sort_values('occupancy_explained_fraction',ascending=False) if len(z) else z
    return pd.DataFrame(maps),z

def main():
    m,sig,e=lab8.build_all_events(); discovery=e[(e.signal_time>=lab8.DISCOVERY_START)&(e.signal_time<=lab8.DISCOVERY_END)].copy(); thr=lab8.freeze_thresholds(discovery); x=lab8.apply_frozen_state(e,thr); x=lab10.add_slow_regime_features(m,x); base=x[(x.low_activity_score>=2)&(x.flow_align_12==1)].copy().reset_index(drop=True); base=add_micro(m,base); mf=mfeatures(base.columns)
    f=base[base.year==FAIL_YEAR].copy(); r=base[base.year.isin(REF_YEARS)].copy(); f.index=np.arange(len(f)); r.index=np.arange(len(r)); mt=match(f,r); pdiff=paired(f,r,mt,mf); md=match_diag(f,r,mt); os=outcome(f,r,mt); cs=cuts(r,mf); fmap,sdec=decomp(f,r,mf,cs); pmap,pdec=pair_decomp(f,r,cs)
    print('='*92); print(LAB); print('EVENTS',len(e),'BASE LOW2_X_ALIGN',len(base)); print('OUTCOME',os); print('IMPORTANT all candidate microstructure windows end at i-1; BOS bar excluded.'); print('MATCH DISTANCE',{'pairs':len(mt),'unique_controls':int(mt.control_index.nunique()),'p50':float(mt.distance.median()),'p90':float(mt.distance.quantile(.9)),'max':float(mt.distance.max()),'fallback_pairs':int(mt.fallback_direction_only.sum())}); print('\nMATCH QUALITY'); print(md.sort_values('abs_post_smd',ascending=False).to_string(index=False)); print('\nTOP MATCHED MICRO DIFFERENCES'); print(pdiff.head(25).to_string(index=False)); print('\nSINGLE DECOMPOSITION'); print(sdec.head(20).to_string(index=False)); print('\nPAIR DECOMPOSITION'); print(pdec.to_string(index=False))
    strong=int((pdiff.fdr_q<=.10).sum()) if len(pdiff) else 0; bp=pdec.iloc[0].to_dict() if len(pdec) else {}; bs=sdec.iloc[0].to_dict() if len(sdec) else {}; st=pdiff.iloc[0].to_dict() if len(pdiff) else {}; pe=float(bp.get('occupancy_explained_fraction',np.nan)) if bp else np.nan; pc=float(bp.get('fail_coverage',0)) if bp else 0
    vc='MATCHED_MICROSTRUCTURE_STRONGLY_MAPS_2021_FAILURE_DISCOVERY_ONLY' if np.isfinite(pe) and pe>=.70 and pc>=.80 and strong>=2 else ('MATCHED_MICROSTRUCTURE_PARTIALLY_MAPS_2021_FAILURE_DISCOVERY_ONLY' if ((np.isfinite(pe) and pe>=.35 and pc>=.75) or strong>=2) else 'TESTED_MATCHED_MICROSTRUCTURE_PROXIES_DO_NOT_EXPLAIN_MOST_2021_FAILURE')
    verdict={'lab':LAB,'question':'After slow/structural matching, what pre-BOS microstructure proxy differs in the 2021 LOW2_X_ALIGN failure?','base_selector':'LOW_ACTIVITY_SCORE>=2 AND FLOW_DELTA_12>0','target':'clean MFE >= 2.5R within 32 M15 bars before structural SL','failure_year':FAIL_YEAR,'reference_years':REF_YEARS,'causality':'candidate microstructure features end at i-1; BOS candle/post-BOS excluded','matching':{'exact_strata':'direction + low_activity_score, fallback direction only','k_controls':K,'features':MATCH,'pairs':len(mt),'unique_controls':int(mt.control_index.nunique()),'distance_p50':float(mt.distance.median()),'distance_p90':float(mt.distance.quantile(.9)),'fallback_pairs':int(mt.fallback_direction_only.sum())},'outcome':os,'strongest_matched_micro_difference':st,'matched_features_fdr_q_le_0_10':strong,'best_single_micro_occupancy_decomposition':bs,'best_pair_micro_occupancy_decomposition':bp,'verdict_class':vc,'warning':'Discovery-only historical causal map. Freeze and replicate any veto/router on untouched data before production.'}
    print('\nVERDICT'); print(json.dumps(verdict,indent=2)); out=Path('lab011'); out.mkdir(exist_ok=True); base.to_csv(out/f'{LAB}_BASE_EVENTS.csv',index=False); f.to_csv(out/f'{LAB}_FAILURE_2021_EVENTS.csv',index=False); r.to_csv(out/f'{LAB}_REFERENCE_EVENTS.csv',index=False); mt.to_csv(out/f'{LAB}_MATCHES.csv',index=False); pdiff.to_csv(out/f'{LAB}_MATCHED_MICRO_DIFFERENCES.csv',index=False); md.to_csv(out/f'{LAB}_MATCH_DIAGNOSTICS.csv',index=False); fmap.to_csv(out/f'{LAB}_SINGLE_FEATURE_CELL_MAP.csv',index=False); sdec.to_csv(out/f'{LAB}_SINGLE_FEATURE_DECOMPOSITION.csv',index=False); pmap.to_csv(out/f'{LAB}_PAIR_CELL_MAP.csv',index=False); pdec.to_csv(out/f'{LAB}_PAIR_DECOMPOSITION.csv',index=False); (out/'verdict.json').write_text(json.dumps(verdict,indent=2),encoding='utf-8'); report=[f'# {LAB}','','All candidate microstructure windows end at i-1; BOS/post-BOS are excluded.','',f'Outcome: `{json.dumps(os)}`','', '## Match diagnostics','',md.sort_values('abs_post_smd',ascending=False).to_markdown(index=False),'','## Top matched differences','',pdiff.head(30).to_markdown(index=False),'','## Single decomposition','',sdec.head(25).to_markdown(index=False),'','## Pair decomposition','',pdec.to_markdown(index=False),'','## Verdict','',f'```json\n{json.dumps(verdict,indent=2)}\n```']; (out/f'{LAB}_REPORT.md').write_text('\n'.join(report),encoding='utf-8')
if __name__=='__main__':main()
