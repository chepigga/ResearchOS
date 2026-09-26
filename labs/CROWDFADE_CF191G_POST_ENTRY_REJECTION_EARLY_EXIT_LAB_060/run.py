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
HORIZONS=[5,10,15]
REASON={1:'INITIAL_STOP',2:'PROFIT_STOP',4:'TIME_EXIT'}

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
    m=pd.concat(rows,ignore_index=True).sort_values('open_ts').drop_duplicates('open_ts').reset_index(drop=True)
    return m

class RejectionIndex:
    def __init__(self,m1):
        self.end=m1.end_ts.to_numpy(np.int64)
        self.high=m1.high.to_numpy(float)
        self.low=m1.low.to_numpy(float)
        self.close=m1.close.to_numpy(float)

    def anchor(self,entry_ts):
        j=np.searchsorted(self.end,int(entry_ts),'left')
        if j>=len(self.end) or self.end[j]!=int(entry_ts) or j<4:
            return None
        idx=np.arange(j-4,j+1)
        expected=np.arange(int(entry_ts)-240,int(entry_ts)+1,60)
        if not np.array_equal(self.end[idx],expected):
            return None
        return j,float(np.max(self.high[idx])),float(np.min(self.low[idx]))

    def first_rejection(self,entry_ts,side,horizon_min):
        a=self.anchor(entry_ts)
        if a is None:return None
        j,ah,al=a
        for n in range(1,horizon_min+1):
            q=j+n
            if q>=len(self.end) or self.end[q]!=int(entry_ts)+60*n:
                break
            c=float(self.close[q])
            reject=(c<al) if side>0 else (c>ah)
            if reject:
                return {'ts':int(self.end[q]),'close':c,'minute':n,'anchor_high':ah,'anchor_low':al}
        return None

def excursion_m5(p,entry_k,side,entry,atr,mins):
    dt5,H5,L5,C5=p[5],p[6],p[7],p[8]
    if not np.isfinite(atr) or atr<=0:return (np.nan,np.nan,np.nan)
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

def simulate(p,reject_idx,horizon_min):
    ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5=p
    cap=len(dt5)
    R=np.zeros(cap);ST=np.zeros(cap,np.int64);ET=np.zeros(cap,np.int64);XT=np.zeros(cap,np.int64);SIDE=np.zeros(cap,np.int8)
    n=0;k=0;day=-1;dc=0;nextts=0;last=0.;la=0.;has=False
    conf=False;cs=0;cp=0.;ca=0.;ct=0;cb=0;mf=0.;ma=0.
    events=[]

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
            rr0,ex0,reason0=lab53.manage_cf191g(dt5,H5,L5,C5,k,side,entry,atr)
            control_exit_ts=int(dt5[int(ex0)])
            rr=float(rr0);exit_ts=control_exit_ts;exit_reason=REASON.get(int(reason0),str(reason0))
            rej=None
            if horizon_min>0:
                rej=reject_idx.first_rejection(t,side,horizon_min)
                # Conservative ordering: only override if rejection completed strictly before frozen 5m exit timestamp.
                if rej is not None and int(rej['ts'])<control_exit_ts:
                    rr=side*(float(rej['close'])-entry)/(lab53.SL_ATR*atr)-(lab53.COST_BPS/10000.)*entry/(lab53.SL_ATR*atr)
                    exit_ts=int(rej['ts']);exit_reason='EARLY_REJECTION'
                    ev={
                      'signal_ts':int(ct),'entry_ts':t,'exit_ts':exit_ts,'side':int(side),
                      'entry_price':entry,'atr':atr,'horizon_min':horizon_min,
                      'rejection_minute':int(rej['minute']),'rejection_close':float(rej['close']),
                      'anchor_high':float(rej['anchor_high']),'anchor_low':float(rej['anchor_low']),
                      'early_R':float(rr),'original_R':float(rr0),
                      'delta_R':float(rr-rr0),
                      'saved_R':float(max(rr-rr0,0.0)),
                      'given_up_R':float(max(rr0-rr,0.0)),
                      'original_exit_ts':control_exit_ts,
                      'original_exit_reason':REASON.get(int(reason0),str(reason0)),
                    }
                    for h in [15,30,60,120]:
                        mfe,mae,ret=excursion_m5(p,k,side,entry,atr,h)
                        ev[f'mfe_{h}m']=mfe;ev[f'mae_{h}m']=mae;ev[f'ret_{h}m']=ret
                    events.append(ev)

            R[n]=rr;ST[n]=int(ct);ET[n]=t;XT[n]=exit_ts;SIDE[n]=side;n+=1
            dc+=1;last=entry;la=atr;has=True;nextts=exit_ts+1
            k+=1;continue

        side=-1 if z>=lab53.ZTH else (1 if z<=-lab53.ZTH else 0)
        if side==0:
            k+=1;continue
        if has and abs(C5[k]-last)<lab53.PAUSE_ATR*la:
            k+=1;continue
        conf=True;cs=side;cp=float(C5[k]);ca=float(A5[k]);ct=t;cb=9;mf=0.;ma=0.
        k+=1

    return R[:n],ST[:n],ET[:n],XT[:n],SIDE[:n],pd.DataFrame(events)

def period_stats(R,ST,period):
    m=metrics_r(R)
    t=pd.to_datetime(ST,unit='s',utc=True)
    keys=t.year.astype(str).to_numpy() if period=='historical' else t.to_period('M').astype(str).to_numpy()
    details={}
    for key in sorted(set(keys)):
        details[str(key)]=metrics_r(np.asarray(R)[keys==key].astype(float))
    pos=sum(1 for x in details.values() if x.get('SumR',0)>0)
    return m,details,pos,len(details)

def event_stats(ev):
    if len(ev)==0:
        return {'rejection_exits':0,'mean_saved_R':0.0,'total_saved_R':0.0,'mean_given_up_R':0.0,'total_given_up_R':0.0,
                'net_local_delta_R':0.0,'initial_stop_share':np.nan,'median_saved_R_on_rescued':np.nan}
    rescued=ev[ev.saved_R>0]
    return {
      'rejection_exits':int(len(ev)),
      'mean_saved_R':float(ev.saved_R.mean()),'total_saved_R':float(ev.saved_R.sum()),
      'mean_given_up_R':float(ev.given_up_R.mean()),'total_given_up_R':float(ev.given_up_R.sum()),
      'net_local_delta_R':float(ev.delta_R.sum()),
      'initial_stop_share':float((ev.original_exit_reason=='INITIAL_STOP').mean()),
      'median_saved_R_on_rescued':float(rescued.saved_R.median()) if len(rescued) else np.nan,
    }

def success(control,cand,cpos,npos,evs):
    sum_ok=cand['SumR']>=0.98*control['SumR']
    return {
      'R_DD_not_worse':bool(cand['R_DD']>=control['R_DD']),
      'SumR_ge_98pct_control':bool(sum_ok),
      'PF_ge_control_or_DD_better':bool(cand['PF']>=control['PF'] or cand['MaxDD_R']<control['MaxDD_R']),
      'max_consecutive_losses_not_worse':bool(cand['MaxConsecutiveLosses']<=control['MaxConsecutiveLosses']),
      'positive_periods_not_worse':bool(npos>=cpos),
      'event_count_meaningful':bool((evs>=20)), # forward threshold handled separately below
    }

def main():
    m1=load_m1();ridx=RejectionIndex(m1)
    ft,fz=lab43.load_flow()
    hist_raw=lab43.load_hist();sec_raw=lab43.load_sec()
    periods={
      'historical':lab43.prep(hist_raw,ft,fz,int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-01-01',tz='UTC').timestamp())),
      'forward_2026':lab43.prep(sec_raw,ft,fz,int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()))
    }

    rows=[];period_details={};events_all=[];checks={}
    for period,p in periods.items():
        cR,cST,cET,cXT,cSIDE,cEV=simulate(p,ridx,0)
        exp=EXPECT[period]
        if len(cR)!=exp['N'] or abs(float(cR.sum())-exp['SumR'])>1e-6:
            raise RuntimeError(f'control parity fail {period}: {len(cR)} {cR.sum()}')
        cm,cp,cpos,ctot=period_stats(cR,cST,period)
        rows.append({'period':period,'variant':'CONTROL',**cm,'positive_periods':cpos,'periods_total':ctot,
                     **event_stats(cEV)})
        period_details[f'{period}_CONTROL']=cp

        for h in HORIZONS:
            R,ST,ET,XT,SIDE,ev=simulate(p,ridx,h)
            m,pdets,pos,tot=period_stats(R,ST,period)
            es=event_stats(ev)
            rows.append({'period':period,'variant':f'EARLY_REJECTION_{h}M',**m,'positive_periods':pos,'periods_total':tot,**es})
            period_details[f'{period}_{h}M']=pdets
            if len(ev):
                ev=ev.copy();ev['period']=period;events_all.append(ev)
            ch=success(cm,m,cpos,pos,len(ev))
            if period=='forward_2026':
                ch['event_count_meaningful']=bool(len(ev)>=5)
            checks[f'{period}_{h}M']=ch

    comp=pd.DataFrame(rows)
    comp.to_csv(OUT/'comparison.csv',index=False)
    events=pd.concat(events_all,ignore_index=True) if events_all else pd.DataFrame()
    events.to_csv(OUT/'rejection_event_audit.csv',index=False)

    horizon_pass={}
    for h in HORIZONS:
        a=checks[f'historical_{h}M'];b=checks[f'forward_2026_{h}M']
        horizon_pass[str(h)]=bool(all(a.values()) and all(b.values()))

    result={
      'lab':'CROWDFADE_CF191G_POST_ENTRY_REJECTION_EARLY_EXIT_LAB_060',
      'definition':'first completed 1m close through opposite boundary of frozen pre-entry 5m range',
      'horizons_min':HORIZONS,
      'checks':checks,'horizon_PASS_both_periods':horizon_pass,
      'period_details':period_details,
      'limitations':[
        'Control management remains frozen M5 CF191g; rejection is observed on completed Binance 1m closes.',
        'If rejection occurs in the same M5 timestamp as a frozen control exit, control exit wins conservatively.',
        'BTCUSDT only; ETH/SOL transfer not established.',
        '2026 Mar-Aug is reused shadow/stress, not pristine OOS.',
        'No BE-ish modification tested; only full early exit on rejection.',
        'No entry filters or C/D gates are mixed into this LAB.'
      ]
    }
    (OUT/'summary.json').write_text(json.dumps(result,indent=2,default=float))

    lines=['# LAB060 — POST-ENTRY ABSORPTION REJECTION EARLY EXIT','',
      'CF191g entry core unchanged. Full stateful replay.','',
      '## Comparison','',comp.to_markdown(index=False),'',
      '## Preregistered checks','',json.dumps(checks,indent=2),'',
      '## Horizon PASS both periods','',json.dumps(horizon_pass,indent=2),'',
      '## Limitations']+[f"- {x}" for x in result['limitations']]
    if len(events):
        cols=['period','horizon_min','entry_ts','side','rejection_minute','early_R','original_R','delta_R','saved_R','given_up_R','original_exit_reason','mfe_60m','mae_60m']
        lines += ['','## Rejection event audit','',events[cols].to_markdown(index=False)]
    (OUT/'REPORT.md').write_text('\n'.join(lines))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__':
    main()
