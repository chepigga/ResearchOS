from pathlib import Path
import zipfile,json
import numpy as np
import pandas as pd
ROOT=Path('labs/CROWDFADE_CONFIRMATION_ENTRY_CAUSAL_OOS_LAB_002'); DATA=ROOT/'tz_data'; OUT=ROOT/'tz_output'; OUT.mkdir(parents=True,exist_ok=True)

def ftmo_m1(zpath):
    parts=[]
    with zipfile.ZipFile(zpath) as z:
        member=[n for n in z.namelist() if n.lower().endswith('.csv')][0]
        with z.open(member) as f:
            for ch in pd.read_csv(f,usecols=['time_msc','bid','ask'],dtype={'time_msc':'int64','bid':'float32','ask':'float32'},chunksize=1000000):
                ch['minute']=(ch.time_msc//60000).astype('int64'); ch['mid']=(ch.bid+ch.ask)/2
                parts.append(ch.groupby('minute',sort=False).agg(mid=('mid','last')).reset_index())
    d=pd.concat(parts,ignore_index=True).sort_values('minute').groupby('minute',sort=True).agg(mid=('mid','last')).reset_index(); d['server_time']=pd.to_datetime(d.minute*60,unit='s',utc=True)
    return d[['server_time','mid']]

def binance_m1(zpath):
    parts=[]
    with zipfile.ZipFile(zpath) as z:
        member=[n for n in z.namelist() if n.lower().endswith('.csv')][0]
        with z.open(member) as f:
            for ch in pd.read_csv(f,usecols=['ts','c'],dtype={'ts':'int64','c':'float32'},chunksize=1500000):
                ch['minute']=(ch.ts//60).astype('int64')
                parts.append(ch.groupby('minute',sort=False).agg(close=('c','last')).reset_index())
    d=pd.concat(parts,ignore_index=True).sort_values('minute').groupby('minute',sort=True).agg(close=('close','last')).reset_index(); d['time']=pd.to_datetime(d.minute*60,unit='s',utc=True)
    return d[['time','close']]

def score(ft,bn,offset_min):
    a=ft.copy(); a['time']=a.server_time-pd.to_timedelta(offset_min,unit='m'); m=a[['time','mid']].merge(bn,on='time',how='inner')
    if len(m)<1000:return {'offset_min':offset_min,'N':len(m),'corr':np.nan,'price_ratio_cv':np.nan}
    rb=np.diff(np.log(m.close.to_numpy(float))); rf=np.diff(np.log(m.mid.to_numpy(float))); good=np.isfinite(rb)&np.isfinite(rf)
    corr=float(np.corrcoef(rb[good],rf[good])[0,1]); ratio=m.mid.to_numpy(float)/m.close.to_numpy(float)
    return {'offset_min':offset_min,'N':int(len(m)),'corr':corr,'price_ratio_cv':float(np.std(ratio)/np.mean(ratio)),'ratio_median':float(np.median(ratio))}

def main():
    ft=ftmo_m1(DATA/'TickExport_BTCUSD_2026-05.csv.zip'); bn=binance_m1(DATA/'BTCUSDT_sec.csv.zip')
    lo=pd.Timestamp('2026-05-01',tz='UTC'); hi=pd.Timestamp('2026-06-01',tz='UTC'); bn=bn[(bn.time>=lo-pd.Timedelta(hours=8))&(bn.time<hi+pd.Timedelta(hours=8))]
    coarse=[score(ft,bn,x) for x in range(-360,361,15)]; valid=[x for x in coarse if np.isfinite(x['corr'])]; best=max(valid,key=lambda r:r['corr']); center=best['offset_min']
    fine=[score(ft,bn,x) for x in range(center-20,center+21)]; allr=sorted([x for x in coarse+fine if np.isfinite(x['corr'])],key=lambda r:r['corr'],reverse=True)
    out={'interpretation':'FTMO_UTC = MT5_server_timestamp - offset_min','best':allr[0],'top20':allr[:20]}; (OUT/'alignment.json').write_text(json.dumps(out,indent=2)); pd.DataFrame(allr).to_csv(OUT/'alignment_surface.csv',index=False); print(json.dumps(out,indent=2))
if __name__=='__main__':main()
