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
                ch['minute']=(ch.time_msc//60000).astype('int64')
                ch['mid']=(ch.bid+ch.ask)/2
                g=ch.groupby('minute',sort=False).agg(mid=('mid','last')).reset_index();parts.append(g)
    d=pd.concat(parts,ignore_index=True).sort_values('minute').groupby('minute',sort=True).agg(mid=('mid','last')).reset_index()
    d['server_time']=pd.to_datetime(d.minute*60,unit='s',utc=True)
    return d[['server_time','mid']]

def binance_m1(zpath):
    out=DATA/'b1_unz';out.mkdir(exist_ok=True)
    if not list(out.rglob('*.csv')):
        with zipfile.ZipFile(zpath) as z:z.extractall(out)
    f=list(out.rglob('*.csv'))[0]; d=pd.read_csv(f)
    if 'time' in d.columns:
        t=pd.to_datetime(d['time'],errors='coerce',utc=True)
    elif 'open_time' in d.columns:
        x=d.open_time
        if np.issubdtype(x.dtype,np.number):t=pd.to_datetime(x,unit='ms',errors='coerce',utc=True)
        else:t=pd.to_datetime(x,errors='coerce',utc=True)
    else: raise RuntimeError(f'unknown columns {d.columns.tolist()}')
    close_col='close' if 'close' in d.columns else 'c'
    q=pd.DataFrame({'time':t,'close':pd.to_numeric(d[close_col],errors='coerce')}).dropna().sort_values('time').drop_duplicates('time')
    return q

def score(ft,bn,offset_min):
    a=ft.copy();a['time']=a.server_time-pd.to_timedelta(offset_min,unit='m')
    m=a[['time','mid']].merge(bn,on='time',how='inner');
    if len(m)<1000:return {'offset_min':offset_min,'N':len(m),'corr':np.nan,'price_ratio_cv':np.nan}
    rb=np.diff(np.log(m.close.to_numpy(float))); rf=np.diff(np.log(m.mid.to_numpy(float))); good=np.isfinite(rb)&np.isfinite(rf)
    corr=float(np.corrcoef(rb[good],rf[good])[0,1]); ratio=m.mid.to_numpy(float)/m.close.to_numpy(float); cv=float(np.std(ratio)/np.mean(ratio))
    return {'offset_min':offset_min,'N':int(len(m)),'corr':corr,'price_ratio_cv':cv,'ratio_median':float(np.median(ratio))}

def main():
    ft=ftmo_m1(DATA/'TickExport_BTCUSD_2026-05.csv.zip');bn=binance_m1(DATA/'btc_1m.zip')
    lo=pd.Timestamp('2026-05-01',tz='UTC');hi=pd.Timestamp('2026-06-01',tz='UTC');bn=bn[(bn.time>=lo-pd.Timedelta(hours=8))&(bn.time<hi+pd.Timedelta(hours=8))]
    coarse=[score(ft,bn,x) for x in range(-360,361,15)]; best=max(coarse,key=lambda r:-999 if not np.isfinite(r['corr']) else r['corr']); center=best['offset_min']
    fine=[score(ft,bn,x) for x in range(center-20,center+21)]; allr=sorted(coarse+fine,key=lambda r:-999 if not np.isfinite(r['corr']) else r['corr'],reverse=True)
    out={'interpretation':'FTMO_UTC = MT5_server_timestamp - offset_min','best':allr[0],'top20':allr[:20]};(OUT/'alignment.json').write_text(json.dumps(out,indent=2));pd.DataFrame(allr).to_csv(OUT/'alignment_surface.csv',index=False);print(json.dumps(out,indent=2))
if __name__=='__main__':main()
