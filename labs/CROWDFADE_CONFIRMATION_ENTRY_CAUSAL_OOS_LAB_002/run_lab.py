from pathlib import Path
import zipfile, json
import numpy as np
import pandas as pd

ROOT=Path('labs/CROWDFADE_CONFIRMATION_ENTRY_CAUSAL_OOS_LAB_002')
DATA=ROOT/'data'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)
ZTH=1.0; SIGNAL_TTL_S=3*3600; PAUSE_S=3*3600; HOLD_S=6*3600
BE_AT=0.50; BE_LOCK=0.15; TRAIL_ARM=2.50; TRAIL_DIST=0.50
CONFIRMS=[0.25,0.35,0.40,0.50]; STOPS=[1.25,1.50]
COST_ATR_HALF=0.027; COST_ATR_FULL=0.054
DEV0=pd.Timestamp('2026-06-01',tz='UTC').timestamp(); DEV1=pd.Timestamp('2026-09-01',tz='UTC').timestamp()
OOS0=pd.Timestamp('2026-03-01',tz='UTC').timestamp(); OOS1=pd.Timestamp('2026-06-01',tz='UTC').timestamp()

def extract(name):
    zp=DATA/name; out=DATA/(zp.stem+'_unz'); out.mkdir(parents=True,exist_ok=True)
    if not list(out.rglob('*.csv')):
        with zipfile.ZipFile(zp) as z:z.extractall(out)
    return list(out.rglob('*.csv'))[0]

def stats(r, span_s):
    r=np.asarray(r,float)
    if len(r)==0:return {'N':0}
    eq=np.cumsum(r); pk=np.maximum.accumulate(np.r_[0.,eq]); dd=float((pk[1:]-eq).max())
    pos=r[r>0]; neg=r[r<0]; pf=float(pos.sum()/abs(neg.sum())) if len(neg) else float('inf')
    se=r.std(ddof=1)/np.sqrt(len(r)) if len(r)>1 else np.nan
    years=span_s/(365.25*86400)
    return {'N':int(len(r)),'WR':float((r>0).mean()),'EV':float(r.mean()),'t':float(r.mean()/se) if se>0 else np.nan,
            'PF':pf,'SumR':float(r.sum()),'Ryr':float(r.sum()/years),'MaxDD_R':dd,
            'R_DD':float((r.sum()/years)/dd) if dd>0 else np.nan}

def prepare():
    secf=extract('BTCUSDT_sec.csv.zip'); flowf=extract('BTCUSDT_flow_2021-01-2026-08.csv.zip')
    s=pd.read_csv(secf,usecols=['ts','o','h','l','c'],dtype={'ts':'int64','o':'float32','h':'float32','l':'float32','c':'float32'})
    s=s.sort_values('ts').drop_duplicates('ts',keep='last').reset_index(drop=True)
    ts=s.ts.to_numpy(np.int64); O=s.o.to_numpy(float); H=s.h.to_numpy(float); L=s.l.to_numpy(float); C=s.c.to_numpy(float)
    bucket=(ts//900)*900; starts=np.r_[0,np.flatnonzero(bucket[1:]!=bucket[:-1])+1]; ends=np.r_[starts[1:],len(ts)]
    bt=bucket[starts]; bh=np.maximum.reduceat(H,starts); bl=np.minimum.reduceat(L,starts); bc=C[ends-1]
    pc=np.r_[bc[0],bc[:-1]]; tr=np.maximum(bh-bl,np.maximum(abs(bh-pc),abs(bl-pc)))
    atr=pd.Series(tr).rolling(14,min_periods=14).mean().to_numpy(); atr_avail=bt+900
    f=pd.read_csv(flowf,usecols=['create_time','sum_open_interest','count_long_short_ratio']); f=f[f.sum_open_interest>0].copy()
    f['time']=pd.to_datetime(f.create_time,utc=True,errors='coerce'); f=f.dropna(subset=['time']).sort_values('time').drop_duplicates('time',keep='last')
    ft=f.time.dt.tz_convert(None).to_numpy(dtype='datetime64[s]').astype(np.int64); rr=pd.Series(f.count_long_short_ratio.to_numpy(float))
    mm=rr.rolling(72,min_periods=72).mean(); sd=rr.rolling(72,min_periods=72).std(ddof=0); z=((rr-mm)/sd.replace(0,np.nan)).to_numpy()
    dts=np.arange(((ts[0]+299)//300)*300,ts[-1]+1,300,dtype=np.int64); di=np.searchsorted(ts,dts,'left')
    ok=(di<len(ts))&(ts[np.minimum(di,len(ts)-1)]==dts); dts=dts[ok]; di=di[ok]
    fi=np.searchsorted(ft,dts,'left')-1; ai=np.searchsorted(atr_avail,dts,'right')-1
    good=(fi>=0)&(ai>=0)&np.isfinite(z[np.maximum(fi,0)])&np.isfinite(atr[np.maximum(ai,0)])
    return ts,O,H,L,C,ft,z,dts[good],di[good],z[fi[good]],atr[ai[good]]

def manage(ts,H,L,C,ft,z,entry_idx,entry,side,a,stop_atr):
    sl=entry-side*stop_atr*a; peak=entry; mfe=0.; armed=False; entry_ts=int(ts[entry_idx]); end=min(len(ts)-1,int(np.searchsorted(ts,entry_ts+HOLD_S,'left')))
    for j in range(entry_idx+1,end+1):
        if (H[j]>=sl) if side<0 else (L[j]<=sl):
            kind='trail' if armed else ('be' if ((side<0 and sl<entry) or (side>0 and sl>entry)) else 'stop')
            return j,sl,kind,mfe
        cp=float(C[j]); prof=(entry-cp) if side<0 else (cp-entry)
        if prof>=BE_AT*a:
            ns=entry+side*BE_LOCK*a
            if (ns<sl) if side<0 else (ns>sl): sl=ns
        peak=min(peak,cp) if side<0 else max(peak,cp)
        mfe=max(mfe,((entry-peak) if side<0 else (peak-entry))/a)
        if mfe>=TRAIL_ARM:
            armed=True; ns=peak+TRAIL_DIST*a if side<0 else peak-TRAIL_DIST*a
            if (ns<sl) if side<0 else (ns>sl): sl=ns
        if ts[j]%300==0:
            q=np.searchsorted(ft,ts[j],'left')-1
            if q>=0 and np.isfinite(z[q]) and ((z[q]<=-ZTH) if side<0 else (z[q]>=ZTH)):
                return j,cp,'signal',mfe
        if ts[j]>=entry_ts+HOLD_S:return j,cp,'time',mfe
    return end,float(C[end]),'time',mfe

def simulate(arr, confirm_atr, stop_atr):
    ts,O,H,L,C,ft,z,dts,di,zdec,adec=arr; rows=[]; k=0; next_t=int(dts[0]); armed_count=0; confirmed=0
    while k<len(dts):
        t=int(dts[k])
        if t<next_t:k+=1;continue
        zz=float(zdec[k]); a=float(adec[k]); side=-1 if zz>=ZTH else (1 if zz<=-ZTH else 0)
        if side==0:k+=1;continue
        armed_count+=1; sig_i=int(di[k]); sig_px=float(O[sig_i]); level=sig_px+side*confirm_atr*a
        expiry=t+SIGNAL_TTL_S; end=min(len(ts),int(np.searchsorted(ts,expiry,'left'))); st=sig_i+1
        if st>=end:
            next_t=t+PAUSE_S;k=np.searchsorted(dts,next_t,'left');continue
        mask=(L[st:end]<=level) if side<0 else (H[st:end]>=level)
        hits=np.flatnonzero(mask)
        if len(hits)==0:
            next_t=t+PAUSE_S;k=np.searchsorted(dts,next_t,'left');continue
        ci=st+int(hits[0]); confirmed+=1
        # causal market proxy: first second close after threshold has been observed
        entry=float(C[ci]); ex,px,kind,mfe=manage(ts,H,L,C,ft,z,ci,entry,side,a,stop_atr)
        gross_R=side*(px-entry)/(stop_atr*a)
        rows.append({'signal_ts':t,'confirm_ts':int(ts[ci]),'exit_ts':int(ts[ex]),'side':'SELL' if side<0 else 'BUY','z':zz,'atr':a,
                     'signal_px':sig_px,'confirm_level':level,'entry':entry,'exit':px,'gross_R':gross_R,
                     'half_cost_R':gross_R-COST_ATR_HALF/stop_atr,'full_cost_R':gross_R-COST_ATR_FULL/stop_atr,
                     'kind':kind,'mfe_atr':mfe,'confirm_lag_s':int(ts[ci])-t})
        next_t=max(t+PAUSE_S,int(ts[ex])+1);k=np.searchsorted(dts,next_t,'left')
    return pd.DataFrame(rows),armed_count,confirmed

def slice_stats(d,t0,t1,stop_atr):
    q=d[(d.signal_ts>=t0)&(d.signal_ts<t1)].copy(); span=t1-t0
    out={'gross':stats(q.gross_R.values,span),'half_cost':stats(q.half_cost_R.values,span),'full_cost':stats(q.full_cost_R.values,span)}
    out['confirm_rate']=float(len(q))/max(1,int(((d.signal_ts>=t0)&(d.signal_ts<t1)).sum())) if len(d) else 0.0
    out['median_confirm_lag_min']=float(q.confirm_lag_s.median()/60) if len(q) else np.nan
    out['exit_kinds']=q.kind.value_counts().to_dict() if len(q) else {}
    return out

def main():
    arr=prepare(); allres={}; dev_rows=[]
    for c in CONFIRMS:
        for s in STOPS:
            d,armed,confirmed=simulate(arr,c,s)
            key=f'confirm_{c:.2f}_stop_{s:.2f}'; d['confirm_atr']=c; d['stop_atr']=s
            d.to_csv(OUT/f'trades_{key}.csv',index=False)
            dev=d[(d.signal_ts>=DEV0)&(d.signal_ts<DEV1)]; oos=d[(d.signal_ts>=OOS0)&(d.signal_ts<OOS1)]
            devstat={'gross':stats(dev.gross_R.values,DEV1-DEV0),'half_cost':stats(dev.half_cost_R.values,DEV1-DEV0),'full_cost':stats(dev.full_cost_R.values,DEV1-DEV0),
                     'N':int(len(dev)),'median_confirm_lag_min':float(dev.confirm_lag_s.median()/60) if len(dev) else np.nan}
            oosstat={'gross':stats(oos.gross_R.values,OOS1-OOS0),'half_cost':stats(oos.half_cost_R.values,OOS1-OOS0),'full_cost':stats(oos.full_cost_R.values,OOS1-OOS0),
                     'N':int(len(oos)),'median_confirm_lag_min':float(oos.confirm_lag_s.median()/60) if len(oos) else np.nan}
            allres[key]={'confirm_atr':c,'stop_atr':s,'armed_total':armed,'confirmed_total':confirmed,'dev_JunAug':devstat,'oos_MarMay':oosstat}
            dev_rows.append((devstat['full_cost'].get('R_DD',-np.inf),key))
    # Selection is made ONLY from Jun-Aug development window, before reading OOS metric.
    dev_rows.sort(reverse=True); selected=dev_rows[0][1]
    out={'design':{'development':'2026-06-01..2026-08-31','oos':'2026-03-01..2026-05-31','selection_rule':'max full-cost R/DD on development only',
                   'confirms':CONFIRMS,'stops':STOPS,'signal_ttl_h':3,'pause_h':3,'hold_h':6,'be_at_atr':BE_AT,'be_lock_atr':BE_LOCK,'trail_arm_atr':TRAIL_ARM,'trail_dist_atr':TRAIL_DIST,
                   'market_entry_proxy':'close of first 1-second bar whose H/L crosses confirmation level','cost_scenarios_atr':[0,COST_ATR_HALF,COST_ATR_FULL]},
         'selected_from_dev':selected,'results':allres}
    # monthly OOS decomposition for the selected dev candidate
    c=allres[selected]['confirm_atr']; s=allres[selected]['stop_atr']; d,_,_=simulate(arr,c,s)
    monthly={}
    for m0,m1,label in [(pd.Timestamp('2026-03-01',tz='UTC').timestamp(),pd.Timestamp('2026-04-01',tz='UTC').timestamp(),'2026-03'),
                        (pd.Timestamp('2026-04-01',tz='UTC').timestamp(),pd.Timestamp('2026-05-01',tz='UTC').timestamp(),'2026-04'),
                        (pd.Timestamp('2026-05-01',tz='UTC').timestamp(),pd.Timestamp('2026-06-01',tz='UTC').timestamp(),'2026-05')]:
        q=d[(d.signal_ts>=m0)&(d.signal_ts<m1)]; monthly[label]={'gross':stats(q.gross_R.values,m1-m0),'half_cost':stats(q.half_cost_R.values,m1-m0),'full_cost':stats(q.full_cost_R.values,m1-m0)}
    out['selected_oos_monthly']=monthly
    (OUT/'summary.json').write_text(json.dumps(out,indent=2,default=float))
    print(json.dumps(out,indent=2,default=float))
if __name__=='__main__':main()
