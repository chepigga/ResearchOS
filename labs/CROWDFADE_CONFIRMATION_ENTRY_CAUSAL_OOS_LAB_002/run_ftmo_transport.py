from pathlib import Path
import zipfile, json
import numpy as np
import pandas as pd

ROOT=Path('labs/CROWDFADE_CONFIRMATION_ENTRY_CAUSAL_OOS_LAB_002'); DATA=ROOT/'ftmo_data'; OUT=ROOT/'ftmo_output'; OUT.mkdir(parents=True,exist_ok=True)
CONFIRMS=[0.25,0.35,0.40,0.50]; STOPS=[1.25,1.50]
ZTH=1.0; TTL=10800; PAUSE=10800; HOLD=21600; BE_AT=0.50; BE_LOCK=0.15; TRAIL_ARM=2.50; TRAIL_DIST=0.50
MAY0=int(pd.Timestamp('2026-05-01',tz='UTC').timestamp()); JUN0=int(pd.Timestamp('2026-06-01',tz='UTC').timestamp()); SEP0=int(pd.Timestamp('2026-09-01',tz='UTC').timestamp())

def stats(r,span_s):
    r=np.asarray(r,float)
    if not len(r): return {'N':0}
    eq=np.cumsum(r); pk=np.maximum.accumulate(np.r_[0.,eq]); dd=float((pk[1:]-eq).max()); pos=r[r>0]; neg=r[r<0]
    pf=float(pos.sum()/abs(neg.sum())) if len(neg) else float('inf'); se=r.std(ddof=1)/np.sqrt(len(r)) if len(r)>1 else np.nan; years=span_s/(365.25*86400)
    return {'N':int(len(r)),'WR':float((r>0).mean()),'EV':float(r.mean()),'t':float(r.mean()/se) if se>0 else np.nan,'PF':pf,'SumR':float(r.sum()),'Ryr':float(r.sum()/years),'MaxDD_R':dd,'R_DD':float((r.sum()/years)/dd) if dd>0 else np.nan}

def agg_zip(path):
    parts=[]
    with zipfile.ZipFile(path) as z:
        member=[n for n in z.namelist() if n.lower().endswith('.csv')][0]
        with z.open(member) as f:
            for ch in pd.read_csv(f,usecols=['time_msc','bid','ask'],dtype={'time_msc':'int64','bid':'float32','ask':'float32'},chunksize=1000000):
                ch['sec']=(ch.time_msc//1000).astype('int64')
                g=ch.groupby('sec',sort=False).agg(bid_o=('bid','first'),bid_h=('bid','max'),bid_l=('bid','min'),bid_c=('bid','last'),ask_o=('ask','first'),ask_h=('ask','max'),ask_l=('ask','min'),ask_c=('ask','last')).reset_index()
                parts.append(g)
    d=pd.concat(parts,ignore_index=True).sort_values('sec')
    # merge seconds split across CSV chunks
    d=d.groupby('sec',sort=True).agg(bid_o=('bid_o','first'),bid_h=('bid_h','max'),bid_l=('bid_l','min'),bid_c=('bid_c','last'),ask_o=('ask_o','first'),ask_h=('ask_h','max'),ask_l=('ask_l','min'),ask_c=('ask_c','last')).reset_index()
    return d

def prepare():
    months=[]
    for m in ['05','06','07','08']:
        months.append(agg_zip(DATA/f'TickExport_BTCUSD_2026-{m}.csv.zip'))
    d=pd.concat(months,ignore_index=True).sort_values('sec').drop_duplicates('sec',keep='last').reset_index(drop=True)
    ts=d.sec.to_numpy(np.int64); bo=d.bid_o.to_numpy(float); bh=d.bid_h.to_numpy(float); bl=d.bid_l.to_numpy(float); bc=d.bid_c.to_numpy(float); ao=d.ask_o.to_numpy(float); ah=d.ask_h.to_numpy(float); al=d.ask_l.to_numpy(float); ac=d.ask_c.to_numpy(float)
    # MT5 charts are Bid based: build closed M15 ATR14 from Bid OHLC.
    bucket=(ts//900)*900; starts=np.r_[0,np.flatnonzero(bucket[1:]!=bucket[:-1])+1]; ends=np.r_[starts[1:],len(ts)]
    bt=bucket[starts]; BHi=np.maximum.reduceat(bh,starts); BLi=np.minimum.reduceat(bl,starts); BCi=bc[ends-1]
    pc=np.r_[BCi[0],BCi[:-1]]; tr=np.maximum(BHi-BLi,np.maximum(abs(BHi-pc),abs(BLi-pc))); atr=pd.Series(tr).rolling(14,min_periods=14).mean().to_numpy(); atr_av=bt+900
    # Binance retail-ratio signal source, same frozen z construction.
    zp=DATA/'BTCUSDT_flow_2021-01-2026-08.csv.zip'; out=DATA/'flow_unz'; out.mkdir(exist_ok=True)
    if not list(out.rglob('*.csv')):
        with zipfile.ZipFile(zp) as z:z.extractall(out)
    ff=list(out.rglob('*.csv'))[0]; f=pd.read_csv(ff,usecols=['create_time','sum_open_interest','count_long_short_ratio']); f=f[f.sum_open_interest>0].copy(); f['time']=pd.to_datetime(f.create_time,utc=True,errors='coerce'); f=f.dropna(subset=['time']).sort_values('time').drop_duplicates('time',keep='last')
    ft=f.time.dt.tz_convert(None).to_numpy(dtype='datetime64[s]').astype(np.int64); rr=pd.Series(f.count_long_short_ratio.to_numpy(float)); mm=rr.rolling(72,min_periods=72).mean(); sd=rr.rolling(72,min_periods=72).std(ddof=0); z=((rr-mm)/sd.replace(0,np.nan)).to_numpy()
    # M5 decision boundaries -> first broker second at/after boundary, max 5s late.
    bds=np.arange(((ts[0]+299)//300)*300,ts[-1]+1,300,dtype=np.int64); di=np.searchsorted(ts,bds,'left'); valid=di<len(ts); bds=bds[valid]; di=di[valid]; valid=(ts[di]-bds)<=5; bds=bds[valid]; di=di[valid]; dts=ts[di]
    fi=np.searchsorted(ft,dts,'left')-1; ai=np.searchsorted(atr_av,dts,'right')-1; good=(fi>=0)&(ai>=0)&np.isfinite(z[np.maximum(fi,0)])&np.isfinite(atr[np.maximum(ai,0)])
    return ts,bo,bh,bl,bc,ao,ah,al,ac,ft,z,dts[good],di[good],z[fi[good]],atr[ai[good]]

def manage(A,entry_i,entry,side,a,stop_atr):
    ts,bo,bh,bl,bc,ao,ah,al,ac,ft,z,*_=A; sl=entry-side*stop_atr*a; peak=entry; mfe=0.; armed=False; et=int(ts[entry_i]); end=min(len(ts)-1,int(np.searchsorted(ts,et+HOLD,'left')))
    for j in range(entry_i+1,end+1):
        stop_hit=(ah[j]>=sl) if side<0 else (bl[j]<=sl)
        if stop_hit:
            return j,sl,'trail' if armed else ('be' if ((side<0 and sl<entry) or (side>0 and sl>entry)) else 'stop'),mfe
        px=float(ac[j] if side<0 else bc[j]); prof=(entry-px) if side<0 else (px-entry)
        if prof>=BE_AT*a:
            ns=entry+side*BE_LOCK*a
            if (ns<sl) if side<0 else (ns>sl): sl=ns
        peak=min(peak,px) if side<0 else max(peak,px); mfe=max(mfe,((entry-peak) if side<0 else (peak-entry))/a)
        if mfe>=TRAIL_ARM:
            armed=True; ns=peak+TRAIL_DIST*a if side<0 else peak-TRAIL_DIST*a
            if (ns<sl) if side<0 else (ns>sl): sl=ns
        if ts[j]%300==0:
            q=np.searchsorted(ft,ts[j],'left')-1
            if q>=0 and np.isfinite(z[q]) and ((z[q]<=-ZTH) if side<0 else (z[q]>=ZTH)):
                return j,px,'signal',mfe
        if ts[j]>=et+HOLD:return j,px,'time',mfe
    return end,float(ac[end] if side<0 else bc[end]),'time',mfe

def simulate(A,confirm,stop):
    ts,bo,bh,bl,bc,ao,ah,al,ac,ft,z,dts,di,zdec,adec=A; rows=[]; k=0; next_t=int(dts[0]); armed_n=0; conf_n=0
    while k<len(dts):
        t=int(dts[k])
        if t<next_t:k+=1;continue
        zz=float(zdec[k]); a=float(adec[k]); side=-1 if zz>=ZTH else (1 if zz<=-ZTH else 0)
        if side==0:k+=1;continue
        armed_n+=1; i=int(di[k]); sig=float(bc[i] if side<0 else ac[i]); level=sig+side*confirm*a; end=min(len(ts),int(np.searchsorted(ts,t+TTL,'left'))); st=i+1
        if st>=end: next_t=t+PAUSE;k=np.searchsorted(dts,next_t,'left');continue
        mask=(bl[st:end]<=level) if side<0 else (ah[st:end]>=level); hits=np.flatnonzero(mask)
        if not len(hits): next_t=t+PAUSE;k=np.searchsorted(dts,next_t,'left');continue
        ci=st+int(hits[0]); conf_n+=1; entry=float(bc[ci] if side<0 else ac[ci]); ex,px,kind,mfe=manage(A,ci,entry,side,a,stop); R=side*(px-entry)/(stop*a); spr=float(ac[ci]-bc[ci])/a
        rows.append({'signal_ts':t,'confirm_ts':int(ts[ci]),'exit_ts':int(ts[ex]),'side':'SELL' if side<0 else 'BUY','z':zz,'atr':a,'entry':entry,'exit':px,'R':R,'spread_atr_entry':spr,'kind':kind,'mfe_atr':mfe,'confirm_lag_s':int(ts[ci])-t})
        next_t=max(t+PAUSE,int(ts[ex])+1);k=np.searchsorted(dts,next_t,'left')
    return pd.DataFrame(rows),armed_n,conf_n

def main():
    A=prepare(); out={'data':{'broker':'FTMO-Demo','period':'2026-05-01..2026-08-07','execution':'native bid/ask 1-second aggregation from MT5 ticks','commission':'not included'}}
    res={}
    for c in CONFIRMS:
        for s in STOPS:
            d,armed,confirmed=simulate(A,c,s); key=f'confirm_{c:.2f}_stop_{s:.2f}'; d.to_csv(OUT/f'trades_{key}.csv',index=False)
            may=d[(d.signal_ts>=MAY0)&(d.signal_ts<JUN0)]; dev=d[(d.signal_ts>=JUN0)&(d.signal_ts<SEP0)]
            res[key]={'armed_total':armed,'confirmed_total':confirmed,
                      'May_OOS':stats(may.R.values,JUN0-MAY0),'JunAug_dev':stats(dev.R.values,SEP0-JUN0),
                      'May_spread_atr_median':float(may.spread_atr_entry.median()) if len(may) else np.nan,'May_spread_atr_p95':float(may.spread_atr_entry.quantile(.95)) if len(may) else np.nan,
                      'dev_spread_atr_median':float(dev.spread_atr_entry.median()) if len(dev) else np.nan,'dev_spread_atr_p95':float(dev.spread_atr_entry.quantile(.95)) if len(dev) else np.nan,
                      'May_median_confirm_lag_min':float(may.confirm_lag_s.median()/60) if len(may) else np.nan,'dev_median_confirm_lag_min':float(dev.confirm_lag_s.median()/60) if len(dev) else np.nan}
    out['results']=res; (OUT/'summary_ftmo.json').write_text(json.dumps(out,indent=2,default=float)); print(json.dumps(out,indent=2,default=float))
if __name__=='__main__':main()
