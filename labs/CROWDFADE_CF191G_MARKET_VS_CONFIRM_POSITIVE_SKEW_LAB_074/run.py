from pathlib import Path
import json, importlib.util
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)

p73=ROOT.parent/'CROWDFADE_CF191G_MARKET_VS_CONFIRM_STATEFUL_LAB_073'/'run.py'
sp=importlib.util.spec_from_file_location('lab73',p73)
lab73=importlib.util.module_from_spec(sp); sp.loader.exec_module(lab73)
lab72=lab73.lab72; lab54=lab73.lab54; lab53=lab73.lab53; lab43=lab73.lab43
for m in [lab73,lab72,lab54,lab53,lab43]:
    if hasattr(m,'DATA'): m.DATA=DATA

COSTS=lab72.COSTS
MODES=['MARKET_RAW','CONFIRM_CANONICAL']
SL_ATR=1.50
HOLD_S=6*3600
BE_ARM=3.00
BE_LOCK=2.25
TRAIL_ARM=3.50
TRAIL_GAP=0.50

def metrics(a):
    a=np.asarray(a,float)
    if len(a)==0:
        return {'N':0,'WR':np.nan,'EV_R':np.nan,'PF':np.nan,'SumR':0.0,'MaxDD_R':0.0,'R_DD':np.nan,'MaxConsecutiveLosses':0}
    eq=np.cumsum(a); pk=np.maximum.accumulate(np.r_[0.,eq]); dd=float((pk[1:]-eq).max())
    pos=float(a[a>0].sum()); neg=float(abs(a[a<0].sum()))
    streak=best=0
    for x in a:
        streak=streak+1 if x<0 else 0
        best=max(best,streak)
    return {'N':int(len(a)),'WR':float((a>0).mean()),'EV_R':float(a.mean()),
            'PF':float(pos/neg) if neg>0 else 99.0,'SumR':float(a.sum()),
            'MaxDD_R':dd,'R_DD':float(a.sum()/dd) if dd>0 else 99.0,
            'MaxConsecutiveLosses':int(best)}

def ba(mid,spread_bps):
    h=spread_bps/20000.0
    return mid*(1.0-h),mid*(1.0+h)

def manage(dt5,H5,L5,C5,ei,side,entry_mid,atr,cost):
    sb=float(cost['spread_bps']); slip=float(cost['stop_slip_bps'])
    b0,a0=ba(entry_mid,sb)
    entry=a0 if side>0 else b0
    stop0=entry-side*SL_ATR*atr
    pending=stop0
    peak_exec=entry
    xe=min(len(dt5)-1,int(np.searchsorted(dt5,int(dt5[ei])+HOLD_S,'left')))
    exitp=None; ex=xe; reason='TIME'

    for q in range(ei+1,xe+1):
        stop=pending
        low_bid,low_ask=ba(float(L5[q]),sb)
        high_bid,high_ask=ba(float(H5[q]),sb)

        stop_hit=(low_bid<=stop) if side>0 else (high_ask>=stop)
        if stop_hit:
            exitp=stop*(1.0-side*slip/10000.0)
            ex=q
            protected=(side>0 and stop>entry) or (side<0 and stop<entry)
            reason='PROTECTED_STOP' if protected else 'INITIAL_STOP'
            break

        if side>0:
            favorable=high_bid
            if favorable>peak_exec: peak_exec=favorable
            mfe=(peak_exec-entry)/atr
        else:
            favorable=low_ask
            if favorable<peak_exec: peak_exec=favorable
            mfe=(entry-peak_exec)/atr

        ns=stop
        if mfe>=BE_ARM:
            lvl=entry+side*BE_LOCK*atr
            if (side>0 and lvl>ns) or (side<0 and lvl<ns): ns=lvl
        if mfe>=TRAIL_ARM:
            lvl=peak_exec-side*TRAIL_GAP*atr
            if (side>0 and lvl>ns) or (side<0 and lvl<ns): ns=lvl
        pending=ns

    if exitp is None:
        b,a=ba(float(C5[xe]),sb)
        exitp=b if side>0 else a
        ex=xe
        reason='TIME'

    rr=side*(exitp-entry)/(SL_ATR*atr)
    return float(rr),int(ex),reason,float(entry),float(exitp)

def replay(p,mode,cost):
    ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5=p
    rows=[]
    k=0; day=-1; dc=0; nextts=0; last=0.; la=0.; has=False
    conf=False; cs=0; cp=0.; ca=0.; ct=0; cb=0; mf=0.; ma=0.
    skips={'timeout':0,'adverse':0,'side':0,'minz':0,'response':0,'pause':0}

    while k<len(dt5)-3:
        t=int(dt5[k]); z=float(Z5[k])
        if t<nextts:
            k+=1; continue
        d=t//86400
        if d!=day: day=d; dc=0
        if dc>=lab53.MAXDAY:
            conf=False; k+=1; continue

        if mode=='CONFIRM_CANONICAL' and conf:
            side=cs
            fav=((cp-L5[k]) if side<0 else (H5[k]-cp))/ca
            adv=((H5[k]-cp) if side<0 else (cp-L5[k]))/ca
            mf=max(mf,max(0.0,float(fav))); ma=max(ma,max(0.0,float(adv)))
            cb-=1; age=t-ct
            if cb<=0 or age>2700:
                skips['timeout']+=1; conf=False; k+=1; continue
            if ma>lab53.G_MAX_ADV:
                skips['adverse']+=1; conf=False; k+=1; continue
            target=cp+side*lab53.CONF_ATR*ca
            confirmed=(C5[k]>=target) if side>0 else (C5[k]<=target)
            if not confirmed:
                k+=1; continue
            same=(z<0.0) if side>0 else (z>0.0)
            if not same:
                skips['side']+=1; conf=False; k+=1; continue
            if abs(z)<lab53.G_MIN_ABS_Z:
                skips['minz']+=1; conf=False; k+=1; continue
            response=mf/(ma+1e-9)
            if response<lab53.G_MIN_RESPONSE:
                skips['response']+=1; conf=False; k+=1; continue
            conf=False
            if has and abs(float(C5[k])-last)<lab53.PAUSE_ATR*la:
                skips['pause']+=1; k+=1; continue

            rr,ex,reason,entry,exitp=manage(dt5,H5,L5,C5,k,side,float(C5[k]),ca,cost)
            rows.append({'signal_ts':ct,'entry_ts':t,'exit_ts':int(dt5[ex]),'side':side,
                         'R':rr,'reason':reason,'entry_fill':entry,'exit_fill':exitp})
            dc+=1; last=float(C5[k]); la=ca; has=True; nextts=int(dt5[ex])+1
            k=int(np.searchsorted(dt5,nextts)); continue

        side=-1 if z>=lab53.ZTH else (1 if z<=-lab53.ZTH else 0)
        if side==0:
            k+=1; continue
        if has and abs(float(C5[k])-last)<lab53.PAUSE_ATR*la:
            skips['pause']+=1; k+=1; continue

        if mode=='MARKET_RAW':
            atr=float(A5[k])
            rr,ex,reason,entry,exitp=manage(dt5,H5,L5,C5,k,side,float(C5[k]),atr,cost)
            rows.append({'signal_ts':t,'entry_ts':t,'exit_ts':int(dt5[ex]),'side':side,
                         'R':rr,'reason':reason,'entry_fill':entry,'exit_fill':exitp})
            dc+=1; last=float(C5[k]); la=atr; has=True; nextts=int(dt5[ex])+1
            k=int(np.searchsorted(dt5,nextts)); continue

        conf=True; cs=side; cp=float(C5[k]); ca=float(A5[k]); ct=t; cb=9; mf=0.; ma=0.
        k+=1

    return pd.DataFrame(rows),skips

def summary_row(period,cost,mode,d):
    m=metrics(d.R.to_numpy(float))
    return {'period':period,'cost_model':cost,'mode':mode,**m,
            'InitialStopRate':float((d.reason=='INITIAL_STOP').mean()) if len(d) else np.nan,
            'ProtectedStopRate':float((d.reason=='PROTECTED_STOP').mean()) if len(d) else np.nan,
            'TimeExitRate':float((d.reason=='TIME').mean()) if len(d) else np.nan,
            'RightTail_ge1p5R':float((d.R>=1.5).mean()) if len(d) else np.nan,
            'RightTail_ge2R':float((d.R>=2.0).mean()) if len(d) else np.nan}

def period_rows(label,cost,mode,d):
    t=pd.to_datetime(d.signal_ts,unit='s',utc=True)
    key=t.dt.year.astype(str) if label=='historical' else t.dt.strftime('%Y-%m')
    rows=[]
    for kk,g in d.groupby(key):
        rows.append({'period':label,'cost_model':cost,'mode':mode,'subperiod':str(kk),**metrics(g.R.to_numpy(float))})
    return rows

def promotion(s,pr):
    detail={}; ok=True
    for cost in ['IC','GETLEVERAGED']:
        for period in ['historical','forward_2026']:
            b=s[(s['cost_model']==cost)&(s['period']==period)&(s['mode']=='CONFIRM_CANONICAL')].iloc[0]
            c=s[(s['cost_model']==cost)&(s['period']==period)&(s['mode']=='MARKET_RAW')].iloc[0]
            cond=(c.EV_R>=b.EV_R and c.PF>=b.PF and c.R_DD>=b.R_DD and
                  c.MaxDD_R<=1.25*b.MaxDD_R and c.N>=200)
            if period=='forward_2026':
                cond=cond and c.SumR>0
            detail[f'{cost}_{period}']=bool(cond); ok &= bool(cond)

        yy=pr[(pr.cost_model==cost)&(pr['mode']=='MARKET_RAW')&(pr.period=='historical')]
        allpos=(len(yy)>=5 and bool((yy.SumR>0).all()))
        detail[f'{cost}_all_5_hist_years_positive']=allpos; ok &= allpos
    return {'candidate':'MARKET_RAW','promote':bool(ok),'detail':detail}

def main():
    ft,fz=lab43.load_flow(); hist_raw=lab43.load_hist(); sec_raw=lab43.load_sec()
    frames={
      'historical':lab43.prep(hist_raw,ft,fz,int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-01-01',tz='UTC').timestamp())),
      'forward_2026':lab43.prep(sec_raw,ft,fz,int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()))
    }

    sr=[]; pr=[]; alltr=[]; skiprows=[]
    for label,p in frames.items():
        for cost_name,cost in COSTS.items():
            for mode in MODES:
                d,sk=replay(p,mode,cost)
                d['period']=label; d['cost_model']=cost_name; d['mode']=mode
                alltr.append(d); sr.append(summary_row(label,cost_name,mode,d))
                pr.extend(period_rows(label,cost_name,mode,d))
                skiprows.append({'period':label,'cost_model':cost_name,'mode':mode,**sk})

    s=pd.DataFrame(sr); periods=pd.DataFrame(pr); trades=pd.concat(alltr,ignore_index=True); skips=pd.DataFrame(skiprows)
    promo=promotion(s,periods)
    s.to_csv(OUT/'summary.csv',index=False)
    periods.to_csv(OUT/'subperiods.csv',index=False)
    trades.to_csv(OUT/'trades.csv',index=False)
    skips.to_csv(OUT/'skips.csv',index=False)
    (OUT/'promotion.json').write_text(json.dumps(promo,indent=2))
    (OUT/'REPORT.md').write_text('\n'.join([
      '# LAB074 — MARKET vs CONFIRM / CANONICAL POSITIVE-SKEW MANAGEMENT','',
      '## Summary','',s.to_markdown(index=False),'',
      '## Promotion','',json.dumps(promo,indent=2),'',
      '## Historical years / 2026 months','',periods.to_markdown(index=False),'',
      '## Skips','',skips.to_markdown(index=False)
    ]))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__': main()
