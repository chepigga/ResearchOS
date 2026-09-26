from pathlib import Path
import json, importlib.util
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)

p53=ROOT.parent/'CROWDFADE_THREE_BOT_FIXES_HISTORICAL_REPLAY_LAB_053'/'run.py'
sp=importlib.util.spec_from_file_location('lab53',p53)
lab53=importlib.util.module_from_spec(sp); sp.loader.exec_module(lab53)
lab43=lab53.lab43
lab53.DATA=DATA; lab43.DATA=DATA

EXPECT={'historical':(5297,700.3704107793633,8),'forward_2026':(544,35.49784078156513,3)}
REASON={1:'INITIAL_STOP',2:'PROFIT_STOP',4:'TIME_EXIT'}

def fmt_ts(x):
    return pd.to_datetime(int(x),unit='s',utc=True).strftime('%Y-%m-%d %H:%M:%S') if pd.notna(x) else ''

def excursion(dt5,H5,L5,C5,k,side,entry,atr,mins):
    if not np.isfinite(atr) or atr<=0: return (np.nan,np.nan,np.nan)
    end_t=dt5[k]+mins*60
    e=np.searchsorted(dt5,end_t,'right')
    if e<=k+1: return (0.0,0.0,0.0)
    hh=H5[k+1:e]; ll=L5[k+1:e]
    if len(hh)==0:return (0.0,0.0,0.0)
    if side>0:
        mfe=(np.nanmax(hh)-entry)/atr
        mae=(entry-np.nanmin(ll))/atr
    else:
        mfe=(entry-np.nanmin(ll))/atr
        mae=(np.nanmax(hh)-entry)/atr
    ci=min(len(C5)-1,e-1)
    ret=side*(C5[ci]-entry)/atr
    return (float(mfe),float(mae),float(ret))

def simulate(p, gate):
    ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5=p
    trades=[]; triggers=[]
    k=0;day=-1;dc=0;nextts=0;last=0.;la=0.;has=False
    conf=False;cs=0;cp=0.;ca=0.;ct=0;cb=0;mf=0.;ma=0.;sigz=np.nan
    while k<len(dt5)-3:
        t=int(dt5[k]); z=float(Z5[k])
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
            cb-=1; age=t-ct
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

            ret60=np.nan; eff60=np.nan; ret15=np.nan
            if k>=12 and np.isfinite(A5[k]) and A5[k]>0:
                p60=C5[k-12:k+1]
                ret60=side*(p60[-1]-p60[0])/A5[k]
                path=np.abs(np.diff(p60)).sum()
                if path>0: eff60=side*(p60[-1]-p60[0])/path
                ret15=side*(C5[k]-C5[k-3])/A5[k]
            is_d=(np.isfinite(ret60) and np.isfinite(eff60) and np.isfinite(ret15)
                  and ret60>1.0 and eff60<0.25 and ret15<=0.0)

            entry=float(C5[k]); atr=float(ca)
            rr,ex,reason=lab53.manage_cf191g(dt5,H5,L5,C5,k,side,entry,atr)
            ex=int(ex); exit_ts=int(dt5[ex])

            if gate and is_d:
                row={
                  'signal_ts':int(ct),'entry_ts':t,'side':int(side),'entry_k':int(k),
                  'entry_price':entry,'atr':atr,'signal_z':float(sigz),'confirm_z':z,
                  'confirm_age_min':age/60.0,'pre_fav_atr':mf,'pre_adv_atr':ma,
                  'response_ratio':float(response),
                  'ret60_atr':float(ret60),'eff60':float(eff60),'ret15_dir':float(ret15),
                  'hyp_R':float(rr),'hyp_exit_ts':exit_ts,'hyp_exit_reason':REASON.get(int(reason),str(reason))
                }
                for h in [15,30,60,120,360]:
                    mfe,mae,ret=excursion(dt5,H5,L5,C5,k,side,entry,atr,h)
                    row[f'mfe_{h}m']=mfe;row[f'mae_{h}m']=mae;row[f'ret_{h}m']=ret
                triggers.append(row)
                k+=1;continue

            trades.append({
              'signal_ts':int(ct),'entry_ts':t,'side':int(side),'entry_k':int(k),
              'entry_price':entry,'atr':atr,'R':float(rr),'exit_ts':exit_ts,
              'exit_reason':REASON.get(int(reason),str(reason)),
              'ret60_atr':float(ret60) if np.isfinite(ret60) else np.nan,
              'eff60':float(eff60) if np.isfinite(eff60) else np.nan,
              'ret15_dir':float(ret15) if np.isfinite(ret15) else np.nan,
            })
            dc+=1;last=entry;la=atr;has=True;nextts=exit_ts+1
            k+=1;continue

        side=-1 if z>=lab53.ZTH else (1 if z<=-lab53.ZTH else 0)
        if side==0:
            k+=1;continue
        if has and abs(C5[k]-last)<lab53.PAUSE_ATR*la:
            k+=1;continue
        conf=True;cs=side;cp=float(C5[k]);ca=float(A5[k]);ct=t;cb=9;mf=0.;ma=0.;sigz=z
        k+=1

    return pd.DataFrame(trades),pd.DataFrame(triggers)

def key(row):
    return (int(row.signal_ts),int(row.entry_ts),int(row.side))

def audit_period(period,p):
    ctrl,_=simulate(p,False)
    gated,trig=simulate(p,True)

    expN,expR,expSkip=EXPECT[period]
    if len(ctrl)!=expN or abs(float(ctrl.R.sum())-expR)>1e-6:
        raise RuntimeError(f'control parity fail {period}: {len(ctrl)} {ctrl.R.sum()}')
    if len(trig)!=expSkip:
        raise RuntimeError(f'trigger count fail {period}: {len(trig)} expected {expSkip}')

    ctrl_map={key(r):i for i,r in ctrl.iterrows()}
    gated_map={key(r):i for i,r in gated.iterrows()}
    common=set(ctrl_map).intersection(gated_map)

    out=[]
    for j,tr in trig.iterrows():
        t0=int(tr.entry_ts); k0=key(tr)
        exact_i=ctrl_map.get(k0,None)

        # first actual gated trade after the skipped candidate
        g_after=gated[gated.entry_ts>t0]
        ng=g_after.iloc[0] if len(g_after) else None

        # first control trade after candidate time (excluding exact candidate itself)
        c_after=ctrl[ctrl.entry_ts>t0]
        nc=c_after.iloc[0] if len(c_after) else None

        # strict state resync = first future exact trade key present in both paths
        fut=[]
        for ck in common:
            ci=ctrl_map[ck]; gi=gated_map[ck]
            et=int(ctrl.iloc[ci].entry_ts)
            if et>t0:
                fut.append((et,ck,ci,gi))
        fut.sort()
        if fut:
            rs_t,rs_key,ci,gi=fut[0]
            cseq=ctrl[(ctrl.entry_ts>=t0)&(ctrl.entry_ts<rs_t)]
            gseq=gated[(gated.entry_ts>=t0)&(gated.entry_ts<rs_t)]
            csum=float(cseq.R.sum());gsum=float(gseq.R.sum())
            resync_delay=(rs_t-t0)/60.0
            resync_signal_ts=int(ctrl.iloc[ci].signal_ts)
            cN=len(cseq);gN=len(gseq)
        else:
            cseq=ctrl[ctrl.entry_ts>=t0];gseq=gated[gated.entry_ts>=t0]
            csum=float(cseq.R.sum());gsum=float(gseq.R.sum())
            resync_delay=np.nan;resync_signal_ts=np.nan;cN=len(cseq);gN=len(gseq)

        row=tr.to_dict()
        row.update({
          'period':period,'event_no':j+1,
          'side_name':'BUY' if tr.side>0 else 'SELL',
          'signal_time':fmt_ts(tr.signal_ts),'entry_time':fmt_ts(tr.entry_ts),
          'hyp_exit_time':fmt_ts(tr.hyp_exit_ts),
          'control_exact_match':exact_i is not None,
          'control_exact_R':float(ctrl.iloc[exact_i].R) if exact_i is not None else np.nan,
          'control_exact_exit_reason':ctrl.iloc[exact_i].exit_reason if exact_i is not None else '',
          'next_D_delay_min':((int(ng.entry_ts)-t0)/60.0) if ng is not None else np.nan,
          'next_D_side':('BUY' if ng is not None and ng.side>0 else ('SELL' if ng is not None else '')),
          'next_D_signal_time':fmt_ts(ng.signal_ts) if ng is not None else '',
          'next_D_entry_time':fmt_ts(ng.entry_ts) if ng is not None else '',
          'next_D_R':float(ng.R) if ng is not None else np.nan,
          'next_control_delay_min':((int(nc.entry_ts)-t0)/60.0) if nc is not None else np.nan,
          'next_control_side':('BUY' if nc is not None and nc.side>0 else ('SELL' if nc is not None else '')),
          'next_control_R':float(nc.R) if nc is not None else np.nan,
          'resync_delay_min':resync_delay,
          'control_R_until_resync':csum,'D_R_until_resync':gsum,
          'stateful_delta_R':gsum-csum,'control_trades_until_resync':cN,'D_trades_until_resync':gN,
          'direct_skip_label':'GOOD_SKIP' if tr.hyp_R<0 else ('BAD_SKIP' if tr.hyp_R>0 else 'FLAT_SKIP'),
          'stateful_label':'GOOD' if (gsum-csum)>1e-9 else ('BAD' if (gsum-csum)<-1e-9 else 'FLAT')
        })
        out.append(row)
    return ctrl,gated,pd.DataFrame(out)

def main():
    ft,fz=lab43.load_flow();hist=lab43.load_hist();sec=lab43.load_sec()
    periods={
      'historical':lab43.prep(hist,ft,fz,int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-01-01',tz='UTC').timestamp())),
      'forward_2026':lab43.prep(sec,ft,fz,int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()))
    }
    audits=[];summary=[]
    for period,p in periods.items():
        ctrl,gated,a=audit_period(period,p);audits.append(a)
        summary.append({
          'period':period,'triggers':len(a),
          'direct_good_skips':int((a.direct_skip_label=='GOOD_SKIP').sum()),
          'direct_bad_skips':int((a.direct_skip_label=='BAD_SKIP').sum()),
          'stateful_good':int((a.stateful_label=='GOOD').sum()),
          'stateful_bad':int((a.stateful_label=='BAD').sum()),
          'hyp_R_sum':float(a.hyp_R.sum()),
          'stateful_delta_R_sum_event_windows':float(a.stateful_delta_R.sum()),
          'control_N':len(ctrl),'D_N':len(gated),
          'control_SumR':float(ctrl.R.sum()),'D_SumR':float(gated.R.sum()),
          'net_full_period_delta_R':float(gated.R.sum()-ctrl.R.sum())
        })
    audit=pd.concat(audits,ignore_index=True)
    audit.to_csv(OUT/'D_EVENT_AUDIT_11.csv',index=False)
    pd.DataFrame(summary).to_csv(OUT/'D_EVENT_AUDIT_SUMMARY.csv',index=False)

    cols=['period','event_no','signal_time','entry_time','side_name',
          'ret60_atr','eff60','ret15_dir','confirm_age_min',
          'hyp_R','hyp_exit_reason','mfe_15m','mae_15m','mfe_60m','mae_60m','mfe_120m','mae_120m',
          'control_exact_match','next_D_delay_min','next_D_side','next_D_R',
          'resync_delay_min','control_R_until_resync','D_R_until_resync','stateful_delta_R',
          'direct_skip_label','stateful_label']
    report=['# LAB055D — EVENT AUDIT OF 11 D TRIGGERS','',
            'Descriptive audit. No new threshold or strategy change.','',
            '## Aggregate','',pd.DataFrame(summary).to_markdown(index=False),'',
            '## Event table','',audit[cols].to_markdown(index=False),'',
            '## Notes','',
            '- hyp_R = result if the skipped candidate were taken with frozen CF191g positive-skew management.',
            '- next_D = first actual trade reached by the D state machine after the skip.',
            '- stateful_delta_R = D-path cumulative R minus control cumulative R from trigger until first strict future resync trade.',
            '- An exact control match can be absent for later triggers because earlier skips alter occupancy/reachability.',
            '- MFE/MAE are ATR-normalized from the candidate entry using completed M5 high/low windows.',
            '- 2026 Mar–Aug remains reused shadow/stress, not pristine OOS.']
    (OUT/'D_EVENT_AUDIT_REPORT.md').write_text('\n'.join(report))
    result={'lab':'LAB055D_EVENT_AUDIT','summary':summary,'events':audit[cols].to_dict('records')}
    (OUT/'D_EVENT_AUDIT.json').write_text(json.dumps(result,indent=2,default=float))
    print((OUT/'D_EVENT_AUDIT_REPORT.md').read_text())

if __name__=='__main__':
    main()
