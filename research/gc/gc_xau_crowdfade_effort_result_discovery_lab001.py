#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd

ROOT=Path('research/gc')
BASE=ROOT/'gc_m1_orderflow_edge_discovery_003.py'
LT=ROOT/'gc_buyer_breakout_long_to_ftmo_xau_transfer_lab_006.py'
OUT_JSON=ROOT/'GC_XAU_CROWDFade_EFFORT_RESULT_DISCOVERY_LAB001.json'
OUT_MD=ROOT/'GC_XAU_CROWDFade_EFFORT_RESULT_DISCOVERY_LAB001.md'
OUT_EVENTS=ROOT/'GC_XAU_CROWDFade_EFFORT_RESULT_DISCOVERY_LAB001_EVENTS.csv'
TRAIN_END=pd.Timestamp('2026-08-20T00:00:00Z')
VALID_END=pd.Timestamp('2026-09-06T22:00:00Z')
CLOCK_OFFSET_MIN=180
HORIZONS=(1,3,5,10,15,30)
STALE_MS=5000
CANDIDATES=('FADE_OPPOSITE_BODY','FADE_Q20','FADE_LOC_Q20','FADE_REJECTION','CHASE_Q80','CHASE_BREAKOUT')

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(spec)
    assert spec and spec.loader; spec.loader.exec_module(m); return m

def candidate(b,name):
    A=b.aggr.ne(''); sell=b.aggr.eq('SELL'); buy=b.aggr.eq('BUY')
    fade=np.where(sell,1,np.where(buy,-1,0)); chase=-fade
    loc=np.where(sell,b.sell_loc,np.where(buy,b.buy_loc,np.nan))
    qloc=np.where(sell,b.q75_sellloc,np.where(buy,b.q75_buyloc,np.nan))
    reject=(sell&(b.close_pos>=.75))|(buy&(b.close_pos<=.25))
    sweep=(sell&(b.low<=b.prior20_low))|(buy&(b.high>=b.prior20_high))
    breakout=(sell&(b.close_pos<=.25))|(buy&(b.close_pos>=.75))
    if name=='FADE_OPPOSITE_BODY': m=A&(b.impact<=0); d=fade
    elif name=='FADE_Q20': m=A&b.impact_q20.notna()&(b.impact<=b.impact_q20); d=fade
    elif name=='FADE_LOC_Q20': m=A&(loc>=qloc)&b.impact_q20.notna()&(b.impact<=b.impact_q20); d=fade
    elif name=='FADE_REJECTION': m=A&reject; d=fade
    elif name=='CHASE_Q80': m=A&b.impact_q80.notna()&(b.impact>=b.impact_q80); d=chase
    elif name=='CHASE_BREAKOUT': m=A&sweep&breakout&(b.impact>0); d=chase
    else: raise ValueError(name)
    return m,np.asarray(d,int)

def first_idx(times,target):
    i=int(np.searchsorted(times,target,side='left'))
    if i>=len(times): return None,None
    lag=int(times[i]-target)
    return (None,lag) if lag<0 or lag>STALE_MS else (i,lag)

def quote_at(times,bids,asks,target):
    i,lag=first_idx(times,target)
    if i is None: return None
    return i,float(bids[i]),float(asks[i]),lag

def period(t):
    t=pd.Timestamp(t)
    if t<TRAIN_END: return 'TRAIN'
    if t<VALID_END: return 'VALID'
    return 'POST_CHECK'

def metric(z,h):
    c=f'ret_{h}m_atr'; x=z[c].dropna().to_numpy(float)
    return {'n':int(len(x)),'ev':float(x.mean()) if len(x) else None,'median':float(np.median(x)) if len(x) else None,'wr':float((x>0).mean()*100) if len(x) else None}

def summarize(ev):
    out={}
    for p in ('TRAIN','VALID','POST_CHECK','FULL'):
        d=ev if p=='FULL' else ev[ev.period.eq(p)]
        out[p]={'all':{str(h):metric(d,h) for h in HORIZONS}}
        q=d[d.pre_move_atr<=0]
        out[p]['strict_lead']={str(h):metric(q,h) for h in HORIZONS}
        q=d[d.pre_move_atr<=.25]
        out[p]['loose_lead']={str(h):metric(q,h) for h in HORIZONS}
        v=d.pre_move_atr.dropna().to_numpy(float)
        out[p]['pre_move']={'n':int(len(v)),'mean':float(v.mean()) if len(v) else None,'median':float(np.median(v)) if len(v) else None,'strict_share':float((v<=0).mean()) if len(v) else None,'loose_share':float((v<=.25).mean()) if len(v) else None}
    return out

def gate(s):
    tr=s['TRAIN']['all']; va=s['VALID']['all']; sl=s['VALID']['strict_lead']; pm=s['VALID']['pre_move']
    checks={'train_n_ge12':tr['15']['n']>=12,'valid_n_ge12':va['15']['n']>=12,'train_5_pos':tr['5']['ev'] is not None and tr['5']['ev']>0,'valid_5_pos':va['5']['ev'] is not None and va['5']['ev']>0,'train_15_pos':tr['15']['ev'] is not None and tr['15']['ev']>0,'valid_15_pos':va['15']['ev'] is not None and va['15']['ev']>0,'valid_strict_n_ge5':sl['15']['n']>=5,'valid_strict_5_pos':sl['5']['ev'] is not None and sl['5']['ev']>0,'valid_strict_15_pos':sl['15']['ev'] is not None and sl['15']['ev']>0,'valid_median_premove_le025':pm['median'] is not None and pm['median']<=.25}
    checks['pass']=all(checks.values()); return checks

def main():
    base=load(BASE,'base'); lt=load(LT,'lt')
    work=ROOT/'_crowdfade001'; work.mkdir(parents=True,exist_ok=True)
    az=work/'amp.zip'
    if not az.exists(): base.download(base.AMP_URL,az)
    if base.sha(az)!=base.AMP_SHA: raise SystemExit('AMP SHA mismatch')
    b=base.load_amp(az)
    times,bids,asks,file_stats=lt.read_xau_ticks()
    xm1=lt.build_xau_m1(times,bids,asks); atr_map=lt.xau_atr_lookup(xm1)
    minute=(times//60000)*60000; mid=(bids+asks)/2.0
    first_mid={}
    for i,m in enumerate(minute):
        m=int(m)
        if m not in first_mid: first_mid[m]=float(mid[i])
    rows=[]
    for name in CANDIDATES:
        mask,dirs=candidate(b,name)
        for i in np.flatnonzero(mask.to_numpy()):
            if i+1>=len(b) or b.iloc[i+1].time != b.iloc[i].time + pd.Timedelta(minutes=1): continue
            sig=pd.Timestamp(b.iloc[i].time); direction=int(dirs[i])
            action_utc=sig+pd.Timedelta(minutes=1)
            action_ms=int(action_utc.value//1_000_000)+CLOCK_OFFSET_MIN*60000
            q=quote_at(times,bids,asks,action_ms)
            if q is None: continue
            qi,ebid,eask,lag=q
            atr=float(atr_map.get(action_ms-60000,np.nan))
            if not np.isfinite(atr) or atr<=0: continue
            entry=eask if direction>0 else ebid
            sig_broker_min=int(sig.value//1_000_000)+CLOCK_OFFSET_MIN*60000
            pm0=first_mid.get(sig_broker_min,np.nan); action_mid=(ebid+eask)/2.0
            pre=np.nan if not np.isfinite(pm0) else direction*(action_mid-pm0)/atr
            r={'candidate':name,'period':period(sig),'signal_time':sig.isoformat(),'action_time_utc':action_utc.isoformat(),'direction':direction,'side':'LONG' if direction>0 else 'SHORT','xau_atr14':atr,'entry_bid':ebid,'entry_ask':eask,'entry_lag_ms':lag,'pre_move_atr':pre,'gc_delta_frac':float(b.iloc[i].delta_frac),'gc_impact':float(b.iloc[i].impact),'gc_body_atr':float(b.iloc[i].body_atr),'gc_close_pos':float(b.iloc[i].close_pos),'gc_buy_loc':float(b.iloc[i].buy_loc),'gc_sell_loc':float(b.iloc[i].sell_loc)}
            for h in HORIZONS:
                qq=quote_at(times,bids,asks,action_ms+h*60000)
                if qq is None: r[f'ret_{h}m_atr']=np.nan; r[f'ret_{h}m_bps']=np.nan; continue
                _,xbid,xask,_=qq; exitpx=xbid if direction>0 else xask
                pnl=direction*(exitpx-entry)
                r[f'ret_{h}m_atr']=pnl/atr; r[f'ret_{h}m_bps']=pnl/entry*10000.0
            rows.append(r)
    ev=pd.DataFrame(rows); ev.to_csv(OUT_EVENTS,index=False)
    result={}
    for name in CANDIDATES:
        d=ev[ev.candidate.eq(name)].copy(); s=summarize(d); result[name]={'summary':s,'gate':gate(s)}
    passing=[n for n in CANDIDATES if result[n]['gate']['pass']]
    winner=None
    if passing:
        def score(n):
            s=result[n]['summary']; vals=[s['TRAIN']['all']['5']['ev'],s['VALID']['all']['5']['ev'],s['TRAIN']['all']['15']['ev'],s['VALID']['all']['15']['ev'],s['VALID']['strict_lead']['5']['ev'],s['VALID']['strict_lead']['15']['ev']]
            return min(vals)
        winner=max(passing,key=score)
    out={'lab':'GC_XAU_CROWDFade_EFFORT_RESULT_DISCOVERY_LAB001','status':'HISTORICAL_BOUNDED_DISCOVERY_NOT_OOS','clock_offset_min':CLOCK_OFFSET_MIN,'candidate_set':list(CANDIDATES),'passing':passing,'winner':winner,'results':result,'xau_file_stats':file_stats}
    OUT_JSON.write_text(json.dumps(out,indent=2,default=str),encoding='utf-8')
    def f(x): return 'NA' if x is None else f'{x:+.3f}'
    lines=['# GC_XAU_CROWDFade_EFFORT_RESULT_DISCOVERY_LAB001','','Status: HISTORICAL_BOUNDED_DISCOVERY_NOT_OOS','','Question: can GC futures order flow signal XAU before the CFD has already expressed the predicted move?','','| Candidate | Gate | Train N | Train EV5 | Valid N | Valid EV5 | Valid EV15 | StrictLead N | Strict EV5 | Strict EV15 | Valid median pre-move | Post EV15 |','|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for n in CANDIDATES:
        s=result[n]['summary']; g=result[n]['gate']
        lines.append(f"| {n} | {'PASS' if g['pass'] else 'FAIL'} | {s['TRAIN']['all']['15']['n']} | {f(s['TRAIN']['all']['5']['ev'])} | {s['VALID']['all']['15']['n']} | {f(s['VALID']['all']['5']['ev'])} | {f(s['VALID']['all']['15']['ev'])} | {s['VALID']['strict_lead']['15']['n']} | {f(s['VALID']['strict_lead']['5']['ev'])} | {f(s['VALID']['strict_lead']['15']['ev'])} | {f(s['VALID']['pre_move']['median'])} | {f(s['POST_CHECK']['all']['15']['ev'])} |")
    lines += ['',f'Passing: {passing if passing else "NONE"}',f'Nominated: {winner or "NONE"}','','STRICT_LEAD means XAU had not yet moved in the predicted direction when the completed GC M1 signal became actionable.','LOOSE_LEAD allows up to +0.25 XAU ATR already expressed. Spread is embedded. POST_CHECK was not used for nomination.','This is discovery, not OOS certification or EA authorization.']
    OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8'); print(OUT_MD.read_text())
if __name__=='__main__': main()
