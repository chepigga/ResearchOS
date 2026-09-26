from pathlib import Path
import json, zipfile, importlib.util
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)

p54=ROOT.parent/'CROWDFADE_CF191G_CAUSAL_REGIME_IMPULSE_MODEL_LAB_054'/'run.py'
sp=importlib.util.spec_from_file_location('lab54',p54)
lab54=importlib.util.module_from_spec(sp); sp.loader.exec_module(lab54)
lab53=lab54.lab53; lab43=lab54.lab43
lab54.DATA=DATA; lab53.DATA=DATA; lab43.DATA=DATA

EXPECT={
 'historical':{'N':5297,'SumR':700.3704107793633},
 'forward_2026':{'N':544,'SumR':35.49784078156513},
}
SL_ATR=1.50
TP_ATR=3.00
HOLD_S=6*3600

COSTS={
 'GROSS':{'spread_bps':0.0,'stop_slip_bps':0.0},
 'IC':{'spread_bps':0.597376,'stop_slip_bps':0.684253},
 'GETLEVERAGED':{'spread_bps':2.643809,'stop_slip_bps':0.291636},
}
METHODS=['MARKET_SIGNAL','CONFIRM_MARKET','RETRACE_LIMIT_5','RETRACE_LIMIT_10','RETRACE_LIMIT_15']

def metrics(a):
    a=np.asarray(a,float)
    if len(a)==0:return {'N':0,'WR':np.nan,'EV_R':np.nan,'PF':np.nan,'SumR':0.0,'MaxDD_R':0.0,'R_DD':np.nan}
    eq=np.cumsum(a); pk=np.maximum.accumulate(np.r_[0.,eq]); dd=float((pk[1:]-eq).max())
    pos=float(a[a>0].sum()); neg=float(abs(a[a<0].sum()))
    return {'N':int(len(a)),'WR':float((a>0).mean()),'EV_R':float(a.mean()),
            'PF':float(pos/neg) if neg>0 else 99.0,'SumR':float(a.sum()),
            'MaxDD_R':dd,'R_DD':float(a.sum()/dd) if dd>0 else 99.0}

def load_m1():
    rows=[]
    for zp in sorted((DATA/'all_1m').glob('BTCUSDT-1m-*.zip')):
        with zipfile.ZipFile(zp) as z:
            n=z.namelist()[0]
            with z.open(n) as f:
                q=pd.read_csv(f,header=None,usecols=[0,1,2,3,4])
        raw=pd.to_numeric(q.iloc[:,0],errors='coerce')
        op=pd.to_numeric(q.iloc[:,1],errors='coerce')
        hi=pd.to_numeric(q.iloc[:,2],errors='coerce')
        lo=pd.to_numeric(q.iloc[:,3],errors='coerce')
        cl=pd.to_numeric(q.iloc[:,4],errors='coerce')
        x=pd.DataFrame({'raw_ts':raw,'open':op,'high':hi,'low':lo,'close':cl}).dropna()
        rr=x.raw_ts.to_numpy(np.int64)
        sec=np.where(rr>10**14,rr//1_000_000,rr//1000)
        x['open_ts']=sec; x['end_ts']=sec+60
        rows.append(x[['open_ts','end_ts','open','high','low','close']])
    return pd.concat(rows,ignore_index=True).sort_values('open_ts').drop_duplicates('open_ts').reset_index(drop=True)

def find_open_idx(m1,t):
    a=m1.open_ts.to_numpy(np.int64)
    j=int(np.searchsorted(a,int(t),'left'))
    if j<len(a) and a[j]==int(t): return j
    return -1

def bidask(mid,spread_bps):
    h=spread_bps/20000.0
    return mid*(1.0-h), mid*(1.0+h)

def make_entry(event,p,m1,method):
    ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5=p
    sig_t=int(event.signal_ts); conf_t=int(event.entry_ts); side=int(event.side)
    ks=int(np.searchsorted(dt5,sig_t,'left'))
    kc=int(event.entry_k)
    if ks>=len(dt5) or dt5[ks]!=sig_t:return None
    sig_close=float(C5[ks]); conf_close=float(C5[kc]); atr=float(A5[ks])
    if not np.isfinite(atr) or atr<=0:return None

    if method=='MARKET_SIGNAL':
        j=find_open_idx(m1,sig_t)
        if j<0:return None
        return {'entry_ts':sig_t,'entry_mid':float(m1.open.iloc[j]),'atr':atr,'side':side,
                'signal_close':sig_close,'confirm_close':conf_close,
                'entry_improve_atr':side*(conf_close-float(m1.open.iloc[j]))/atr}

    if method=='CONFIRM_MARKET':
        j=find_open_idx(m1,conf_t)
        if j<0:return None
        return {'entry_ts':conf_t,'entry_mid':float(m1.open.iloc[j]),'atr':atr,'side':side,
                'signal_close':sig_close,'confirm_close':conf_close,'entry_improve_atr':0.0}

    ttl=int(method.rsplit('_',1)[1])
    target=0.5*(sig_close+conf_close)
    a=m1.open_ts.to_numpy(np.int64); hi=m1.high.to_numpy(float); lo=m1.low.to_numpy(float)
    j0=int(np.searchsorted(a,conf_t,'left'))
    j1=int(np.searchsorted(a,conf_t+ttl*60,'left'))
    if j0>=len(a):return None
    for j in range(j0,min(j1,len(a))):
        touched=(lo[j]<=target) if side>0 else (hi[j]>=target)
        if touched:
            return {'entry_ts':int(a[j]),'entry_mid':float(target),'atr':atr,'side':side,
                    'signal_close':sig_close,'confirm_close':conf_close,
                    'entry_improve_atr':side*(conf_close-target)/atr}
    return {'not_filled':True,'atr':atr,'side':side,'signal_close':sig_close,'confirm_close':conf_close}

def simulate_trade(m1,en,cost):
    side=int(en['side']); entry_mid=float(en['entry_mid']); atr=float(en['atr']); et=int(en['entry_ts'])
    sb=float(cost['spread_bps']); slip=float(cost['stop_slip_bps'])
    b0,a0=bidask(entry_mid,sb)
    entry=a0 if side>0 else b0
    risk=SL_ATR*atr
    sl=entry-side*risk; tp=entry+side*TP_ATR*atr

    a=m1.open_ts.to_numpy(np.int64); hi=m1.high.to_numpy(float); lo=m1.low.to_numpy(float); cl=m1.close.to_numpy(float)
    j0=int(np.searchsorted(a,et,'left'))
    j1=int(np.searchsorted(a,et+HOLD_S,'left'))
    if j0>=len(a):return None
    reason='TIME'; exitp=None; exit_ts=None
    for j in range(j0,min(j1,len(a))):
        low_bid,low_ask=bidask(float(lo[j]),sb)
        high_bid,high_ask=bidask(float(hi[j]),sb)
        if side>0:
            sh=low_bid<=sl; th=high_bid>=tp
        else:
            sh=high_ask>=sl; th=low_ask<=tp
        if sh or th:
            if sh:
                reason='SL'; exitp=sl*(1.0-side*slip/10000.0); exit_ts=int(a[j]); break
            reason='TP'; exitp=tp; exit_ts=int(a[j]); break
    if exitp is None:
        j=max(j0,min(len(a)-1,j1-1))
        b,aask=bidask(float(cl[j]),sb)
        exitp=b if side>0 else aask; exit_ts=int(a[j]+60)
    rr=side*(exitp-entry)/risk
    return {'R':float(rr),'reason':reason,'entry_fill':float(entry),'exit_fill':float(exitp),'exit_ts':exit_ts}

def build_events(label,p,m1):
    d=lab54.extract_cf191g_events(p)
    exp=EXPECT[label]
    if len(d)!=exp['N'] or abs(float(d.R.sum())-exp['SumR'])>1e-6:
        raise RuntimeError(f'canonical parity fail {label}: N={len(d)} SumR={d.R.sum()}')
    rows=[]
    for idx,r in d.iterrows():
        year=pd.to_datetime(int(r.signal_ts),unit='s',utc=True).year
        for method in METHODS:
            en=make_entry(r,p,m1,method)
            for cost_name,cost in COSTS.items():
                row={'period':label,'year':int(year),'event_id':int(idx),'signal_ts':int(r.signal_ts),
                     'confirm_ts':int(r.entry_ts),'side':int(r.side),'method':method,'cost_model':cost_name,
                     'filled':False,'R':np.nan,'reason':'NO_FILL','entry_improve_atr':np.nan}
                if en is not None:
                    row['entry_improve_atr']=float(en.get('entry_improve_atr',np.nan))
                    if not en.get('not_filled',False):
                        tr=simulate_trade(m1,en,cost)
                        if tr is not None:
                            row.update(tr); row['filled']=True
                rows.append(row)
    return pd.DataFrame(rows)

def summarize(events):
    out=[]
    total=events[['period','event_id']].drop_duplicates().groupby('period').size().to_dict()
    for (period,cost,method),g in events.groupby(['period','cost_model','method']):
        f=g[g.filled]; m=metrics(f.R.to_numpy(float))
        out.append({'period':period,'cost_model':cost,'method':method,'signals':int(total[period]),
                    'fills':int(len(f)),'fill_rate':float(len(f)/total[period]),**m,
                    'TP_rate':float((f.reason=='TP').mean()) if len(f) else np.nan,
                    'SL_rate':float((f.reason=='SL').mean()) if len(f) else np.nan,
                    'TIME_rate':float((f.reason=='TIME').mean()) if len(f) else np.nan,
                    'mean_entry_improve_atr':float(f.entry_improve_atr.mean()) if len(f) else np.nan})
    return pd.DataFrame(out)

def yearly(events):
    rows=[]
    q=events[(events.period=='historical') & events.filled]
    for (cost,method,year),g in q.groupby(['cost_model','method','year']):
        rows.append({'cost_model':cost,'method':method,'year':int(year),**metrics(g.R.to_numpy(float))})
    return pd.DataFrame(rows)

def missed_opportunity(events):
    rows=[]
    for period in events.period.unique():
        for cost in COSTS:
            base=events[(events.period==period)&(events.cost_model==cost)&(events.method=='CONFIRM_MARKET')][['event_id','R']].rename(columns={'R':'base_R'})
            for method in ['RETRACE_LIMIT_5','RETRACE_LIMIT_10','RETRACE_LIMIT_15']:
                x=events[(events.period==period)&(events.cost_model==cost)&(events.method==method)][['event_id','filled','R']]
                z=base.merge(x,on='event_id',how='left')
                miss=z[~z.filled]
                rows.append({'period':period,'cost_model':cost,'method':method,'missed_N':int(len(miss)),
                             'missed_control_sum_R':float(miss.base_R.sum()),
                             'missed_control_EV_R':float(miss.base_R.mean()) if len(miss) else np.nan})
    return pd.DataFrame(rows)

def promotion(summary,yr):
    checks=[]
    for method in METHODS:
        if method=='CONFIRM_MARKET':continue
        ok=True; detail={}
        for cost in ['IC','GETLEVERAGED']:
            for period in ['historical','forward_2026']:
                b=summary[(summary.cost_model==cost)&(summary.period==period)&(summary.method=='CONFIRM_MARKET')].iloc[0]
                c=summary[(summary.cost_model==cost)&(summary.period==period)&(summary.method==method)].iloc[0]
                cond=(c.EV_R>=b.EV_R and c.R_DD>=b.R_DD and c.PF>=b.PF)
                if method.startswith('RETRACE'): cond=cond and c.fill_rate>=0.50
                detail[f'{cost}_{period}']=bool(cond); ok &= bool(cond)
            if method.startswith('RETRACE'):
                yb=yr[(yr.cost_model==cost)&(yr.method=='CONFIRM_MARKET')].set_index('year')
                yc=yr[(yr.cost_model==cost)&(yr.method==method)].set_index('year')
                annual=True
                for y in sorted(set(yb.index)&set(yc.index)):
                    bsum=float(yb.loc[y,'SumR']); csum=float(yc.loc[y,'SumR'])
                    if bsum>0 and csum < 0.8*bsum: annual=False
                detail[f'{cost}_annual_no_gt20pct_drop']=annual; ok &= annual
        checks.append({'method':method,'promote':bool(ok),'detail':json.dumps(detail,sort_keys=True)})
    return pd.DataFrame(checks)

def main():
    m1=load_m1()
    ft,fz=lab43.load_flow(); hist_raw=lab43.load_hist(); sec_raw=lab43.load_sec()
    hist=lab43.prep(hist_raw,ft,fz,int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-01-01',tz='UTC').timestamp()))
    fwd=lab43.prep(sec_raw,ft,fz,int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()))
    ev=pd.concat([build_events('historical',hist,m1),build_events('forward_2026',fwd,m1)],ignore_index=True)
    ev.to_csv(OUT/'events.csv',index=False)
    s=summarize(ev); s.to_csv(OUT/'summary_by_method.csv',index=False)
    y=yearly(ev); y.to_csv(OUT/'historical_yearly.csv',index=False)
    mo=missed_opportunity(ev); mo.to_csv(OUT/'missed_opportunity.csv',index=False)
    pr=promotion(s,y); pr.to_csv(OUT/'promotion_checks.csv',index=False)
    (OUT/'REPORT.md').write_text('\n'.join([
      '# LAB072 — CF191g EXECUTION LAYER ENTRY METHOD','',
      '## Summary','',s.to_markdown(index=False),'',
      '## Promotion checks','',pr.to_markdown(index=False),'',
      '## Missed opportunity for passive limits','',mo.to_markdown(index=False),'',
      '## Historical yearly','',y.to_markdown(index=False),'',
      'Notes: frozen canonical signal universe; fixed 2R execution comparator; no stateful occupancy change; broker cost models from BFP004 + LAB050.'
    ]))
    (OUT/'summary.json').write_text(json.dumps({'lab':'LAB072','promoted':pr[pr.promote].method.tolist(),
      'costs':COSTS,'methods':METHODS},indent=2))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__':main()
