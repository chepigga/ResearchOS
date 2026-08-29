#!/usr/bin/env python3
"""XAU_PRICE_TIME_ALOGICAL_PATH_TRANSITION_LAB_007 V2

Same frozen research protocol as LAB007 v1, vectorized for the 1.28M-row M1
artifact. Signal is price+time only; ATR is causal scaling/risk normalization.

Causality:
- obviousness at t0 uses t0-1 or earlier;
- path transition uses completed bars t0..t0+W-1;
- DIRECT executes first tick t0+W;
- RETEST executes first tick after a completed retest-touch bar;
- outcome label is looked up at the actual later entry minute.

Chronology: 2023-24 discovery -> 2025 validation -> 2026 untouched OOS.
Target: SL 1.25 ATR, TP 2R, H240, LAB001 Bid/Ask-aware labels.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd

SL_ATR=1.25; RR=2.0; H=240; COMMISSION_RATE_SIDE=0.000007
BUY_LABEL='BUY_S1.25_R2_H240'; SELL_LABEL='SELL_S1.25_R2_H240'
WAIT_WINDOWS=(5,10,20,40); RETEST_WINDOWS=(10,20); RETEST_ZONE_ATR=0.10


def parse_args():
    p=argparse.ArgumentParser(); p.add_argument('--bars',type=Path,required=True); p.add_argument('--labels',type=Path,required=True); p.add_argument('--outdir',type=Path,required=True); return p.parse_args()


def pf(r):
    r=np.asarray(r,float); r=r[np.isfinite(r)]
    if not len(r): return None
    gp=float(r[r>0].sum()); gl=float(-r[r<0].sum()); return gp/gl if gl>0 else None


def stats(r):
    r=np.asarray(r,float); r=r[np.isfinite(r)]; n=len(r)
    if n==0: return {'n':0,'mean_R':None,'pf':None,'win_rate':None,'max_dd_R':None,'sum_R':0.0}
    eq=np.cumsum(r); peak=np.maximum.accumulate(np.r_[0.0,eq]); dd=peak[1:]-eq
    return {'n':int(n),'mean_R':float(np.mean(r)),'pf':pf(r),'win_rate':float(np.mean(r>0)),'max_dd_R':float(np.max(dd)) if len(dd) else 0.0,'sum_R':float(np.sum(r))}


def load_data(bp,lp):
    b=pd.read_parquet(bp); l=pd.read_parquet(lp)
    bc=['minute','timestamp_from_time_msc','first_bid','first_ask','mid_open','mid_high','mid_low','mid_close']
    lc=['minute','atr14_causal',BUY_LABEL,SELL_LABEL]
    mb=[c for c in bc if c not in b.columns]; ml=[c for c in lc if c not in l.columns]
    if mb or ml: raise RuntimeError(f'schema mismatch bars={mb} labels={ml}')
    x=b[bc].merge(l[lc],on='minute',how='inner',validate='one_to_one').sort_values('minute').reset_index(drop=True)
    x['year']=pd.to_datetime(x['timestamp_from_time_msc'],errors='coerce').dt.year.astype('Int64')
    return x


def add_obviousness(x):
    d=x.copy(); pc=d.mid_close.shift(1).astype(float); po=d.mid_open.shift(1).astype(float); atr=d.atr14_causal.astype(float)
    hi60=d.mid_high.shift(2).rolling(60,min_periods=60).max(); lo60=d.mid_low.shift(2).rolling(60,min_periods=60).min(); width=(hi60-lo60).replace(0,np.nan); loc=(pc-lo60)/width
    r15=(pc-pc.shift(15))/atr; r60=(pc-pc.shift(60))/atr; sgn=np.sign((pc-po).fillna(0.0)); up5=(sgn>0).astype(int).rolling(5,min_periods=5).sum(); dn5=(sgn<0).astype(int).rolling(5,min_periods=5).sum()
    s=np.zeros(len(d),np.int8)
    s+=(pc>hi60).fillna(False).to_numpy(np.int8); s-=(pc<lo60).fillna(False).to_numpy(np.int8)
    s+=(loc>=.85).fillna(False).to_numpy(np.int8); s-=(loc<=.15).fillna(False).to_numpy(np.int8)
    s+=(r15>=1.0).fillna(False).to_numpy(np.int8); s-=(r15<=-1.0).fillna(False).to_numpy(np.int8)
    s+=(r60>=1.8).fillna(False).to_numpy(np.int8); s-=(r60<=-1.8).fillna(False).to_numpy(np.int8)
    s+=(up5>=4).fillna(False).to_numpy(np.int8); s-=(dn5>=4).fillna(False).to_numpy(np.int8)
    d['crowd_score']=s; d['crowd_dir']=np.sign(s).astype(np.int8); d['score_bucket']=np.where(np.abs(s)>=4,'S4P',np.where(np.abs(s)==3,'S3','LT3')); d['origin']=pc
    return d


def forward_roll(a,w,kind):
    s=pd.Series(a[::-1]); z=(s.rolling(w,min_periods=w).max() if kind=='max' else s.rolling(w,min_periods=w).min()).to_numpy()[::-1]; return z


def label_r_arrays(x, side):
    lab=x[BUY_LABEL if side=='BUY' else SELL_LABEL].to_numpy(float); entry=x['first_ask' if side=='BUY' else 'first_bid'].to_numpy(float); atr=x.atr14_causal.to_numpy(float)
    c=np.divide(2*COMMISSION_RATE_SIDE*entry,SL_ATR*atr,out=np.full(len(x),np.nan),where=np.isfinite(atr)&(atr>0)); r=np.full(len(x),np.nan); r[lab==1]=RR-c[lab==1]; r[lab==-1]=-1.0-c[lab==-1]; r[lab==0]=-c[lab==0]
    return r,lab,c


def retest_idx(high,low,start,max_wait,cdir,origin,atr):
    end=min(len(high)-2,start+max_wait-1); zone=RETEST_ZONE_ATR*atr
    if end<start: return None
    hits=np.flatnonzero(high[start:end+1]>=origin-zone) if cdir>0 else np.flatnonzero(low[start:end+1]<=origin+zone)
    return (start+int(hits[0])+1) if len(hits) else None


def build_transitions(x):
    n=len(x); high=x.mid_high.to_numpy(float); low=x.mid_low.to_numpy(float); close=x.mid_close.to_numpy(float); origin=x.origin.to_numpy(float); atr=x.atr14_causal.to_numpy(float); cdir=x.crowd_dir.to_numpy(np.int8); sb=x.score_bucket.to_numpy(object); mins=x.minute.to_numpy(np.int64); years=x.year.to_numpy(); rb,lb,cb=label_r_arrays(x,'BUY'); rs,ls,cs=label_r_arrays(x,'SELL')
    eligible=np.isin(sb,['S3','S4P']) & (cdir!=0) & np.isfinite(origin) & np.isfinite(atr) & (atr>0); rows=[]
    for w in WAIT_WINDOWS:
        fhi=forward_roll(high,w,'max'); flo=forward_roll(low,w,'min'); endc=np.full(n,np.nan); endc[:n-w+1]=close[w-1:]
        mfe=np.where(cdir>0,(fhi-origin)/atr,(origin-flo)/atr); mae=np.where(cdir>0,(origin-flo)/atr,(fhi-origin)/atr); endp=cdir.astype(float)*(endc-origin)/atr
        code=np.zeros(n,np.int8); m1=eligible & (mfe<.50) & (mae>=.40) & (endp<=-.20); code[m1]=1; m2=eligible & (code==0) & (mfe>=.50) & (endp<=0.0) & ((mfe-endp)>=.60); code[m2]=2; m3=eligible & (code==0) & (mfe>=.80) & (endp<=.20) & ((mfe-endp)>=.80); code[m3]=3
        idx=np.flatnonzero((code>0) & (np.arange(n)+w<n)); print(f'[W{w}] transition origins={len(idx)}',flush=True)
        for k,i in enumerate(idx):
            typ=('NO_REWARD_REJECT' if code[i]==1 else 'FAKE_CONFIRM_RETURN' if code[i]==2 else 'OVEREXTEND_SNAPBACK'); direct=i+w; modes=[('DIRECT',direct)]
            for rw in RETEST_WINDOWS: modes.append((f'RETEST_{rw}',retest_idx(high,low,direct,rw,int(cdir[i]),float(origin[i]),float(atr[i]))))
            for mode,e in modes:
                if e is None or e>=n: continue
                if cdir[i]>0: rinv,robv,il,ol,ic,oc=rs[e],rb[e],ls[e],lb[e],cs[e],cb[e]; invside='SELL'
                else: rinv,robv,il,ol,ic,oc=rb[e],rs[e],lb[e],ls[e],cb[e],cs[e]; invside='BUY'
                if not np.isfinite(rinv) or not np.isfinite(robv): continue
                rows.append({'event_idx':int(i),'event_minute':int(mins[i]),'event_year':int(years[i]),'crowd_dir':int(cdir[i]),'score_bucket':str(sb[i]),'wait_min':int(w),'transition':typ,'origin':float(origin[i]),'atr0':float(atr[i]),'mfe_atr':float(mfe[i]),'mae_atr':float(mae[i]),'end_progress_atr':float(endp[i]),'giveback_atr':float(mfe[i]-endp[i]),'entry_mode':mode,'entry_idx':int(e),'entry_minute':int(mins[e]),'entry_year':int(years[e]),'inverse_side':invside,'r_inverse':float(rinv),'r_obvious':float(robv),'inverse_label':int(il),'obvious_label':int(ol),'inverse_commission_R':float(ic),'obvious_commission_R':float(oc),'cell_id':f'D{int(cdir[i])}|{str(sb[i])}|W{w}|{typ}|{mode}'})
            if k and k%50000==0: print(f'[W{w}] processed={k}',flush=True)
    return pd.DataFrame(rows)


def cooldown(df,minutes=H):
    if df.empty:return df.copy()
    z=df.sort_values('entry_minute'); keep=[]; last=-10**18
    for ix,m in zip(z.index,z.entry_minute.to_numpy(np.int64)):
        if int(m)-last>=minutes: keep.append(ix); last=int(m)
    return z.loc[keep].copy()


def period_stats(t,years):
    rows=[]; d=t[t.entry_year.isin(years)]
    for cid,g in d.groupby('cell_id',sort=True,observed=True):
        z=cooldown(g); si=stats(z.r_inverse.to_numpy(float)); so=stats(z.r_obvious.to_numpy(float)); f=z.iloc[0] if len(z) else g.iloc[0]
        rows.append({'cell_id':cid,'crowd_dir':int(f.crowd_dir),'score_bucket':str(f.score_bucket),'wait_min':int(f.wait_min),'transition':str(f.transition),'entry_mode':str(f.entry_mode),'n':si['n'],'inverse_mean_R':si['mean_R'],'inverse_pf':si['pf'],'inverse_sum_R':si['sum_R'],'obvious_mean_R':so['mean_R'],'obvious_pf':so['pf'],'inversion_gap_R':si['mean_R']-so['mean_R'] if si['mean_R'] is not None and so['mean_R'] is not None else None})
    return pd.DataFrame(rows)


def cell_year(t):
    rows=[]
    for (cid,y),g in t.groupby(['cell_id','entry_year'],sort=True,observed=True):
        z=cooldown(g); si=stats(z.r_inverse.to_numpy(float)); so=stats(z.r_obvious.to_numpy(float)); rows.append({'cell_id':cid,'year':int(y),'n':si['n'],'inverse_mean_R':si['mean_R'],'inverse_pf':si['pf'],'inverse_sum_R':si['sum_R'],'obvious_mean_R':so['mean_R'],'obvious_pf':so['pf'],'inversion_gap_R':si['mean_R']-so['mean_R'] if si['mean_R'] is not None and so['mean_R'] is not None else None})
    return pd.DataFrame(rows)


def choose_locked(tr,va,fi):
    t=tr.add_prefix('train_').rename(columns={'train_cell_id':'cell_id'}); v=va.add_prefix('val_').rename(columns={'val_cell_id':'cell_id'}); f=fi.add_prefix('final_').rename(columns={'final_cell_id':'cell_id'}); m=t.merge(v,on='cell_id',how='outer').merge(f,on='cell_id',how='outer')
    m['discovery_pass']=(m.train_n>=40)&(m.train_inverse_mean_R>=.08)&(m.train_inverse_pf>=1.10)&(m.train_inversion_gap_R>=.12); m['validation_pass']=(m.val_n>=20)&(m.val_inverse_mean_R>0)&(m.val_inverse_pf>1.0)&(m.val_inversion_gap_R>0); m['locked_before_2026']=m.discovery_pass&m.validation_pass; m['final_2026_pass']=(m.final_n>=10)&(m.final_inverse_mean_R>0)&(m.final_inverse_pf>1.0); return m


def portfolio(t,l):
    cells=set(l.loc[l.locked_before_2026,'cell_id'].astype(str));
    if not cells:return pd.DataFrame()
    d=t[t.cell_id.isin(cells)].copy(); rank=l.set_index('cell_id').train_inverse_mean_R.to_dict(); d['train_rank']=d.cell_id.map(rank).fillna(-999.0); d=d.sort_values(['event_idx','train_rank','entry_minute'],ascending=[True,False,True]).drop_duplicates('event_idx').sort_values('entry_minute'); return cooldown(d)


def yearly(p):
    if p.empty:return pd.DataFrame(columns=['year','n','mean_R','pf','win_rate','max_dd_R','sum_R'])
    return pd.DataFrame([{'year':int(y),**stats(g.sort_values('entry_minute').r_inverse.to_numpy(float))} for y,g in p.groupby('entry_year',sort=True)])


def main():
    a=parse_args(); a.outdir.mkdir(parents=True,exist_ok=True); x=add_obviousness(load_data(a.bars,a.labels)); print('rows',len(x),flush=True); t=build_transitions(x); print('raw transitions',len(t),flush=True)
    if t.empty: raise RuntimeError('No transitions generated')
    t.to_parquet(a.outdir/'path_transition_events.parquet',index=False); cell_year(t).to_csv(a.outdir/'cell_year_summary.csv',index=False); tr=period_stats(t,{2023,2024}); va=period_stats(t,{2025}); fi=period_stats(t,{2026}); l=choose_locked(tr,va,fi).sort_values(['locked_before_2026','train_inverse_mean_R','val_inverse_mean_R'],ascending=[False,False,False],na_position='last'); l.to_csv(a.outdir/'candidate_transfer.csv',index=False); diag=period_stats(t,{2023,2024,2025,2026}).sort_values(['inverse_mean_R','n'],ascending=[False,False]); diag.to_csv(a.outdir/'pooled_diagnostic_cells.csv',index=False); p=portfolio(t,l); (p.to_csv(a.outdir/'locked_portfolio_trades.csv',index=False) if not p.empty else None); yearly(p).to_csv(a.outdir/'locked_portfolio_yearly.csv',index=False)
    p26=p[p.entry_year==2026] if not p.empty else pd.DataFrame(); s26=stats(p26.r_inverse.to_numpy(float)) if not p26.empty else stats(np.array([])); lc=int(l.locked_before_2026.sum()); pos=int((l.locked_before_2026&l.final_2026_pass).sum()); verdict='FAIL_NO_TRANSFER' if lc==0 else ('PASS' if s26['n']>=20 and s26['mean_R'] is not None and s26['mean_R']>0 and s26['pf'] is not None and s26['pf']>1.05 else ('WEAK_PASS' if s26['n']>=10 and s26['mean_R'] is not None and s26['mean_R']>0 else 'FAIL_OOS'))
    out={'lab':'XAU_PRICE_TIME_ALOGICAL_PATH_TRANSITION_LAB_007','engine':'V2 vectorized, frozen protocol','rows_input':int(len(x)),'raw_transition_rows':int(len(t)),'unique_origin_events':int(t.event_idx.nunique()),'matrix_cells':int(t.cell_id.nunique()),'locked_cells_before_2026':lc,'locked_cells_positive_in_2026':pos,'final_2026_locked_portfolio':s26,'verdict':verdict,'causality':'obviousness <= t0-1; path through t0+W-1; DIRECT entry t0+W; RETEST entry one minute after completed retest-touch; label at actual entry minute','target':{'sl_atr':SL_ATR,'rr':RR,'horizon_minutes':H}}; (a.outdir/'verdict.json').write_text(json.dumps(out,indent=2)); print(json.dumps(out,indent=2),flush=True)
if __name__=='__main__':main()
