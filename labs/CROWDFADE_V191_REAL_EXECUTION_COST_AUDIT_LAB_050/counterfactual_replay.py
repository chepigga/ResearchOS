# LAB050_REPLAY_TRIGGER
from pathlib import Path
import zipfile, json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'replay_data'
OUT=ROOT/'counterfactual_output'
OUT.mkdir(parents=True,exist_ok=True)

COST_BPS=0.50
SL_ATR=1.50
BE_ATR=0.50
BE_LOCK=0.15
TRAIL_GAP=0.50
EXIT_Z=0.75
HOLD_SEC=6*3600
CONF_ATR=0.30
FRESH_SEC=45*60
MAX_ADV_ATR=0.75

ARMS={
  'CONTROL_2P5':2.5,
  'BALANCED_3P5':3.5,
  'AGGRESSIVE_5P0':5.0,
}

def read_kline_zip(path):
    with zipfile.ZipFile(path) as z:
        name=[n for n in z.namelist() if n.lower().endswith('.csv')][0]
        with z.open(name) as f:
            r=pd.read_csv(f,header=None)
    # Binance kline schema: open_time, open, high, low, close, ...
    q=pd.DataFrame({
      'ts':pd.to_numeric(r.iloc[:,0],errors='coerce'),
      'o':pd.to_numeric(r.iloc[:,1],errors='coerce'),
      'h':pd.to_numeric(r.iloc[:,2],errors='coerce'),
      'l':pd.to_numeric(r.iloc[:,3],errors='coerce'),
      'c':pd.to_numeric(r.iloc[:,4],errors='coerce'),
    }).dropna()
    med=float(np.nanmedian(q.ts.to_numpy(float)))
    if med>1e15: q['ts']=(q.ts//1_000_000).astype(np.int64)
    elif med>1e12: q['ts']=(q.ts//1000).astype(np.int64)
    else: q['ts']=q.ts.astype(np.int64)
    return q

def read_metrics_zip(path):
    with zipfile.ZipFile(path) as z:
        name=[n for n in z.namelist() if n.lower().endswith('.csv')][0]
        with z.open(name) as f:
            r=pd.read_csv(f)
    cols={c.lower():c for c in r.columns}
    # Daily futures metrics contain create_time and count_long_short_ratio.
    tcol=cols.get('create_time')
    rcol=cols.get('count_long_short_ratio')
    if tcol is None or rcol is None:
        raise RuntimeError(f'Unexpected metrics columns in {path.name}: {list(r.columns)}')
    t=pd.to_datetime(r[tcol],utc=True,errors='coerce')
    ratio=pd.to_numeric(r[rcol],errors='coerce')
    out=pd.DataFrame({'t':t,'ratio':ratio}).dropna().sort_values('t').drop_duplicates('t')
    return out

def load_symbol(sym):
    kparts=[read_kline_zip(p) for p in sorted((DATA/sym/'klines').glob('*.zip'))]
    mparts=[read_metrics_zip(p) for p in sorted((DATA/sym/'metrics').glob('*.zip'))]
    if not kparts or not mparts:
        raise RuntimeError(f'missing data for {sym}')
    q=pd.concat(kparts,ignore_index=True).drop_duplicates('ts').sort_values('ts').reset_index(drop=True)
    m=pd.concat(mparts,ignore_index=True).drop_duplicates('t').sort_values('t').reset_index(drop=True)
    mu=m.ratio.rolling(72,min_periods=72).mean()
    sd=m.ratio.rolling(72,min_periods=72).std(ddof=0)
    m['z']=(m.ratio-mu)/sd.replace(0,np.nan)
    m['ts']=(m.t.astype('int64')//10**9).astype(np.int64)

    # completed M15 ATR14, same geometry as research
    ts=q.ts.to_numpy(np.int64); H=q.h.to_numpy(float); L=q.l.to_numpy(float); C=q.c.to_numpy(float)
    b15=(ts//900)*900
    st15=np.r_[0,np.flatnonzero(b15[1:]!=b15[:-1])+1]
    en15=np.r_[st15[1:],len(ts)]
    bt15=b15[st15]
    bh15=np.maximum.reduceat(H,st15)
    bl15=np.minimum.reduceat(L,st15)
    bc15=C[en15-1]
    pc=np.r_[bc15[0],bc15[:-1]]
    tr=np.maximum(bh15-bl15,np.maximum(np.abs(bh15-pc),np.abs(bl15-pc)))
    atr=pd.Series(tr).rolling(14,min_periods=14).mean().to_numpy()
    av15=bt15+900

    # completed M5 close
    b5=(ts//300)*300
    st5=np.r_[0,np.flatnonzero(b5[1:]!=b5[:-1])+1]
    en5=np.r_[st5[1:],len(ts)]
    av5=b5[st5]+300
    c5=C[en5-1]

    return {
      'q':q,'ts':ts,'H':H,'L':L,'C':C,
      'm_ts':m.ts.to_numpy(np.int64),'m_z':m.z.to_numpy(float),
      'av15':av15,'atr15':atr,'av5':av5,'c5':c5,
    }

def asof_z(d,t):
    i=np.searchsorted(d['m_ts'],t,'right')-1
    if i<0:return np.nan
    if t-d['m_ts'][i]>600:return np.nan
    return float(d['m_z'][i])

def atr_at(d,t):
    i=np.searchsorted(d['av15'],t,'right')-1
    if i<0:return np.nan
    return float(d['atr15'][i])

def signal_close(d,t):
    i=np.searchsorted(d['av5'],t)
    if i<len(d['av5']) and int(d['av5'][i])==int(t):
        return float(d['c5'][i])
    i=np.searchsorted(d['av5'],t,'right')-1
    if i<0:return np.nan
    return float(d['c5'][i])

def confirm_entry(d,t,side):
    a=atr_at(d,t)
    sig=signal_close(d,t)
    if not np.isfinite(a) or not np.isfinite(sig):
        return {'status':'NO_DATA'}
    s=1 if side=='BUY' else -1
    target=sig+s*CONF_ATR*a
    ps=np.searchsorted(d['ts'],t+1)
    pe=np.searchsorted(d['ts'],t+FRESH_SEC,'right')
    maxadv=0.0
    for q in range(ps,min(pe,len(d['ts']))):
        adv=((d['H'][q]-sig) if s<0 else (sig-d['L'][q]))/a
        maxadv=max(maxadv,float(adv))
        if maxadv>MAX_ADV_ATR:
            return {'status':'SKIP_ADVERSE','atr':a,'signal_price':sig,'target':target,'max_adverse_atr':maxadv}
        crossed=(s>0 and d['C'][q]>=target) or (s<0 and d['C'][q]<=target)
        if crossed:
            z=asof_z(d,int(d['ts'][q]))
            if not np.isfinite(z):
                return {'status':'SKIP_NO_Z','atr':a,'signal_price':sig,'target':target,'max_adverse_atr':maxadv}
            contradiction=(s>0 and z>=0.75) or (s<0 and z<=-0.75)
            if contradiction:
                return {'status':'SKIP_CONFIRM_Z','atr':a,'signal_price':sig,'target':target,'max_adverse_atr':maxadv,'confirm_z':z}
            return {
              'status':'ENTER','atr':a,'signal_price':sig,'target':target,'max_adverse_atr':maxadv,
              'entry_idx':q,'entry_ts':int(d['ts'][q]),'entry_price':float(d['C'][q]),'confirm_z':z,
            }
    return {'status':'SKIP_NO_CONFIRM','atr':a,'signal_price':sig,'target':target,'max_adverse_atr':maxadv}

def manage(d,ent,side,arm):
    s=1 if side=='BUY' else -1
    a=ent['atr']; entry=ent['entry_price']; ei=ent['entry_idx']
    risk=SL_ATR*a
    stop=entry-s*risk
    pending=stop
    peak=entry
    xe=min(len(d['ts'])-1,np.searchsorted(d['ts'],d['ts'][ei]+HOLD_SEC,'left'))
    xp=float(d['C'][xe]); ex=xe; reason='TIME'
    for q in range(ei+1,xe+1):
        stop=pending
        if (s>0 and d['L'][q]<=stop) or (s<0 and d['H'][q]>=stop):
            xp=float(stop); ex=q
            protected=(s>0 and stop>entry) or (s<0 and stop<entry)
            reason='PROTECTED_STOP' if protected else 'SL'
            break
        if s>0:
            peak=max(peak,float(d['H'][q])); fav=(peak-entry)/a
        else:
            peak=min(peak,float(d['L'][q])); fav=(entry-peak)/a
        ns=stop
        if fav>=BE_ATR:
            lvl=entry+s*BE_LOCK*a
            if (s>0 and lvl>ns) or (s<0 and lvl<ns): ns=lvl
        if fav>=arm:
            lvl=peak-s*TRAIL_GAP*a
            if (s>0 and lvl>ns) or (s<0 and lvl<ns): ns=lvl
        pending=ns
        z=asof_z(d,int(d['ts'][q]))
        if np.isfinite(z) and ((s>0 and z>=EXIT_Z) or (s<0 and z<=-EXIT_Z)):
            xp=float(d['C'][q]); ex=q; reason='EXIT_Z'; break
    gross=s*(xp-entry)/risk
    cost=(COST_BPS/10000.0)*entry/risk
    return {
      'exit_ts':int(d['ts'][ex]),'exit_price':xp,'reason':reason,
      'gross_R':float(gross),'cost_R':float(cost),'net_R':float(gross-cost),
      'hold_min':float((d['ts'][ex]-d['ts'][ei])/60.0),
    }

def main():
    signals=pd.read_csv(ROOT/'live_signal_ids.csv')
    data={s:load_symbol(s) for s in sorted(signals.symbol.unique())}
    out=[]
    for _,r in signals.iterrows():
        t=int(''.join([c for c in str(r.comment) if c.isdigit()])[-10:])
        d=data[r.symbol]
        ent=confirm_entry(d,t,r.side)
        base={
          'comment':r.comment,'symbol':r.symbol,'side':r.side,'signal_ts':t,
          'signal_utc':pd.to_datetime(t,unit='s',utc=True).isoformat(),
          'signal_z':asof_z(d,t),
          'entry_status':ent['status'],
          'signal_price':ent.get('signal_price',np.nan),
          'atr15':ent.get('atr',np.nan),
          'max_adverse_atr':ent.get('max_adverse_atr',np.nan),
          'lab_entry_ts':ent.get('entry_ts',np.nan),
          'lab_entry_utc':pd.to_datetime(ent['entry_ts'],unit='s',utc=True).isoformat() if ent.get('entry_ts') is not None else None,
          'lab_entry_price':ent.get('entry_price',np.nan),
          'confirm_z':ent.get('confirm_z',np.nan),
        }
        if ent['status']=='ENTER':
            for name,arm in ARMS.items():
                m=manage(d,ent,r.side,arm)
                for k,v in m.items(): base[f'{name}_{k}']=v
                base[f'{name}_exit_utc']=pd.to_datetime(m['exit_ts'],unit='s',utc=True).isoformat()
        out.append(base)
    df=pd.DataFrame(out)
    df.to_csv(OUT/'signal_counterfactual.csv',index=False)

    summary={'signals':int(len(df)),'entered':int((df.entry_status=='ENTER').sum()),
             'status_counts':df.entry_status.value_counts().to_dict(),'variants':{}}
    for name in ARMS:
        x=pd.to_numeric(df.get(f'{name}_net_R'),errors='coerce').dropna()
        summary['variants'][name]={
          'N':int(len(x)),'SumR':float(x.sum()),'EV':float(x.mean()) if len(x) else None,
          'WR':float((x>0).mean()) if len(x) else None,
        }
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))
    print(df[['comment','symbol','side','entry_status','lab_entry_utc',
      'CONTROL_2P5_reason','CONTROL_2P5_net_R',
      'BALANCED_3P5_reason','BALANCED_3P5_net_R',
      'AGGRESSIVE_5P0_reason','AGGRESSIVE_5P0_net_R']].to_string(index=False))

if __name__=='__main__':
    main()
