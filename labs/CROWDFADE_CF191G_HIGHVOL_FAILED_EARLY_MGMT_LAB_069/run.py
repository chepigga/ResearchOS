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
 'historical':{'N':5297,'SumR':700.3704107793633},
 'forward_2026':{'N':544,'SumR':35.49784078156513},
}
LB=2016
REASON={1:'INITIAL_STOP',2:'PROFIT_STOP',4:'TIME_EXIT'}

def metrics(a): return lab43.metrics(np.asarray(a,float))

def load_m1():
    rows=[]
    for zp in sorted((DATA/'all_1m').glob('BTCUSDT-1m-*.zip')):
        with zipfile.ZipFile(zp) as z:
            n=z.namelist()[0]
            with z.open(n) as f:
                q=pd.read_csv(f,header=None,usecols=[0,4])
        raw=pd.to_numeric(q.iloc[:,0],errors='coerce')
        cl=pd.to_numeric(q.iloc[:,1],errors='coerce')
        x=pd.DataFrame({'raw_ts':raw,'close':cl}).dropna()
        rr=x.raw_ts.to_numpy(np.int64)
        sec=np.where(rr>10**14,rr//1_000_000,rr//1000)
        x['end_ts']=sec+60
        rows.append(x[['end_ts','close']])
    return pd.concat(rows,ignore_index=True).sort_values('end_ts').drop_duplicates('end_ts').reset_index(drop=True)

class EarlyStateIndex:
    def __init__(self,m1):
        self.end=m1.end_ts.to_numpy(np.int64)
        self.close=m1.close.to_numpy(float)

    def at15(self,entry_ts,side,entry,atr):
        j=np.searchsorted(self.end,int(entry_ts)+60,'left')
        if j>=len(self.end) or self.end[j]!=int(entry_ts)+60:
            return None
        idx=np.arange(j,j+15)
        if idx[-1]>=len(self.end): return None
        expected=np.arange(int(entry_ts)+60,int(entry_ts)+16*60,60)
        if not np.array_equal(self.end[idx],expected): return None
        closes=self.close[idx]
        steps=np.diff(np.r_[entry,closes])
        expansion=float(side*(closes[-1]-entry)/atr)
        denom=float(np.sum(np.abs(steps)))
        eff=float(side*(closes[-1]-entry)/(denom+1e-12))
        return {
          'ts':int(self.end[idx[-1]]),
          'close':float(closes[-1]),
          'expansion15_atr':expansion,
          'eff15':eff,
          'failed_early':bool(expansion<=0 or eff<=0)
        }

def build_vol_pct(p):
    C5,A5=p[8],p[10]
    vm=A5/C5
    pct=np.full(len(vm),np.nan)
    for k in range(LB,len(vm)):
        hist=vm[k-LB:k]
        if np.all(np.isfinite(hist)) and np.isfinite(vm[k]):
            pct[k]=float(np.mean(hist<=vm[k]))
    return pct

def simulate(p,eidx,enable_action):
    ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5=p
    vp=build_vol_pct(p)
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
            ctrl_xt=int(dt5[int(ex0)])
            rr=float(rr0);xt=ctrl_xt;reason=REASON.get(int(reason0),str(reason0))

            st=eidx.at15(t,side,entry,atr)
            highvol=bool(np.isfinite(vp[k]) and vp[k]>=0.80)
            if enable_action and st is not None and highvol and st['failed_early'] and ctrl_xt>int(st['ts']):
                rr=side*(float(st['close'])-entry)/(lab53.SL_ATR*atr)-(lab53.COST_BPS/10000.)*entry/(lab53.SL_ATR*atr)
                xt=int(st['ts']);reason='HIGHVOL_FAILED_EARLY_EXIT'
                events.append({
                  'entry_ts':t,'side':int(side),'vol_percentile':float(vp[k]),
                  'expansion15_atr':float(st['expansion15_atr']),'eff15':float(st['eff15']),
                  'early_exit_R':float(rr),'original_R':float(rr0),
                  'delta_R':float(rr-rr0),
                  'saved_R':float(max(rr-rr0,0.0)),
                  'given_up_R':float(max(rr0-rr,0.0)),
                  'original_exit_ts':ctrl_xt,
                  'original_exit_reason':REASON.get(int(reason0),str(reason0)),
                  'original_right_tail':bool(rr0>=1.5)
                })

            R[n]=rr;ST[n]=int(ct);ET[n]=t;XT[n]=xt;SIDE[n]=side;n+=1
            dc+=1;last=entry;la=atr;has=True;nextts=xt+1
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
    m=metrics(R)
    t=pd.to_datetime(ST,unit='s',utc=True)
    keys=t.year.astype(str).to_numpy() if period=='historical' else t.to_period('M').astype(str).to_numpy()
    details={}
    for key in sorted(set(keys)):
        details[str(key)]=metrics(np.asarray(R)[keys==key].astype(float))
    pos=sum(1 for x in details.values() if x.get('SumR',0)>0)
    return m,details,pos,len(details)

def event_stats(ev):
    if len(ev)==0:
        return {'action_count':0,'total_saved_R':0.0,'total_given_up_R':0.0,'net_local_delta_R':0.0,
                'mean_saved_R':0.0,'mean_given_up_R':0.0,'original_initial_stop_share':np.nan,
                'original_right_tail_share':np.nan}
    return {
      'action_count':int(len(ev)),
      'total_saved_R':float(ev.saved_R.sum()),
      'total_given_up_R':float(ev.given_up_R.sum()),
      'net_local_delta_R':float(ev.delta_R.sum()),
      'mean_saved_R':float(ev.saved_R.mean()),
      'mean_given_up_R':float(ev.given_up_R.mean()),
      'original_initial_stop_share':float((ev.original_exit_reason=='INITIAL_STOP').mean()),
      'original_right_tail_share':float(ev.original_right_tail.mean())
    }

def check(period,c,cm,cpos,m,pos,evn):
    need=100 if period=='historical' else 20
    return {
      'R_DD_not_worse':bool(m['R_DD']>=cm['R_DD']),
      'SumR_ge_98pct_control':bool(m['SumR']>=0.98*cm['SumR']),
      'PF_ge_control_or_DD_better':bool(m['PF']>=cm['PF'] or m['MaxDD_R']<cm['MaxDD_R']),
      'max_consecutive_losses_not_worse':bool(m['MaxConsecutiveLosses']<=cm['MaxConsecutiveLosses']),
      'positive_periods_not_worse':bool(pos>=cpos),
      'event_count_meaningful':bool(evn>=need)
    }

def main():
    m1=load_m1();eidx=EarlyStateIndex(m1)
    ft,fz=lab43.load_flow();hist_raw=lab43.load_hist();sec_raw=lab43.load_sec()
    periods={
      'historical':lab43.prep(hist_raw,ft,fz,int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-01-01',tz='UTC').timestamp())),
      'forward_2026':lab43.prep(sec_raw,ft,fz,int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()))
    }

    rows=[];checks={};details={};all_ev=[]
    for period,p in periods.items():
        cR,cST,cET,cXT,cSIDE,cEV=simulate(p,eidx,False)
        exp=EXPECT[period]
        if len(cR)!=exp['N'] or abs(float(cR.sum())-exp['SumR'])>1e-6:
            raise RuntimeError(f'control parity fail {period}: {len(cR)} {cR.sum()}')
        cm,cd,cpos,ctot=period_stats(cR,cST,period)
        rows.append({'period':period,'variant':'CONTROL',**cm,'positive_periods':cpos,'periods_total':ctot,**event_stats(cEV)})
        details[f'{period}_CONTROL']=cd

        R,ST,ET,XT,SIDE,ev=simulate(p,eidx,True)
        m,dets,pos,tot=period_stats(R,ST,period)
        es=event_stats(ev)
        rows.append({'period':period,'variant':'HIGHVOL_FAILED_EARLY_EXIT_15M',**m,'positive_periods':pos,'periods_total':tot,**es})
        details[f'{period}_LAB069']=dets
        checks[period]=check(period,cR,cm,cpos,m,pos,len(ev))
        if len(ev):
            ev=ev.copy();ev['period']=period;all_ev.append(ev)

    comp=pd.DataFrame(rows);comp.to_csv(OUT/'comparison.csv',index=False)
    events=pd.concat(all_ev,ignore_index=True) if all_ev else pd.DataFrame()
    events.to_csv(OUT/'action_events.csv',index=False)
    overall=all(all(v.values()) for v in checks.values())

    result={
      'lab':'LAB069_HIGHVOL_FAILED_EARLY_STATEFUL_MGMT',
      'checks':checks,
      'PASS_BOTH_PERIODS':bool(overall),
      'period_details':details,
      'limitations':[
        'Full stateful replay; occupancy changes naturally after early exit.',
        'Action only at +15m completed 1m close, only P80_100 + FAILED_EARLY.',
        'BTCUSDT only; 2026 Mar-Aug reused shadow/stress.',
        'No softer action or threshold tuning tested.'
      ]
    }
    (OUT/'summary.json').write_text(json.dumps(result,indent=2,default=float))
    lines=['# LAB069 — HIGH-VOL FAILED-EARLY STATEFUL MANAGEMENT','',
      'One preregistered action: P80_100 + FAILED_EARLY at +15m -> full exit.','',
      '## Comparison','',comp.to_markdown(index=False),'',
      '## Checks','',json.dumps(checks,indent=2),'',
      f'PASS both periods: **{overall}**'
    ]
    if len(events):
        lines+=['','## Action events','',events.head(300).to_markdown(index=False)]
    (OUT/'REPORT.md').write_text('\n'.join(lines))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__': main()
