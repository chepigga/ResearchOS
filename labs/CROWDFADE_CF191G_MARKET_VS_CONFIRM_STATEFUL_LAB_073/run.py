from pathlib import Path
import json, importlib.util
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)

p72=ROOT.parent/'CROWDFADE_CF191G_EXECUTION_LAYER_ENTRY_METHOD_LAB_072'/'run.py'
sp=importlib.util.spec_from_file_location('lab72',p72)
lab72=importlib.util.module_from_spec(sp); sp.loader.exec_module(lab72)
lab54=lab72.lab54; lab53=lab72.lab53; lab43=lab72.lab43
lab72.DATA=DATA; lab54.DATA=DATA; lab53.DATA=DATA; lab43.DATA=DATA

COSTS=lab72.COSTS
SL_ATR=1.50; TP_ATR=3.0
MODES=['MARKET_RAW','CONFIRM_CANONICAL']

def metrics(a):
    return lab72.metrics(np.asarray(a,float))

def market_entry(m1,t,side,atr):
    j=lab72.find_open_idx(m1,t)
    if j<0:return None
    return {'entry_ts':int(t),'entry_mid':float(m1.open.iloc[j]),'atr':float(atr),'side':int(side)}

def stateful(p,m1,mode,cost):
    ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5=p
    rows=[]
    k=0; day=-1; dc=0; nextts=0; last=0.; la=0.; has=False
    conf=False; cs=0; cp=0.; ca=0.; ct=0; cb=0; mf=0.; ma=0.
    skips={'timeout':0,'adverse':0,'side':0,'minz':0,'response':0,'pause':0,'entry_missing':0}
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
            mf=max(mf,max(0.,float(fav))); ma=max(ma,max(0.,float(adv)))
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
            if has and abs(C5[k]-last)<lab53.PAUSE_ATR*la:
                skips['pause']+=1; k+=1; continue
            en=market_entry(m1,t,side,ca)
            if en is None:
                skips['entry_missing']+=1; k+=1; continue
            tr=lab72.simulate_trade(m1,en,cost)
            if tr is None:
                skips['entry_missing']+=1; k+=1; continue
            rows.append({'signal_ts':ct,'entry_ts':t,'exit_ts':tr['exit_ts'],'side':side,'R':tr['R'],'reason':tr['reason']})
            dc+=1; last=float(C5[k]); la=ca; has=True; nextts=int(tr['exit_ts'])+1
            k=np.searchsorted(dt5,nextts); continue

        side=-1 if z>=lab53.ZTH else (1 if z<=-lab53.ZTH else 0)
        if side==0:
            k+=1; continue
        if has and abs(C5[k]-last)<lab53.PAUSE_ATR*la:
            skips['pause']+=1; k+=1; continue

        if mode=='MARKET_RAW':
            atr=float(A5[k])
            en=market_entry(m1,t,side,atr)
            if en is None:
                skips['entry_missing']+=1; k+=1; continue
            tr=lab72.simulate_trade(m1,en,cost)
            if tr is None:
                skips['entry_missing']+=1; k+=1; continue
            rows.append({'signal_ts':t,'entry_ts':t,'exit_ts':tr['exit_ts'],'side':side,'R':tr['R'],'reason':tr['reason']})
            dc+=1; last=float(C5[k]); la=atr; has=True; nextts=int(tr['exit_ts'])+1
            k=np.searchsorted(dt5,nextts); continue

        conf=True; cs=side; cp=float(C5[k]); ca=float(A5[k]); ct=t; cb=9; mf=0.; ma=0.
        k+=1

    return pd.DataFrame(rows),skips

def summarize(label,cost_name,mode,d):
    m=metrics(d.R.to_numpy(float))
    return {'period':label,'cost_model':cost_name,'mode':mode,**m,
            'TP_rate':float((d.reason=='TP').mean()) if len(d) else np.nan,
            'SL_rate':float((d.reason=='SL').mean()) if len(d) else np.nan,
            'TIME_rate':float((d.reason=='TIME').mean()) if len(d) else np.nan}

def yearly(label,cost_name,mode,d):
    rows=[]
    if label!='historical':return rows
    y=pd.to_datetime(d.signal_ts,unit='s',utc=True).dt.year
    for yy,g in d.groupby(y):
        rows.append({'cost_model':cost_name,'mode':mode,'year':int(yy),**metrics(g.R.to_numpy(float))})
    return rows

def promotion(s,y):
    detail={}; ok=True
    for cost in ['IC','GETLEVERAGED']:
        for period in ['historical','forward_2026']:
            b=s[(s.cost_model==cost)&(s.period==period)&(s.mode=='CONFIRM_CANONICAL')].iloc[0]
            c=s[(s.cost_model==cost)&(s.period==period)&(s.mode=='MARKET_RAW')].iloc[0]
            cond=(c.EV_R>=b.EV_R and c.PF>=b.PF and c.R_DD>=b.R_DD and c.MaxDD_R<=1.5*b.MaxDD_R and c.N>=200)
            detail[f'{cost}_{period}']=bool(cond); ok &= bool(cond)
        yy=y[(y.cost_model==cost)&(y.mode=='MARKET_RAW')]
        pos=bool((yy.SumR>0).all()) and len(yy)>=5
        detail[f'{cost}_all_hist_years_positive']=pos; ok &= pos
    return {'candidate':'MARKET_RAW','promote':bool(ok),'detail':detail}

def main():
    m1=lab72.load_m1()
    ft,fz=lab43.load_flow(); hist_raw=lab43.load_hist(); sec_raw=lab43.load_sec()
    frames={
      'historical':lab43.prep(hist_raw,ft,fz,int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-01-01',tz='UTC').timestamp())),
      'forward_2026':lab43.prep(sec_raw,ft,fz,int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()))
    }
    summary=[]; years=[]; alltr=[]; skiprows=[]
    for label,p in frames.items():
        for cost_name,cost in COSTS.items():
            for mode in MODES:
                d,sk=stateful(p,m1,mode,cost)
                d['period']=label; d['cost_model']=cost_name; d['mode']=mode
                alltr.append(d); summary.append(summarize(label,cost_name,mode,d))
                years.extend(yearly(label,cost_name,mode,d))
                skiprows.append({'period':label,'cost_model':cost_name,'mode':mode,**sk})
    s=pd.DataFrame(summary); y=pd.DataFrame(years); tr=pd.concat(alltr,ignore_index=True); sk=pd.DataFrame(skiprows)
    promo=promotion(s,y)
    s.to_csv(OUT/'summary.csv',index=False); y.to_csv(OUT/'yearly.csv',index=False); tr.to_csv(OUT/'trades.csv',index=False); sk.to_csv(OUT/'skips.csv',index=False)
    (OUT/'promotion.json').write_text(json.dumps(promo,indent=2))
    (OUT/'REPORT.md').write_text('\n'.join([
      '# LAB073 — MARKET vs CONFIRM CAUSAL STATEFUL','',
      '## Summary','',s.to_markdown(index=False),'',
      '## Promotion','',json.dumps(promo,indent=2),'',
      '## Historical yearly','',y.to_markdown(index=False),'',
      '## Skips','',sk.to_markdown(index=False)
    ]))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__':main()
