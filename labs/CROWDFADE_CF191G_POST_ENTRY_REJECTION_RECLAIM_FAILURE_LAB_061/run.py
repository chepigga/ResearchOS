from pathlib import Path
import json, zipfile, importlib.util
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)

p53=ROOT.parent/'CROWDFADE_THREE_BOT_FIXES_HISTORICAL_REPLAY_LAB_053'/'run.py'
sp=importlib.util.spec_from_file_location('lab53',p53)
lab53=importlib.util.module_from_spec(sp); sp.loader.exec_module(lab53)
lab43=lab53.lab43
lab53.DATA=DATA; lab43.DATA=DATA

EXPECT={
    'historical': {'N':5297,'SumR':700.3704107793633},
    'forward_2026': {'N':544,'SumR':35.49784078156513},
}
REASON={1:'INITIAL_STOP',2:'PROFIT_STOP',4:'TIME_EXIT'}
RECLAIM_WINDOWS=[1,3,5]

def metrics_r(a):
    return lab43.metrics(np.asarray(a,float))

def load_m1():
    rows=[]
    for zp in sorted((DATA/'all_1m').glob('BTCUSDT-1m-*.zip')):
        with zipfile.ZipFile(zp) as z:
            n=z.namelist()[0]
            with z.open(n) as f:
                q=pd.read_csv(f,header=None,usecols=[0,2,3,4])
        ot=(pd.to_numeric(q.iloc[:,0],errors='coerce')//1000).astype('Int64')
        hi=pd.to_numeric(q.iloc[:,1],errors='coerce')
        lo=pd.to_numeric(q.iloc[:,2],errors='coerce')
        cl=pd.to_numeric(q.iloc[:,3],errors='coerce')
        x=pd.DataFrame({'open_ts':ot,'high':hi,'low':lo,'close':cl}).dropna()
        x['end_ts']=x.open_ts.astype(np.int64)+60
        rows.append(x)
    return pd.concat(rows,ignore_index=True).sort_values('open_ts').drop_duplicates('open_ts').reset_index(drop=True)

class ReclaimIndex:
    def __init__(self,m1):
        self.end=m1.end_ts.to_numpy(np.int64)
        self.high=m1.high.to_numpy(float)
        self.low=m1.low.to_numpy(float)
        self.close=m1.close.to_numpy(float)

    def classify(self,entry_ts,side):
        j=np.searchsorted(self.end,int(entry_ts),'left')
        if j>=len(self.end) or self.end[j]!=int(entry_ts) or j<4:
            return None
        idx=np.arange(j-4,j+1)
        expected=np.arange(int(entry_ts)-240,int(entry_ts)+1,60)
        if not np.array_equal(self.end[idx],expected):
            return None
        ah=float(np.max(self.high[idx])); al=float(np.min(self.low[idx]))
        rej_q=None;rej_close=np.nan;rej_minute=np.nan
        for n in range(1,16):
            q=j+n
            if q>=len(self.end) or self.end[q]!=int(entry_ts)+60*n:
                break
            c=float(self.close[q])
            reject=(c<al) if side>0 else (c>ah)
            if reject:
                rej_q=q;rej_close=c;rej_minute=n;break
        out={'anchor_high':ah,'anchor_low':al,'rejection_minute':rej_minute,'rejection_close':rej_close}
        if rej_q is None:
            for w in RECLAIM_WINDOWS:
                out[f'class_{w}m']='NO_REJECTION'
                out[f'reclaim_minute_{w}m']=np.nan
            return out

        for w in RECLAIM_WINDOWS:
            found=None
            for k in range(1,w+1):
                q=rej_q+k
                if q>=len(self.end) or self.end[q]!=self.end[rej_q]+60*k:
                    break
                c=float(self.close[q])
                reclaim=(c>=al) if side>0 else (c<=ah)
                if reclaim:
                    found=k;break
            if found is None:
                out[f'class_{w}m']=f'NO_RECLAIM_{w}M'
                out[f'reclaim_minute_{w}m']=np.nan
            else:
                out[f'class_{w}m']=f'RECLAIMED_{w}M'
                out[f'reclaim_minute_{w}m']=int(found)
        return out

def excursion_m5(p,entry_k,side,entry,atr,mins):
    dt5,H5,L5,C5=p[5],p[6],p[7],p[8]
    e=np.searchsorted(dt5,int(dt5[entry_k])+mins*60,'right')
    if e<=entry_k+1:return (0.0,0.0,0.0)
    hh=H5[entry_k+1:e];ll=L5[entry_k+1:e]
    if len(hh)==0:return (0.0,0.0,0.0)
    if side>0:
        mfe=(np.nanmax(hh)-entry)/atr
        mae=(entry-np.nanmin(ll))/atr
    else:
        mfe=(entry-np.nanmin(ll))/atr
        mae=(np.nanmax(hh)-entry)/atr
    ci=min(len(C5)-1,e-1)
    ret=side*(C5[ci]-entry)/atr
    return float(mfe),float(mae),float(ret)

def extract_control_events(p):
    ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5=p
    rows=[]
    k=0;day=-1;dc=0;nextts=0;last=0.;la=0.;has=False
    conf=False;cs=0;cp=0.;ca=0.;ct=0;cb=0;mf=0.;ma=0.
    while k<len(dt5)-3:
        t=int(dt5[k]);z=float(Z5[k])
        if t<nextts:
            k+=1;continue
        d=t//86400
        if d!=day:day=d;dc=0
        if dc>=lab53.MAXDAY:
            conf=False;k+=1;continue
        if conf:
            side=cs
            fav=((cp-L5[k]) if side<0 else (H5[k]-cp))/ca
            adv=((H5[k]-cp) if side<0 else (cp-L5[k]))/ca
            if fav<0:fav=0.
            if adv<0:adv=0.
            mf=max(mf,float(fav));ma=max(ma,float(adv))
            cb-=1;age=t-ct
            if cb<=0 or age>2700:
                conf=False;k+=1;continue
            if ma>lab53.G_MAX_ADV:
                conf=False;k+=1;continue
            target=cp+side*lab53.CONF_ATR*ca
            confirmed=(C5[k]>=target) if side>0 else (C5[k]<=target)
            if not confirmed:
                k+=1;continue
            same=(z<0.0) if side>0 else (z>0.0)
            if not same:
                conf=False;k+=1;continue
            if abs(z)<lab53.G_MIN_ABS_Z:
                conf=False;k+=1;continue
            response=mf/(ma+1e-9)
            if response<lab53.G_MIN_RESPONSE:
                conf=False;k+=1;continue
            conf=False
            if has and abs(C5[k]-last)<lab53.PAUSE_ATR*la:
                k+=1;continue

            entry=float(C5[k]);atr=float(ca)
            rr,ex,reason=lab53.manage_cf191g(dt5,H5,L5,C5,k,side,entry,atr)
            row={
              'signal_ts':int(ct),'entry_ts':t,'entry_k':int(k),'side':int(side),
              'entry_price':entry,'atr':atr,'R':float(rr),
              'exit_ts':int(dt5[int(ex)]),'exit_reason':REASON.get(int(reason),str(reason))
            }
            for h in [15,30,60,120]:
                mfe,mae,ret=excursion_m5(p,k,side,entry,atr,h)
                row[f'mfe_{h}m']=mfe;row[f'mae_{h}m']=mae;row[f'ret_{h}m']=ret
            rows.append(row)
            dc+=1;last=entry;la=atr;has=True;nextts=int(dt5[int(ex)])+1
            k+=1;continue

        side=-1 if z>=lab53.ZTH else (1 if z<=-lab53.ZTH else 0)
        if side==0:
            k+=1;continue
        if has and abs(C5[k]-last)<lab53.PAUSE_ATR*la:
            k+=1;continue
        conf=True;cs=side;cp=float(C5[k]);ca=float(A5[k]);ct=t;cb=9;mf=0.;ma=0.
        k+=1
    return pd.DataFrame(rows)

def describe(g,period,label,w):
    m=metrics_r(g.R.to_numpy(float))
    return {
      'period':period,'window_min':w,'state':label,'N':len(g),
      'EV_R':m.get('EV',np.nan),'PF':m.get('PF',np.nan),'SumR':m.get('SumR',np.nan),
      'WR':m.get('WR',np.nan),'MaxDD_R':m.get('MaxDD_R',np.nan),
      'mean_mfe15':float(g.mfe_15m.mean()) if len(g) else np.nan,
      'mean_mae15':float(g.mae_15m.mean()) if len(g) else np.nan,
      'mean_mfe60':float(g.mfe_60m.mean()) if len(g) else np.nan,
      'mean_mae60':float(g.mae_60m.mean()) if len(g) else np.nan,
      'initial_stop_share':float((g.exit_reason=='INITIAL_STOP').mean()) if len(g) else np.nan,
      'positive_R_share':float((g.R>0).mean()) if len(g) else np.nan,
      'right_tail_ge_1p5R_share':float((g.R>=1.5).mean()) if len(g) else np.nan,
      'mean_R':float(g.R.mean()) if len(g) else np.nan,
    }

def main():
    m1=load_m1();idx=ReclaimIndex(m1)
    ft,fz=lab43.load_flow()
    hist_raw=lab43.load_hist();sec_raw=lab43.load_sec()
    periods={
      'historical':lab43.prep(hist_raw,ft,fz,int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-01-01',tz='UTC').timestamp())),
      'forward_2026':lab43.prep(sec_raw,ft,fz,int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()))
    }

    all_events=[];rows=[]
    for period,p in periods.items():
        ev=extract_control_events(p)
        exp=EXPECT[period]
        if len(ev)!=exp['N'] or abs(float(ev.R.sum())-exp['SumR'])>1e-6:
            raise RuntimeError(f'control parity fail {period}: {len(ev)} {ev.R.sum()}')
        cls=[]
        for _,r in ev.iterrows():
            c=idx.classify(int(r.entry_ts),int(r.side))
            if c is None:
                c={'anchor_high':np.nan,'anchor_low':np.nan,'rejection_minute':np.nan,'rejection_close':np.nan}
                for w in RECLAIM_WINDOWS:
                    c[f'class_{w}m']='NO_DATA';c[f'reclaim_minute_{w}m']=np.nan
            cls.append(c)
        cdf=pd.DataFrame(cls)
        ev=pd.concat([ev.reset_index(drop=True),cdf],axis=1)
        ev['period']=period
        all_events.append(ev)

        for w in RECLAIM_WINDOWS:
            for label in [f'RECLAIMED_{w}M',f'NO_RECLAIM_{w}M','NO_REJECTION']:
                rows.append(describe(ev[ev[f'class_{w}m']==label],period,label,w))

    events=pd.concat(all_events,ignore_index=True)
    events.to_csv(OUT/'reclaim_events.csv',index=False)
    summary=pd.DataFrame(rows)
    summary.to_csv(OUT/'reclaim_summary.csv',index=False)

    checks={}
    for period in ['historical','forward_2026']:
        w=3
        rec=summary[(summary.period==period)&(summary.window_min==w)&(summary.state=='RECLAIMED_3M')].iloc[0]
        nr=summary[(summary.period==period)&(summary.window_min==w)&(summary.state=='NO_RECLAIM_3M')].iloc[0]
        checks[period]={
          'reclaimed_N':int(rec.N),'no_reclaim_N':int(nr.N),
          'NO_RECLAIM_EV_lt_RECLAIMED':bool(nr.EV_R<rec.EV_R) if np.isfinite(nr.EV_R) and np.isfinite(rec.EV_R) else False,
          'NO_RECLAIM_PF_lt_RECLAIMED':bool(nr.PF<rec.PF) if np.isfinite(nr.PF) and np.isfinite(rec.PF) else False,
          'NO_RECLAIM_MFE60_lt_RECLAIMED':bool(nr.mean_mfe60<rec.mean_mfe60) if np.isfinite(nr.mean_mfe60) and np.isfinite(rec.mean_mfe60) else False,
          'NO_RECLAIM_MAE60_gt_RECLAIMED':bool(nr.mean_mae60>rec.mean_mae60) if np.isfinite(nr.mean_mae60) and np.isfinite(rec.mean_mae60) else False,
          'NO_RECLAIM_initial_stop_share_gt_RECLAIMED':bool(nr.initial_stop_share>rec.initial_stop_share) if np.isfinite(nr.initial_stop_share) and np.isfinite(rec.initial_stop_share) else False,
          'sample_ok':bool(nr.N >= (50 if period=='historical' else 10)),
        }
    primary_pass=all(all(v for k,v in checks[p].items() if k not in ['reclaimed_N','no_reclaim_N']) for p in checks)
    stop_branch=not primary_pass

    result={
      'lab':'CROWDFADE_CF191G_POST_ENTRY_REJECTION_RECLAIM_FAILURE_LAB_061',
      'primary_window_min':3,
      'checks':checks,
      'primary_PASS_both_periods':bool(primary_pass),
      'STOP_EXIT_BRANCH':bool(stop_branch),
      'stop_rule':'If primary fails in either period or sample is insufficient, stop this rejection/reclaim exit branch.'
    }
    (OUT/'summary.json').write_text(json.dumps(result,indent=2))

    lines=['# LAB061 — POST-ENTRY REJECTION RECLAIM FAILURE','',
      'Diagnostic only. CF191g entry and management unchanged.','',
      '## Summary','',summary.to_markdown(index=False),'',
      '## Primary 3m checks','',json.dumps(checks,indent=2),'',
      f"Primary PASS both periods: **{primary_pass}**",
      f"STOP exit branch: **{stop_branch}**"]
    (OUT/'REPORT.md').write_text('\n'.join(lines))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__':
    main()
