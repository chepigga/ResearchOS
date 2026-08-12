import zipfile, json
from pathlib import Path
import numpy as np
import pandas as pd

SIG='research/btc_unified_lifecycle/U01_EXACT_MT5_DIRECTIONAL_SIGNALS_COMPACT.csv'
EV='lab020_events.csv'
M5='btc_5m.zip'
OUT=Path('u05_out'); OUT.mkdir(exist_ok=True)

# Canonical LAB018 spec: H4 Supertrend ATR(10), multiplier 3.
def load_m5():
    fs=[]
    with zipfile.ZipFile(M5) as z:
        for n in z.namelist():
            if n.lower().endswith('.csv'):
                with z.open(n) as f: fs.append(pd.read_csv(f,usecols=['time','open','high','low','close']))
    x=pd.concat(fs,ignore_index=True)
    x['time']=pd.to_datetime(x['time'],utc=True).dt.tz_localize(None)
    for c in ['open','high','low','close']: x[c]=pd.to_numeric(x[c],errors='coerce')
    return x.dropna().sort_values('time').drop_duplicates('time')

def resample_h4(m5):
    h=(m5.set_index('time').resample('4h',label='left',closed='left')
       .agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last')).dropna().reset_index())
    h['close_time']=h.time+pd.Timedelta(hours=4)
    return h

def atr_wilder(h,n=10):
    pc=h.close.shift(1)
    tr=pd.concat([h.high-h.low,(h.high-pc).abs(),(h.low-pc).abs()],axis=1).max(axis=1)
    # pandas ewm alpha=1/n is Wilder recursive smoothing after warmup.
    return tr.ewm(alpha=1/n,adjust=False,min_periods=n).mean()

def supertrend(h,mult=3.0):
    x=h.copy(); x['atr10']=atr_wilder(x,10); hl2=(x.high+x.low)/2
    bu=hl2+mult*x.atr10; bl=hl2-mult*x.atr10
    fu=bu.copy(); fl=bl.copy(); st=np.full(len(x),np.nan); d=np.zeros(len(x),dtype=int)
    start=x.atr10.first_valid_index()
    if start is None:return x
    # canonical recursive final bands; initialize first valid as bullish unless close below basic lower.
    for i in range(start,len(x)):
        if i==start:
            fu.iat[i]=bu.iat[i]; fl.iat[i]=bl.iat[i]; d[i]=1; st[i]=fl.iat[i]; continue
        fu.iat[i]=bu.iat[i] if (bu.iat[i] < fu.iat[i-1] or x.close.iat[i-1] > fu.iat[i-1]) else fu.iat[i-1]
        fl.iat[i]=bl.iat[i] if (bl.iat[i] > fl.iat[i-1] or x.close.iat[i-1] < fl.iat[i-1]) else fl.iat[i-1]
        if d[i-1] == -1:
            d[i]=1 if x.close.iat[i] > fu.iat[i] else -1
        else:
            d[i]=-1 if x.close.iat[i] < fl.iat[i] else 1
        st[i]=fl.iat[i] if d[i]==1 else fu.iat[i]
    x['st_dir']=d; x['st_line']=st
    age=np.zeros(len(x),dtype=int)
    for i in range(1,len(x)):
        age[i]=age[i-1]+1 if d[i]!=0 and d[i]==d[i-1] else 0
    x['st_age']=age
    x['st_dist_atr']=(x.close-x.st_line)/x.atr10
    return x

def load_events():
    e=pd.read_csv(EV)
    e['entry_time']=pd.to_datetime(e['entry_time'])
    return e.sort_values('entry_time')

def parity_variants(h,e):
    # Compare multiple causal alignment choices only against frozen state labels, never outcome/P&L.
    rows=[]
    for key,timecol in [('BAR_OPEN','time'),('BAR_CLOSE','close_time')]:
      for lag in [0,1]:
        s=h[['time','close_time','st_dir','st_age']].copy()
        if lag:
            s['st_dir']=s.st_dir.shift(lag); s['st_age']=s.st_age.shift(lag)
        s=s.dropna().sort_values(timecol)
        m=pd.merge_asof(e.sort_values('entry_time'),s.sort_values(timecol),left_on='entry_time',right_on=timecol,direction='backward')
        z=m.dropna(subset=['H4_ST_DIR','H4_ST_AGE_BARS','st_dir','st_age'])
        rows.append(dict(key=key,lag=lag,N=len(z),dir_match=float((z.H4_ST_DIR.astype(int)==z.st_dir.astype(int)).mean()),age_exact=float((z.H4_ST_AGE_BARS.astype(int)==z.st_age.astype(int)).mean()),age_mae=float((z.H4_ST_AGE_BARS-z.st_age).abs().mean())))
    return pd.DataFrame(rows).sort_values(['dir_match','age_exact','age_mae'],ascending=[False,False,True])

def map_signals(h, sig, align_key, lag):
    s=sig.copy(); s['signal_time']=pd.to_datetime(s.signal_time); s['utc_time']=s.signal_time-pd.Timedelta(hours=3)
    timecol='time' if align_key=='BAR_OPEN' else 'close_time'
    hs=h[['time','close_time','st_dir','st_age','st_dist_atr']].copy()
    if lag:
        for c in ['st_dir','st_age','st_dist_atr']:hs[c]=hs[c].shift(lag)
    hs=hs.dropna(subset=['st_dir']).sort_values(timecol)
    m=pd.merge_asof(s.sort_values('utc_time'),hs.sort_values(timecol),left_on='utc_time',right_on=timecol,direction='backward')
    # Trade-coordinate relation: +1 = aligned, -1 = opposite.
    td=np.where(m.side.eq('BUY'),1,-1)
    m['h4_trade_relation']=td*m.st_dir
    m['clock_bucket']=np.select([
        m.st_age<=11,m.st_age<=27,m.st_age<=58
    ],['B1','B2','B3'],default='B4')
    m['unified_state']='OTHER'
    m.loc[(m.side=='BUY')&(m.st_age>58)&(m.h4_trade_relation==-1),'unified_state']='BUY_TIER_A'
    m.loc[(m.side=='BUY')&(m.st_age>58)&(m.h4_trade_relation==1),'unified_state']='BUY_TIER_B'
    m.loc[(m.side=='SELL')&(m.st_age>=27)&(m.st_age<=50),'unified_state']='SELL_B3_RECENT'
    return m

def main():
    m5=load_m5(); h=supertrend(resample_h4(m5)); e=load_events()
    p=parity_variants(h,e); p.to_csv(OUT/'u05_supertrend_parity_variants.csv',index=False)
    best=p.iloc[0]
    sig=pd.read_csv(SIG)
    m=map_signals(h,sig,str(best['key']),int(best['lag'])); m.to_csv(OUT/'u05_signal_market_clock_map.csv',index=False)
    ep=m.sort_values('signal_time').groupby('episode15',as_index=False).first(); ep.to_csv(OUT/'u05_episode_market_clock_map.csv',index=False)
    summary={
      'canonical_supertrend':'H4 ATR10 multiplier3',
      'parity_best':best.to_dict(),
      'poll_state_counts':m.unified_state.value_counts().to_dict(),
      'episode_state_counts':ep.unified_state.value_counts().to_dict(),
      'episode_clock':ep[['episode15','signal_time','side','tag','disposition','st_dir','st_age','h4_trade_relation','clock_bucket','unified_state']].to_dict('records'),
      'tier_a_overlap_polls':int((m.unified_state=='BUY_TIER_A').sum()),
      'tier_b_overlap_polls':int((m.unified_state=='BUY_TIER_B').sum()),
      'sell_b3_overlap_polls':int((m.unified_state=='SELL_B3_RECENT').sum()),
    }
    (OUT/'u05_summary.json').write_text(json.dumps(summary,indent=2,default=str))
    print('PARITY VARIANTS')
    print(p.to_string(index=False))
    print('\nEPISODE CLOCK')
    print(ep[['episode15','signal_time','side','tag','disposition','st_dir','st_age','h4_trade_relation','clock_bucket','unified_state']].to_string(index=False))
    print('\nSUMMARY')
    print(json.dumps(summary,indent=2,default=str))
if __name__=='__main__':main()
