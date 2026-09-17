from pathlib import Path
import zipfile, json, itertools
import numpy as np
import pandas as pd

ROOT=Path('labs/CROWDFADE_EXECUTION_5Y_POSITIVE_LAB_005')
DATA=ROOT/'data'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)
ZTH=2.50; EXIT_Z=0.75; MAX_TRADES_DAY=3; COST_RT_BPS=5.0
YEARS=[2021,2022,2023,2024,2025]
CONFIRMS=[0.25,0.35,0.50,0.65]
TTLS=[1,3,6]
ENTRY_MODES=['touch','confirm_close','next_open','pullback_025','pullback_050']
STOPS=[1.0,1.25,1.50,1.75,2.0]
HOLDS=[3,6,12]
PAUSES=['none','time3h','atr1']
BE_TRAIL=[('none',None,None,None,None),('be05',0.50,0.15,None,None),('be075',0.75,0.15,None,None),('be10',1.00,0.25,None,None),('be05_tr20',0.50,0.15,2.00,0.50),('be05_tr25',0.50,0.15,2.50,0.50),('be075_tr20',0.75,0.15,2.00,0.50)]

def unzip_one(name):
    p=DATA/name; d=DATA/(p.stem+'_unz'); d.mkdir(parents=True,exist_ok=True)
    if not list(d.rglob('*.csv')):
        with zipfile.ZipFile(p) as z:z.extractall(d)
    return list(d.rglob('*.csv'))[0]

def pick(df,names):
    low={str(c).lower():c for c in df.columns}
    for n in names:
        if n.lower() in low:return low[n.lower()]
    for c in df.columns:
        lc=str(c).lower()
        if any(n.lower() in lc for n in names):return c
    raise KeyError((names,list(df.columns)))

def parse_time(s):
    x=pd.to_numeric(s,errors='coerce')
    frac=float(x.notna().mean())
    if frac>0.95:
        med=float(x.dropna().median()); unit='ms' if med>1e11 else 's'
        return pd.to_datetime(x,unit=unit,utc=True,errors='coerce')
    return pd.to_datetime(s.astype(str),utc=True,errors='coerce')

def load_price():
    f=unzip_one('btc_5m.zip'); raw=pd.read_csv(f)
    tc=pick(raw,['open_time','timestamp','time','date','datetime']); oc=pick(raw,['open']); hc=pick(raw,['high']); lc=pick(raw,['low']); cc=pick(raw,['close'])
    dt=parse_time(raw[tc])
    d=pd.DataFrame({'time':dt,'o':pd.to_numeric(raw[oc],errors='coerce'),'h':pd.to_numeric(raw[hc],errors='coerce'),'l':pd.to_numeric(raw[lc],errors='coerce'),'c':pd.to_numeric(raw[cc],errors='coerce')}).dropna().sort_values('time').drop_duplicates('time')
    return d[(d.time>='2021-01-01')&(d.time<'2026-09-01')].reset_index(drop=True)

def load_flow():
    f=unzip_one('BTCUSDT_flow_2021-01-2026-08.csv.zip'); raw=pd.read_csv(f)
    tc=pick(raw,['create_time','time','timestamp']); rc=pick(raw,['count_long_short_ratio','long_short_ratio'])
    if 'sum_open_interest' in raw.columns:raw=raw[pd.to_numeric(raw['sum_open_interest'],errors='coerce')>0]
    f=pd.DataFrame({'time':parse_time(raw[tc]),'ratio':pd.to_numeric(raw[rc],errors='coerce')}).dropna().sort_values('time').drop_duplicates('time')
    mu=f.ratio.rolling(72,min_periods=72).mean(); sd=f.ratio.rolling(72,min_periods=72).std(ddof=0); f['z']=(f.ratio-mu)/sd.replace(0,np.nan)
    return f.dropna(subset=['z'])

def prepare():
    p=load_price(); f=load_flow()
    q=p.set_index('time').resample('15min',label='left',closed='left').agg(o=('o','first'),h=('h','max'),l=('l','min'),c=('c','last')).dropna()
    pc=q.c.shift(1); tr=np.maximum(q.h-q.l,np.maximum((q.h-pc).abs(),(q.l-pc).abs())); q['atr']=tr.rolling(14,min_periods=14).mean(); q['avail_time']=q.index+pd.Timedelta(minutes=15)
    atr=q[['avail_time','atr']].dropna().reset_index(drop=True)
    p=pd.merge_asof(p.sort_values('time'),atr.sort_values('avail_time'),left_on='time',right_on='avail_time',direction='backward')
    p=pd.merge_asof(p.sort_values('time'),f[['time','z']].sort_values('time'),on='time',direction='backward',tolerance=pd.Timedelta(minutes=10))
    p=p.dropna(subset=['atr','z']).reset_index(drop=True); p['year']=p.time.dt.year; p['day']=p.time.dt.floor('D'); return p

def annual_stats(trades):
    out={}
    for y in YEARS:
        arr=np.asarray([x['R'] for x in trades if x['year']==y],float)
        if not len(arr):out[str(y)]={'N':0,'SumR':0.0,'EV':0.0,'PF':0.0,'MaxDD':0.0};continue
        eq=np.cumsum(arr); pk=np.maximum.accumulate(np.r_[0.,eq]); dd=float((pk[1:]-eq).max()); pos=arr[arr>0].sum(); neg=abs(arr[arr<0].sum()); pf=float(pos/neg) if neg>0 else 99.0
        out[str(y)]={'N':len(arr),'SumR':float(arr.sum()),'EV':float(arr.mean()),'PF':pf,'MaxDD':dd}
    return out

def aggregate(trades):
    arr=np.asarray([x['R'] for x in trades],float)
    if not len(arr):return {'N':0,'SumR':0,'EV':0,'PF':0,'MaxDD':0,'WR':0}
    eq=np.cumsum(arr); pk=np.maximum.accumulate(np.r_[0.,eq]); dd=float((pk[1:]-eq).max()); pos=arr[arr>0].sum(); neg=abs(arr[arr<0].sum()); pf=float(pos/neg) if neg>0 else 99.0
    return {'N':len(arr),'SumR':float(arr.sum()),'EV':float(arr.mean()),'PF':pf,'MaxDD':dd,'WR':float((arr>0).mean())}

def simulate(df,confirm,ttl_h,mode,stop_atr,hold_h,pause,exit_policy=('none',None,None,None,None)):
    _,be_at,be_lock,tr_arm,tr_dist=exit_policy
    n=len(df); times=df.time.to_numpy(); O=df.o.to_numpy(float); H=df.h.to_numpy(float); L=df.l.to_numpy(float); C=df.c.to_numpy(float); Z=df.z.to_numpy(float); A=df.atr.to_numpy(float); Y=df.year.to_numpy(int); D=df.day.to_numpy()
    trades=[]; i=0; next_time=np.datetime64('1970-01-01'); last_entry=None; last_atr=None; day_count={}
    while i<n-2:
        if times[i]<next_time:i+=1;continue
        if day_count.get(D[i],0)>=MAX_TRADES_DAY:i+=1;continue
        z=Z[i]; side=-1 if z>=ZTH else (1 if z<=-ZTH else 0)
        if side==0:i+=1;continue
        if pause=='atr1' and last_entry is not None and abs(O[i]-last_entry)<last_atr:i+=1;continue
        sig_px=O[i]; atr=A[i]; level=sig_px+side*confirm*atr; end=min(n-2,i+max(1,int(ttl_h*12))); ci=None
        for j in range(i+1,end+1):
            if (side>0 and H[j]>=level) or (side<0 and L[j]<=level):ci=j;break
        if ci is None:i+=1;continue
        if mode=='touch':ei=ci;entry=level
        elif mode=='confirm_close':ei=ci;entry=C[ci]
        elif mode=='next_open':
            if ci+1>=n:break
            ei=ci+1;entry=O[ei]
        else:
            retr=0.25 if mode=='pullback_025' else 0.50; target=level-side*retr*atr; ei=None
            for j in range(ci,min(n-2,ci+12)+1):
                if (side>0 and L[j]<=target) or (side<0 and H[j]>=target):ei=j;entry=target;break
            if ei is None:i=ci+1;continue
        if day_count.get(D[ei],0)>=MAX_TRADES_DAY:i=ei+1;continue
        sl=entry-side*stop_atr*atr; xe=min(n-1,ei+max(1,int(hold_h*12))); peak=entry; xp=C[xe]; exit_i=xe; reason='time'
        for j in range(ei+1,xe+1):
            if (side>0 and L[j]<=sl) or (side<0 and H[j]>=sl):xp=sl;exit_i=j;reason='stop';break
            px=C[j]; fav=side*(px-entry)
            if be_at is not None and fav>=be_at*atr:
                ns=entry+side*be_lock*atr
                if (side>0 and ns>sl) or (side<0 and ns<sl):sl=ns
            peak=max(peak,px) if side>0 else min(peak,px); mfe=side*(peak-entry)/atr
            if tr_arm is not None and mfe>=tr_arm:
                ns=peak-side*tr_dist*atr
                if (side>0 and ns>sl) or (side<0 and ns<sl):sl=ns
            if (side<0 and Z[j]<=-EXIT_Z) or (side>0 and Z[j]>=EXIT_Z):xp=px;exit_i=j;reason='zexit';break
        gross=side*(xp-entry)/(stop_atr*atr); cost=(COST_RT_BPS/10000.0)*entry/(stop_atr*atr); R=gross-cost
        trades.append({'year':int(Y[ei]),'R':float(R),'reason':reason}); day_count[D[ei]]=day_count.get(D[ei],0)+1; last_entry=entry; last_atr=atr
        next_time=times[exit_i]+(np.timedelta64(3,'h') if pause=='time3h' else np.timedelta64(5,'m')); i=exit_i+1
    return trades

def score_candidate(yearly,agg):
    vals=[yearly[str(y)]['SumR'] for y in YEARS]; return (min(vals),float(np.median(vals)),agg['SumR']/max(agg['MaxDD'],1e-9),agg['EV'])

def main():
    df=prepare(); print('prepared',len(df),df.time.min(),df.time.max(),list(df.columns))
    coarse=[];survivors=[];k=0
    for confirm,ttl,mode,stop,hold,pause in itertools.product(CONFIRMS,TTLS,ENTRY_MODES,STOPS,HOLDS,PAUSES):
        tr=simulate(df,confirm,ttl,mode,stop,hold,pause,BE_TRAIL[0]);ann=annual_stats(tr);agg=aggregate(tr);pos=sum(ann[str(y)]['SumR']>0 for y in YEARS)
        rec={'confirm':confirm,'ttl_h':ttl,'mode':mode,'stop':stop,'hold_h':hold,'pause':pause,'exit':'none','positive_years':pos,'annual':ann,'agg':agg,'score':score_candidate(ann,agg)};coarse.append(rec)
        if pos==5 and agg['N']>=150:survivors.append(rec)
        k+=1
    coarse.sort(key=lambda x:(x['positive_years'],x['score']),reverse=True);(OUT/'coarse_top100.json').write_text(json.dumps(coarse[:100],indent=2));print('COARSE tested',k,'five-year survivors',len(survivors))
    seeds=(survivors if survivors else coarse[:60])[:60];refined=[]
    for s in seeds:
        for ep in BE_TRAIL:
            tr=simulate(df,s['confirm'],s['ttl_h'],s['mode'],s['stop'],s['hold_h'],s['pause'],ep);ann=annual_stats(tr);agg=aggregate(tr);pos=sum(ann[str(y)]['SumR']>0 for y in YEARS)
            refined.append({'confirm':s['confirm'],'ttl_h':s['ttl_h'],'mode':s['mode'],'stop':s['stop'],'hold_h':s['hold_h'],'pause':s['pause'],'exit':ep[0],'positive_years':pos,'annual':ann,'agg':agg,'score':score_candidate(ann,agg)})
    refined.sort(key=lambda x:(x['positive_years'],x['score']),reverse=True);perfect=[r for r in refined if r['positive_years']==5 and r['agg']['N']>=150]
    out={'frozen_signal':{'ZThreshold':ZTH,'ExitZ':EXIT_Z},'cost_rt_bps':COST_RT_BPS,'years':YEARS,'coarse_tested':k,'coarse_5y_positive':len(survivors),'refined_tested':len(refined),'refined_5y_positive':len(perfect),'best':refined[0] if refined else coarse[0],'perfect_top20':perfect[:20],'near_top20':[r for r in refined if r['positive_years']<5][:20]};(OUT/'summary.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
