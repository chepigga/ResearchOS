from pathlib import Path
import json, zipfile, importlib.util
import numpy as np
import pandas as pd
from numba import njit

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'
OUT=ROOT/'output'
OUT.mkdir(parents=True,exist_ok=True)

# Reuse validated v200 parsing/metrics.
_core_path=Path(__file__).resolve().parents[1]/'CROWDFADE_V200_SEQUENTIAL_CHANGE_LABS_033_035'/'run.py'
_spec=importlib.util.spec_from_file_location('crowdfade_core_033_035',_core_path)
core=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(core)

# ---------------- Frozen CORE ----------------
CORE_Z=2.05
CORE_CONFIRM=.25
CORE_CONFIRM_TTL=3600
CORE_RETRACE=.60
CORE_PENDING_TTL=1200
CORE_SL=4.5
CORE_TP=10.0
CORE_HOLD=86400

# ---------------- FAST population parity with LAB039/LAB040 ----------------
FAST_Z_LO=1.00
FAST_Z_HI=2.05
FAST_CONFIRM=.30
FAST_CONFIRM_TTL=10800
FAST_PAUSE_ATR=1.00
MAXDAY=3
FAST_SL=4.5
FAST_TP=10.0
FAST_HOLD=86400
COST_BPS=.50

# Gate IDs:
# 1 = G1 RESPONSE
#     ONE_ALIGN and response in [0.50,1.00) OR response>=2.50
# 2 = G2 RESPONSE+RECLAIM
#     G1 OR (BOTH_ALIGN and reclaim in [0.35,0.50))
# 3 = G3 FULL COMPOSITE
#     G2 OR (MIXED_NEUTRAL and confirm<=15m)

def load_flow():
    zp=DATA/'BTCUSDT_flow_2021-01-2026-08.csv.zip'
    with zipfile.ZipFile(zp) as z:
        n=[x for x in z.namelist() if x.lower().endswith('.csv')][0]
        with z.open(n) as f:r=pd.read_csv(f,usecols=['create_time','sum_open_interest','count_long_short_ratio'])
    r=r[pd.to_numeric(r.sum_open_interest,errors='coerce')>0].copy()
    r['t']=pd.to_datetime(r.create_time,utc=True,errors='coerce')
    r['ratio']=pd.to_numeric(r.count_long_short_ratio,errors='coerce')
    r=r.dropna(subset=['t','ratio']).sort_values('t').drop_duplicates('t')
    mu=r.ratio.rolling(72,min_periods=72).mean()
    sd=r.ratio.rolling(72,min_periods=72).std(ddof=0)
    r['z']=(r.ratio-mu)/sd.replace(0,np.nan)
    ft=r.t.dt.tz_convert(None).to_numpy(dtype='datetime64[s]').astype(np.int64)
    return ft,r.z.to_numpy(float)

def read_zip(path):
    with zipfile.ZipFile(path) as z:
        n=[x for x in z.namelist() if x.lower().endswith('.csv')][0]
        with z.open(n) as f:r=pd.read_csv(f,header=None,usecols=[0,1,2,3,4])
    ts=pd.to_numeric(r.iloc[:,0],errors='coerce')
    med=np.nanmedian(ts.to_numpy(float))
    if med>1e15:ts=(ts//1_000_000).astype('Int64')
    elif med>1e12:ts=(ts//1000).astype('Int64')
    else:ts=ts.astype('Int64')
    q=pd.DataFrame({'ts':ts,'o':pd.to_numeric(r.iloc[:,1],errors='coerce'),
                    'h':pd.to_numeric(r.iloc[:,2],errors='coerce'),
                    'l':pd.to_numeric(r.iloc[:,3],errors='coerce'),
                    'c':pd.to_numeric(r.iloc[:,4],errors='coerce')})
    return q.dropna()

def load_hist():
    parts=[read_zip(zp) for zp in sorted((DATA/'hist_1m').glob('BTCUSDT-1m-*.zip'))]
    p=pd.concat(parts,ignore_index=True).drop_duplicates('ts').sort_values('ts')
    return tuple(p[x].to_numpy(np.int64 if x=='ts' else np.float64) for x in ['ts','o','h','l','c'])

def load_sec():
    with zipfile.ZipFile(DATA/'BTCUSDT_sec.csv.zip') as z:
        n=[x for x in z.namelist() if x.lower().endswith('.csv')][0]
        with z.open(n) as f:s=pd.read_csv(f,usecols=['ts','o','h','l','c'])
    s=s.sort_values('ts').drop_duplicates('ts')
    return tuple(s[x].to_numpy(np.int64 if x=='ts' else np.float64) for x in ['ts','o','h','l','c'])

def tf_states(ts,C,sec):
    b=(ts//sec)*sec
    st=np.r_[0,np.flatnonzero(b[1:]!=b[:-1])+1]
    en=np.r_[st[1:],len(ts)]
    close=C[en-1];bt=b[st]
    ema=pd.Series(close).ewm(span=50,adjust=False).mean().to_numpy()
    lag4=pd.Series(ema).shift(4).to_numpy()
    state=np.where((close>ema)&(ema>lag4),1,np.where((close<ema)&(ema<lag4),-1,0)).astype(np.int64)
    return (bt+sec).astype(np.int64),state

def prep_fast(raw,ft,fz,start,end):
    ts,O,H,L,C=raw
    order=np.argsort(ts);ts=ts[order];O=O[order];H=H[order];L=L[order];C=C[order]
    keep=np.r_[True,ts[1:]!=ts[:-1]]
    ts=ts[keep];O=O[keep];H=H[keep];L=L[keep];C=C[keep]

    b15=(ts//900)*900
    st15=np.r_[0,np.flatnonzero(b15[1:]!=b15[:-1])+1]
    en15=np.r_[st15[1:],len(ts)]
    bt15=b15[st15];bh15=np.maximum.reduceat(H,st15);bl15=np.minimum.reduceat(L,st15);bc15=C[en15-1]
    pc=np.r_[bc15[0],bc15[:-1]]
    tr=np.maximum(bh15-bl15,np.maximum(np.abs(bh15-pc),np.abs(bl15-pc)))
    atr15=pd.Series(tr).rolling(14,min_periods=14).mean().to_numpy()
    av15=bt15+900

    b5=(ts//300)*300
    st5=np.r_[0,np.flatnonzero(b5[1:]!=b5[:-1])+1]
    en5=np.r_[st5[1:],len(ts)]
    bt5=b5[st5];c5=C[en5-1];av5=bt5+300

    h1t,h1s=tf_states(ts,C,3600)
    h4t,h4s=tf_states(ts,C,14400)

    fi=np.searchsorted(ft,av5,'left')-1
    ai=np.searchsorted(av15,av5,'right')-1
    h1i=np.searchsorted(h1t,av5,'right')-1
    h4i=np.searchsorted(h4t,av5,'right')-1
    fi0=np.maximum(fi,0);ai0=np.maximum(ai,0);h1i0=np.maximum(h1i,0);h4i0=np.maximum(h4i,0)
    good=(av5>=start)&(av5<end)&(fi>=0)&(ai>=0)&(h1i>=0)&(h4i>=0)&np.isfinite(fz[fi0])&np.isfinite(atr15[ai0])
    good &= ((av5-ft[fi0])>=0)&((av5-ft[fi0])<=600)
    return (ts,O,H,L,C,av5[good],c5[good],fz[fi[good]],atr15[ai[good]],h1s[h1i[good]],h4s[h4i[good]])

@njit(cache=True)
def core_events(ts,O,H,L,C,dt,QH,QL,QC,Z,A,H1,H4):
    cap=len(dt)
    R=np.zeros(cap);ST=np.zeros(cap,np.int64);ET=np.zeros(cap,np.int64);XT=np.zeros(cap,np.int64);SIDE=np.zeros(cap,np.int8)
    n=0;k=0;last=0.;la=0.;has=False;day=-1;dc=0;nextts=0
    while k<len(dt)-3:
        t=dt[k]
        if t<nextts:k+=1;continue
        d=t//86400
        if d!=day:day=d;dc=0
        if dc>=MAXDAY:k+=1;continue
        z=Z[k]
        side=-1 if z>=CORE_Z else (1 if z<=-CORE_Z else 0)
        if side==0:k+=1;continue
        sig=QC[k];siga=A[k]
        if has and abs(sig-last)<1.0*la:k+=1;continue
        lev=sig+side*CORE_CONFIRM*siga
        ci=-1;j=k+1
        while j<len(dt) and dt[j]<=t+CORE_CONFIRM_TTL:
            if (side>0 and QC[j]>=lev) or (side<0 and QC[j]<=lev):ci=j;break
            j+=1
        if ci<0:k+=1;continue
        if z*Z[ci]<0.0:k=ci+1;continue
        entry=QC[ci]-side*CORE_RETRACE*siga
        ps=np.searchsorted(ts,dt[ci]+1);pe=np.searchsorted(ts,dt[ci]+CORE_PENDING_TTL,'right')
        ei=-1
        for q in range(ps,min(len(ts),pe)):
            if (side>0 and L[q]<=entry) or (side<0 and H[q]>=entry):ei=q;break
        if ei<0:k=ci+1;continue
        risk=CORE_SL*siga;sl=entry-side*risk;tp=entry+side*CORE_TP*siga
        xe=min(len(ts)-1,np.searchsorted(ts,ts[ei]+CORE_HOLD,'left'))
        xp=C[xe];ex=xe
        for q in range(ei+1,xe+1):
            sh=(side>0 and L[q]<=sl) or (side<0 and H[q]>=sl)
            th=(side>0 and H[q]>=tp) or (side<0 and L[q]<=tp)
            if sh:xp=sl;ex=q;break
            if th:xp=tp;ex=q;break
        rr=side*(xp-entry)/risk-(COST_BPS/10000.)*entry/risk
        R[n]=rr;ST[n]=t;ET[n]=ts[ei];XT[n]=ts[ex];SIDE[n]=side;n+=1
        dc+=1;last=entry;la=siga;has=True;nextts=ts[ex]+1;k=np.searchsorted(dt,nextts)
    return R[:n],ST[:n],ET[:n],XT[:n],SIDE[:n]

@njit(cache=True)
def gate_ok(gate_id,trend_state,response,reclaim,confirm_min):
    g1 = (trend_state==1) and (((response>=0.50) and (response<1.00)) or (response>=2.50))
    g2_extra = (trend_state==2) and (reclaim>=0.35) and (reclaim<0.50)
    g3_extra = (trend_state==3) and (confirm_min<=15.0)
    if gate_id==1:return g1
    if gate_id==2:return g1 or g2_extra
    return g1 or g2_extra or g3_extra

@njit(cache=True)
def fast_events(ts,O,H,L,C,dt5,C5,Z5,A5,H1,H4,gate_id):
    cap=len(dt5)
    R=np.zeros(cap);ST=np.zeros(cap,np.int64);ET=np.zeros(cap,np.int64);XT=np.zeros(cap,np.int64)
    SIDE=np.zeros(cap,np.int8);GT=np.zeros(cap,np.int8)
    n=0;k=0;last=0.;la=0.;has=False;day=-1;dc=0;nextts=0

    while k<len(dt5)-3:
        t=dt5[k]
        if t<nextts:k+=1;continue
        d=t//86400
        if d!=day:day=d;dc=0
        if dc>=MAXDAY:k+=1;continue

        z=Z5[k];az=abs(z)
        if az<FAST_Z_LO or az>=FAST_Z_HI:k+=1;continue
        side=-1 if z>0 else 1
        sig=C5[k];siga=A5[k]
        if has and abs(sig-last)<FAST_PAUSE_ATR*la:k+=1;continue

        target=sig+side*FAST_CONFIRM*siga
        ps=np.searchsorted(ts,t+1);pe=np.searchsorted(ts,t+FAST_CONFIRM_TTL,'right')
        ci=-1;maxcrowd=0.;maxthesis=0.
        for q in range(ps,min(len(ts),pe)):
            crowd_exc=((H[q]-sig) if side<0 else (sig-L[q]))/siga
            thesis_exc=((sig-L[q]) if side<0 else (H[q]-sig))/siga
            if crowd_exc>maxcrowd:maxcrowd=crowd_exc
            if thesis_exc>maxthesis:maxthesis=thesis_exc
            if (side>0 and C[q]>=target) or (side<0 and C[q]<=target):
                ci=q;break
        if ci<0:k+=1;continue

        zk=np.searchsorted(dt5,ts[ci],'right')-1
        if zk<0:k+=1;continue
        if z*Z5[zk]<0.0:
            k=np.searchsorted(dt5,ts[ci])+1;continue

        entry=C[ci]
        confirm_min=(ts[ci]-t)/60.0
        response=maxthesis/(maxcrowd+1e-9)
        reclaim=side*(entry-sig)/siga

        # Trend state relative to trade side:
        # 1 ONE_ALIGN, 2 BOTH_ALIGN, 3 MIXED_NEUTRAL, 4 BOTH_OPPOSE.
        align1=(H1[k]==side)
        align4=(H4[k]==side)
        oppose1=(H1[k]==-side)
        oppose4=(H4[k]==-side)
        trend_state=3
        if align1 and align4:trend_state=2
        elif oppose1 and oppose4:trend_state=4
        elif align1!=align4:trend_state=1
        else:trend_state=3

        if not gate_ok(gate_id,trend_state,response,reclaim,confirm_min):
            # IMPORTANT: rejected candidate does NOT consume pause/occupancy/day quota.
            # Search continues from first M5 state after confirmation; causal information is known then.
            k=np.searchsorted(dt5,ts[ci])+1
            continue

        ei=ci
        risk=FAST_SL*siga;sl=entry-side*risk;tp=entry+side*FAST_TP*siga
        xe=min(len(ts)-1,np.searchsorted(ts,ts[ei]+FAST_HOLD,'left'))
        xp=C[xe];ex=xe
        for q in range(ei+1,xe+1):
            sh=(side>0 and L[q]<=sl) or (side<0 and H[q]>=sl)
            th=(side>0 and H[q]>=tp) or (side<0 and L[q]<=tp)
            if sh:xp=sl;ex=q;break
            if th:xp=tp;ex=q;break
        rr=side*(xp-entry)/risk-(COST_BPS/10000.)*entry/risk
        R[n]=rr;ST[n]=t;ET[n]=ts[ei];XT[n]=ts[ex];SIDE[n]=side;GT[n]=gate_id;n+=1
        dc+=1;last=entry;la=siga;has=True;nextts=ts[ex]+1;k=np.searchsorted(dt5,nextts)

    return R[:n],ST[:n],ET[:n],XT[:n],SIDE[:n],GT[:n]

def df_core(z):
    R,st,et,xt,side=z
    return pd.DataFrame({'R':R,'signal_ts':st,'entry_ts':et,'exit_ts':xt,'side':side,'lane':'CORE'})

def df_fast(z,gate_name):
    R,st,et,xt,side,gt=z
    return pd.DataFrame({'R':R,'signal_ts':st,'entry_ts':et,'exit_ts':xt,'side':side,'lane':gate_name})

def met(x):
    return core.metrics(np.asarray(x,float))

def lane_metrics(df,months):
    m=met(df.R.to_numpy(float));m['trades_per_month']=len(df)/months;return m

def portfolio(core_df,fast_df,fast_mult,months):
    a=core_df[['R','signal_ts','entry_ts','exit_ts','lane']].copy();a['w']=1.0
    b=fast_df[['R','signal_ts','entry_ts','exit_ts','lane']].copy();b['w']=fast_mult
    p=pd.concat([a,b],ignore_index=True)
    p['weighted_R']=p.R*p.w
    p['lane_order']=np.where(p.lane.eq('CORE'),0,1)
    p=p.sort_values(['exit_ts','lane_order','signal_ts']).reset_index(drop=True)
    m=met(p.weighted_R.to_numpy(float))
    m['trades']=len(p);m['trades_per_month']=len(p)/months
    m['core_trades']=len(a);m['fast_trades']=len(b)
    m['fast_mult']=fast_mult
    m['weighted_sumR']=float(p.weighted_R.sum())

    ev=[]
    for _,r in p.iterrows():
        ev.append((int(r.entry_ts),1,float(r.w)))
        ev.append((int(r.exit_ts),-1,float(r.w)))
    ev.sort(key=lambda x:(x[0],x[1]))
    cur=0.;mx=0.
    for _,typ,w in ev:
        cur += w if typ==1 else -w
        if cur>mx:mx=cur
    m['max_concurrent_risk_units']=float(mx)
    return m,p

def period_metrics(df,period):
    if not len(df):return {}
    t=pd.to_datetime(df.signal_ts,unit='s',utc=True)
    grp=df.groupby(t.dt.year if period=='hist' else t.dt.strftime('%Y-%m'))
    return {str(k):met(g.R.to_numpy(float)) for k,g in grp}

def run_period(raw,ft,fz,start,end,months,label):
    m15=core.prep(raw,ft,fz,start,end)
    m5=prep_fast(raw,ft,fz,start,end)
    cdf=df_core(core_events(*m15))
    out={'CORE':lane_metrics(cdf,months),'gates':{},'portfolios':{}}
    out['CORE']['periods']=period_metrics(cdf,'hist' if label=='historical' else 'fwd')
    for gid,gname in [(1,'G1_RESPONSE'),(2,'G2_RESPONSE_RECLAIM'),(3,'G3_FULL_COMPOSITE')]:
        fdf=df_fast(fast_events(*m5,gid),gname)
        gm=lane_metrics(fdf,months);gm['periods']=period_metrics(fdf,'hist' if label=='historical' else 'fwd')
        out['gates'][gname]=gm
        fdf.to_csv(OUT/f'{label}_{gname}.csv',index=False)
        for mult in [0.25,0.40]:
            k=f'{gname}_RISK{mult:.2f}'
            pm,pdf=portfolio(cdf,fdf,mult,months)
            out['portfolios'][k]=pm
            pdf.to_csv(OUT/f'{label}_{k}_portfolio.csv',index=False)
    cdf.to_csv(OUT/f'{label}_CORE.csv',index=False)
    return out

def fmt(m):
    n=m.get('N',m.get('trades',0))
    return f"N={n} ({m.get('trades_per_month',0):.1f}/mo) EV={m['EV']:+.4f} PF={m['PF']:.3f} Sum={m['SumR']:+.2f}R DD={m['MaxDD_R']:.2f} R/DD={m['R_DD']:.3f}"

def main():
    ft,fz=load_flow()
    hraw=load_hist();fraw=load_sec()
    hist=run_period(hraw,ft,fz,int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-01-01',tz='UTC').timestamp()),60,'historical')
    fwd=run_period(fraw,ft,fz,int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()),6,'forward')

    # Promotion gate: must add trades; 2026 SumR and R/DD >= CORE; historical EV/PF positive;
    # max concurrent risk <= 1.8 core units.
    promotions={}
    coref=fwd['CORE'];coreh=hist['CORE']
    for k,hm in hist['portfolios'].items():
        fm=fwd['portfolios'][k]
        gname=k.rsplit('_RISK',1)[0]
        fast_h=hist['gates'][gname]
        promotions[k]={
          'adds_trades':bool(fm['trades']>coref['N'] and hm['trades']>coreh['N']),
          'forward_sum_not_worse':bool(fm['SumR']>=coref['SumR']),
          'forward_rdd_not_worse':bool(fm['R_DD']>=coref['R_DD']),
          'hist_portfolio_ev_positive':bool(hm['EV']>0 and hm['PF']>1),
          'fast_lane_hist_positive':bool(fast_h['EV']>0 and fast_h['PF']>1),
          'max_risk_ok':bool(max(hm['max_concurrent_risk_units'],fm['max_concurrent_risk_units'])<=1.8)
        }
        promotions[k]['pass']=bool(all(promotions[k].values()))

    result={
      'lab':'LAB041_FAST_LANE_COMPOSITE_GATE_AND_PORTFOLIO_REPLAY',
      'preregistered_gates':{
        'G1_RESPONSE':'ONE_ALIGN AND (response 0.50-1.00 OR response>=2.50)',
        'G2_RESPONSE_RECLAIM':'G1 OR (BOTH_ALIGN AND reclaim 0.35-0.50 ATR)',
        'G3_FULL_COMPOSITE':'G2 OR (MIXED_NEUTRAL AND confirm<=15m)'
      },
      'risk_tests':[0.25,0.40],
      'historical':hist,'forward':fwd,'promotion_gate':promotions,
      'promotion_rule':'adds trades; 2026 SumR >= CORE; 2026 R/DD >= CORE; historical combined EV>0/PF>1; FAST historical EV>0/PF>1; max concurrent risk <=1.8 units',
      'limitations':[
        'BTC only; ETH/SOL transfer still required.',
        '2026 Mar-Aug is reused forward-shadow, not pristine OOS.',
        'FAST confirmation uses first raw-price close crossing as LAB039/LAB040 approximation to live timer/quote behavior.',
        'CORE and FAST are independent lanes; portfolio overlap is allowed and risk concurrency is audited.',
        'Rejected FAST candidates do not consume pause/day quota; accepted FAST trades do. This is intentional stateful gate-before-entry behavior.'
      ]
    }
    (OUT/'summary.json').write_text(json.dumps(result,indent=2))

    rows=[]
    for period,d in [('historical',hist),('2026',fwd)]:
        rows.append({'period':period,'variant':'CORE',**{x:d['CORE'][x] for x in ['N','trades_per_month','EV','PF','SumR','MaxDD_R','R_DD','MaxConsecutiveLosses']}})
        for k,m in d['gates'].items():
            rows.append({'period':period,'variant':k,**{x:m[x] for x in ['N','trades_per_month','EV','PF','SumR','MaxDD_R','R_DD','MaxConsecutiveLosses']}})
        for k,m in d['portfolios'].items():
            rows.append({'period':period,'variant':k,'N':m['trades'],'trades_per_month':m['trades_per_month'],
                         'EV':m['EV'],'PF':m['PF'],'SumR':m['SumR'],'MaxDD_R':m['MaxDD_R'],'R_DD':m['R_DD'],
                         'MaxConsecutiveLosses':m['MaxConsecutiveLosses'],'max_concurrent_risk_units':m['max_concurrent_risk_units']})
    pd.DataFrame(rows).to_csv(OUT/'comparison.csv',index=False)

    lines=['# LAB041 — FAST_LANE_COMPOSITE_GATE_AND_PORTFOLIO_REPLAY','',
           '## CORE baseline',f"- Hist: {fmt(hist['CORE'])}",f"- 2026: {fmt(fwd['CORE'])}",'',
           '## Standalone gated FAST']
    for g in ['G1_RESPONSE','G2_RESPONSE_RECLAIM','G3_FULL_COMPOSITE']:
        lines += [f"- {g}: hist {fmt(hist['gates'][g])} | 2026 {fmt(fwd['gates'][g])}"]
    lines += ['','## Combined portfolio']
    for k in hist['portfolios']:
        hm=hist['portfolios'][k];fm=fwd['portfolios'][k]
        lines += [f"- {k}: hist {fmt(hm)} maxRisk={hm['max_concurrent_risk_units']:.2f}u | 2026 {fmt(fm)} maxRisk={fm['max_concurrent_risk_units']:.2f}u | PASS={promotions[k]['pass']}"]
    lines += ['','## Promotion checks',json.dumps(promotions,indent=2),'','## Limitations']+[f'- {x}' for x in result['limitations']]
    (OUT/'REPORT.md').write_text('\n'.join(lines))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__':
    main()
