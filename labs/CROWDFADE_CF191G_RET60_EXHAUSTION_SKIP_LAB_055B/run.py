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
EXPECT={'historical':(5297,700.3704107793633),'forward_2026':(544,35.49784078156513)}

def stats(R,ST,period):
    m=lab43.metrics(np.asarray(R,float))
    t=pd.to_datetime(ST,unit='s',utc=True)
    keys=t.year.astype(str).to_numpy() if period=='historical' else t.to_period('M').astype(str).to_numpy()
    d={str(k):lab43.metrics(np.asarray(R)[keys==k].astype(float)) for k in sorted(set(keys))}
    return m,d,sum(1 for v in d.values() if v.get('SumR',0)>0),len(d)

def period_pass(base,new,bpos,npos):
    return bool(new['EV']>base['EV'] and new['PF']>base['PF'] and new['MaxDD_R']<=base['MaxDD_R'] and new['R_DD']>base['R_DD'] and npos>=bpos)

def sim_gate(p,gate):
    ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5=p
    cap=len(dt5); R=np.zeros(cap); ST=np.zeros(cap,np.int64); SIDE=np.zeros(cap,np.int8)
    n=0;k=0;day=-1;dc=0;nextts=0;last=0.;la=0.;has=False;skips=0
    conf=False;cs=0;cp=0.;ca=0.;ct=0;cb=0;mf=0.;ma=0.
    while k<len(dt5)-3:
        t=dt5[k]; z=Z5[k]
        if t<nextts: k+=1; continue
        d=t//86400
        if d!=day: day=d; dc=0
        if dc>=lab53.MAXDAY: conf=False; k+=1; continue
        if conf:
            side=cs
            fav=((cp-L5[k]) if side<0 else (H5[k]-cp))/ca
            adv=((H5[k]-cp) if side<0 else (cp-L5[k]))/ca
            if fav<0:fav=0.
            if adv<0:adv=0.
            mf=max(mf,fav); ma=max(ma,adv); cb-=1; age=t-ct
            if cb<=0 or age>2700: conf=False; k+=1; continue
            if ma>lab53.G_MAX_ADV: conf=False; k+=1; continue
            target=cp+side*lab53.CONF_ATR*ca
            confirmed=(C5[k]>=target) if side>0 else (C5[k]<=target)
            if not confirmed: k+=1; continue
            same=(z<0.0) if side>0 else (z>0.0)
            if not same: conf=False; k+=1; continue
            if abs(z)<lab53.G_MIN_ABS_Z: conf=False; k+=1; continue
            response=mf/(ma+1e-9)
            if response<lab53.G_MIN_RESPONSE: conf=False; k+=1; continue
            conf=False
            if gate:
                ret60=np.nan
                if k>=12 and np.isfinite(A5[k]) and A5[k]>0:
                    ret60=side*(C5[k]-C5[k-12])/A5[k]
                if np.isfinite(ret60) and ret60>1.0:
                    skips+=1; k+=1; continue
            if has and abs(C5[k]-last)<lab53.PAUSE_ATR*la: k+=1; continue
            entry=C5[k]
            rr,ex,reason=lab53.manage_cf191g(dt5,H5,L5,C5,k,side,entry,ca)
            R[n]=rr; ST[n]=ct; SIDE[n]=side; n+=1
            dc+=1; last=entry; la=ca; has=True; nextts=dt5[ex]+1; k+=1; continue
        side=-1 if z>=lab53.ZTH else (1 if z<=-lab53.ZTH else 0)
        if side==0: k+=1; continue
        if has and abs(C5[k]-last)<lab53.PAUSE_ATR*la: k+=1; continue
        conf=True; cs=side; cp=C5[k]; ca=A5[k]; ct=t; cb=9; mf=0.; ma=0.; k+=1
    return R[:n],ST[:n],SIDE[:n],skips

def main():
    ft,fz=lab43.load_flow(); hist=lab43.load_hist(); sec=lab43.load_sec()
    periods={
      'historical':lab43.prep(hist,ft,fz,int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-01-01',tz='UTC').timestamp())),
      'forward_2026':lab43.prep(sec,ft,fz,int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()))}
    rows=[];detail={};overall=True
    for period,p in periods.items():
        bR,bST,bSIDE,bskip=sim_gate(p,False); nR,nST,nSIDE,nskip=sim_gate(p,True)
        en,es=EXPECT[period]
        if len(bR)!=en or abs(float(bR.sum())-es)>1e-6: raise RuntimeError(f'control parity fail {period}')
        bm,bper,bpos,btot=stats(bR,bST,period); nm,nper,npos,ntot=stats(nR,nST,period)
        passed=period_pass(bm,nm,bpos,npos); overall=overall and passed
        rows += [dict(period=period,variant='CONTROL',**bm,positive_periods=bpos,periods_total=btot,skips=0),
                 dict(period=period,variant='SKIP_RET60_GT_1ATR',**nm,positive_periods=npos,periods_total=ntot,skips=nskip)]
        detail[period]={'control':bm,'new':nm,'skip_count':int(nskip),'control_periods':bper,'new_periods':nper,'PASS':passed}
    pd.DataFrame(rows).to_csv(OUT/'comparison.csv',index=False)
    result={'lab':'CROWDFADE_CF191G_RET60_EXHAUSTION_SKIP_LAB_055B','threshold_ret60_atr':1.0,'detail':detail,'PASS_BOTH':overall,
      'limitations':['BTCUSDT only','2026 Mar-Aug reused shadow/stress','0.5bps proxy via frozen management','full stateful replay']}
    (OUT/'summary.json').write_text(json.dumps(result,indent=2,default=float))
    lines=['# LAB055B — RET60 > +1.0 ATR SKIP','',pd.DataFrame(rows).to_markdown(index=False),'',json.dumps(result,indent=2,default=float)]
    (OUT/'REPORT.md').write_text('\n'.join(lines)); print((OUT/'REPORT.md').read_text())

if __name__=='__main__': main()