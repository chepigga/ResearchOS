from pathlib import Path
import json, zipfile, importlib.util, itertools
import numpy as np
import pandas as pd
from numba import njit

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'
OUT=ROOT/'output'
OUT.mkdir(parents=True,exist_ok=True)

_core_path=Path(__file__).resolve().parents[1]/'CROWDFADE_V200_SEQUENTIAL_CHANGE_LABS_033_035'/'run.py'
_spec=importlib.util.spec_from_file_location('crowdfade_core_033_035',_core_path)
core=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(core)

# FAST entry frozen from LAB039
FAST_Z_LO=1.00
FAST_Z_HI=2.05
CONF_ATR=0.30
CONF_TTL=10800
PAUSE_ATR=1.00
MAXDAY=3
COST_BPS=.50

# Use v200 exit shell for discriminator attribution: LAB039 showed v191 exits structurally negative.
SL=4.5
TP=10.0
HOLD=86400

def load_flow():
    zp=DATA/'BTCUSDT_flow_2021-01-2026-08.csv.zip'
    with zipfile.ZipFile(zp) as z:
        n=[x for x in z.namelist() if x.lower().endswith('.csv')][0]
        with z.open(n) as f:
            r=pd.read_csv(f,usecols=['create_time','sum_open_interest','count_long_short_ratio'])
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

def prep(raw,ft,fz,start,end):
    ts,O,H,L,C=raw
    order=np.argsort(ts);ts=ts[order];O=O[order];H=H[order];L=L[order];C=C[order]
    keep=np.r_[True,ts[1:]!=ts[:-1]]
    ts=ts[keep];O=O[keep];H=H[keep];L=L[keep];C=C[keep]

    # M15 ATR
    b15=(ts//900)*900
    st15=np.r_[0,np.flatnonzero(b15[1:]!=b15[:-1])+1]
    en15=np.r_[st15[1:],len(ts)]
    bt15=b15[st15];bh15=np.maximum.reduceat(H,st15);bl15=np.minimum.reduceat(L,st15);bc15=C[en15-1]
    pc=np.r_[bc15[0],bc15[:-1]]
    tr=np.maximum(bh15-bl15,np.maximum(np.abs(bh15-pc),np.abs(bl15-pc)))
    atr15=pd.Series(tr).rolling(14,min_periods=14).mean().to_numpy()
    av15=bt15+900

    # M5 closes
    b5=(ts//300)*300
    st5=np.r_[0,np.flatnonzero(b5[1:]!=b5[:-1])+1]
    en5=np.r_[st5[1:],len(ts)]
    bt5=b5[st5];h5=np.maximum.reduceat(H,st5);l5=np.minimum.reduceat(L,st5);c5=C[en5-1];av5=bt5+300

    h1t,h1s=tf_states(ts,C,3600)
    h4t,h4s=tf_states(ts,C,14400)

    fi=np.searchsorted(ft,av5,'left')-1
    ai=np.searchsorted(av15,av5,'right')-1
    h1i=np.searchsorted(h1t,av5,'right')-1
    h4i=np.searchsorted(h4t,av5,'right')-1
    fi0=np.maximum(fi,0);ai0=np.maximum(ai,0);h1i0=np.maximum(h1i,0);h4i0=np.maximum(h4i,0)
    good=(av5>=start)&(av5<end)&(fi>=0)&(ai>=0)&(h1i>=0)&(h4i>=0)&np.isfinite(fz[fi0])&np.isfinite(atr15[ai0])
    good &= ((av5-ft[fi0])>=0)&((av5-ft[fi0])<=600)

    return (ts,O,H,L,C,av5[good],h5[good],l5[good],c5[good],fz[fi[good]],atr15[ai[good]],h1s[h1i[good]],h4s[h4i[good]])

@njit(cache=True)
def extract_events(ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5,H1,H4):
    cap=len(dt5)
    R=np.zeros(cap);ST=np.zeros(cap,np.int64);CT=np.zeros(cap,np.int64);ET=np.zeros(cap,np.int64)
    SIDE=np.zeros(cap,np.int8);OZ=np.zeros(cap);CZ=np.zeros(cap);SA=np.zeros(cap);CA=np.zeros(cap)
    CMIN=np.zeros(cap);CEX=np.zeros(cap);RESP=np.zeros(cap);RECLAIM=np.zeros(cap);H1A=np.zeros(cap,np.int8);H4A=np.zeros(cap,np.int8)
    n=0;k=0;last=0.;la=0.;has=False;day=-1;dc=0;nextts=0

    while k<len(dt5)-3:
        t=dt5[k]
        if t<nextts:k+=1;continue
        d=t//86400
        if d!=day:day=d;dc=0
        if dc>=MAXDAY:k+=1;continue

        z=Z5[k];az=abs(z)
        if az<FAST_Z_LO or az>=FAST_Z_HI:
            k+=1;continue
        side=-1 if z>0 else 1
        sig=C5[k];siga=A5[k]
        if has and abs(sig-last)<PAUSE_ATR*la:
            k+=1;continue

        target=sig+side*CONF_ATR*siga
        j=k+1;ci=-1
        maxcrowd=0.;maxthesis=0.
        while j<len(dt5) and dt5[j]<=t+CONF_TTL:
            crowd_exc=((H5[j]-sig) if side<0 else (sig-L5[j]))/siga
            thesis_exc=((sig-L5[j]) if side<0 else (H5[j]-sig))/siga
            if crowd_exc>maxcrowd:maxcrowd=crowd_exc
            if thesis_exc>maxthesis:maxthesis=thesis_exc
            if (side>0 and C5[j]>=target) or (side<0 and C5[j]<=target):
                ci=j;break
            j+=1
        if ci<0:
            k+=1;continue

        # LAB035B sign-flip consistency remains ON.
        if z*Z5[ci]<0.0:
            k=ci+1;continue

        # Market entry at completed M5 confirm close (causal approximation to v191 timer quote).
        entry=C5[ci]
        ei=np.searchsorted(ts,dt5[ci]-1,'right')-1
        if ei<0:
            k=ci+1;continue

        # Current completed M15 ATR at confirmation approximated by A5[ci].
        curA=A5[ci]
        atr_exp=curA/siga if siga>0 else 0.
        confirm_min=(dt5[ci]-t)/60.0
        # response quality: thesis excursion / (crowd excursion + epsilon), clipped later only in bins.
        response=maxthesis/(maxcrowd+1e-9)
        # reclaim: confirm close displacement beyond signal, in ATR, positive by construction if confirmed.
        reclaim=side*(C5[ci]-sig)/siga

        risk=SL*siga;sl=entry-side*risk;tp=entry+side*TP*siga
        xe=min(len(ts)-1,np.searchsorted(ts,ts[ei]+HOLD,'left'))
        xp=C[xe];ex=xe
        for q in range(ei+1,xe+1):
            sh=(side>0 and L[q]<=sl) or (side<0 and H[q]>=sl)
            th=(side>0 and H[q]>=tp) or (side<0 and L[q]<=tp)
            if sh:xp=sl;ex=q;break
            if th:xp=tp;ex=q;break

        rr=side*(xp-entry)/risk-(COST_BPS/10000.)*entry/risk
        R[n]=rr;ST[n]=t;CT[n]=dt5[ci];ET[n]=ts[ei];SIDE[n]=side;OZ[n]=z;CZ[n]=Z5[ci]
        SA[n]=siga;CA[n]=curA;CMIN[n]=confirm_min;CEX[n]=maxcrowd;RESP[n]=response;RECLAIM[n]=reclaim
        H1A[n]=H1[k];H4A[n]=H4[k];n+=1

        dc+=1;last=entry;la=siga;has=True;nextts=ts[ex]+1
        k=np.searchsorted(dt5,nextts)

    return (R[:n],ST[:n],CT[:n],ET[:n],SIDE[:n],OZ[:n],CZ[:n],SA[:n],CA[:n],CMIN[:n],CEX[:n],RESP[:n],RECLAIM[:n],H1A[:n],H4A[:n])

def to_df(z):
    R,st,ct,et,side,oz,cz,sa,ca,cmin,cex,resp,recl,h1,h4=z
    d=pd.DataFrame({'R':R,'signal_ts':st,'confirm_ts':ct,'entry_ts':et,'side':side,'orig_z':oz,'confirm_z':cz,
                    'signal_atr':sa,'confirm_atr':ca,'confirm_min':cmin,'crowd_exc_atr':cex,'response_ratio':resp,
                    'reclaim_atr':recl,'h1':h1,'h4':h4})
    d['atr_expansion']=d.confirm_atr/d.signal_atr
    d['abs_z']=d.orig_z.abs()
    d['signal_time_utc']=pd.to_datetime(d.signal_ts,unit='s',utc=True)
    d['trend_state']=np.select([
        (d.h1==d.side)&(d.h4==d.side),
        (d.h1==-d.side)&(d.h4==-d.side),
        ((d.h1==d.side)^(d.h4==d.side))
      ],['BOTH_ALIGN','BOTH_OPPOSE','ONE_ALIGN'],default='MIXED_NEUTRAL')
    return d

def add_bins(d):
    d=d.copy()
    d['z_band']=pd.cut(d.abs_z,[1.0,1.25,1.50,1.75,2.05],right=False,include_lowest=True,
                       labels=['1.00-1.25','1.25-1.50','1.50-1.75','1.75-2.05'])
    d['confirm_bin']=pd.cut(d.confirm_min,[0,15,30,60,120,181],right=True,include_lowest=True,
                            labels=['<=15','15-30','30-60','60-120','120-180'])
    d['crowd_bin']=pd.cut(d.crowd_exc_atr,[-1e-9,.25,.50,1.0,1.5,99],right=False,
                          labels=['<0.25','0.25-0.50','0.50-1.00','1.00-1.50','>=1.50'])
    d['atr_bin']=pd.cut(d.atr_expansion,[0,.90,1.10,1.25,1.50,99],right=False,
                        labels=['<0.90','0.90-1.10','1.10-1.25','1.25-1.50','>=1.50'])
    d['response_bin']=pd.cut(d.response_ratio,[0,.50,1.0,1.5,2.5,99],right=False,
                             labels=['<0.50','0.50-1.00','1.00-1.50','1.50-2.50','>=2.50'])
    d['reclaim_bin']=pd.cut(d.reclaim_atr,[0,.35,.50,.75,1.0,99],right=False,
                            labels=['0.30-0.35','0.35-0.50','0.50-0.75','0.75-1.00','>=1.00'])
    return d

def met(x):
    return core.metrics(np.asarray(x,float))

def sample_metrics(d,mask):
    x=d.loc[mask,'R'].to_numpy(float)
    m=met(x)
    return m

def split_masks(d):
    y=d.signal_time_utc.dt.year
    return {
      'DISC_2021_23':(y>=2021)&(y<=2023),
      'VAL_2024_25':(y>=2024)&(y<=2025),
      'ALL_2021_25':(y>=2021)&(y<=2025)
    }

def rule_text(rule):
    return ' & '.join([f"{k} in {{{','.join(map(str,v))}}}" for k,v in rule.items()])

def apply_rule(d,rule):
    m=np.ones(len(d),dtype=bool)
    for k,vals in rule.items():
        m &= d[k].astype(str).isin(vals).to_numpy()
    return m

def enumerate_rules(hist,fwd):
    # Pre-registered, low-complexity rule family:
    # one single feature OR pairwise AND of two categorical bins/states.
    features=['z_band','confirm_bin','trend_state','crowd_bin','atr_bin','response_bin','reclaim_bin']
    vals={f:[str(x) for x in hist[f].dropna().astype(str).unique()] for f in features}

    candidates=[]
    # Single selected bin OR contiguous-ish unions limited to 1-2 labels per feature.
    for f in features:
        for r in [1,2]:
            for combo in itertools.combinations(vals[f],r):
                candidates.append({f:list(combo)})
    # Pairwise interactions, one bin/state each to limit curve fitting.
    for f1,f2 in itertools.combinations(features,2):
        for v1 in vals[f1]:
            for v2 in vals[f2]:
                candidates.append({f1:[v1],f2:[v2]})
    return candidates

def evaluate_rule(hist,fwd,rule):
    hm=apply_rule(hist,rule);fm=apply_rule(fwd,rule)
    hs=split_masks(hist)
    out={}
    for name,sm in hs.items():
        out[name]=sample_metrics(hist,hm&sm.to_numpy())
    out['FWD_2026']=sample_metrics(fwd,fm)
    out['coverage_hist']=float(hm.mean())
    out['coverage_fwd']=float(fm.mean())
    return out

def pass_gate(e):
    d=e['DISC_2021_23'];v=e['VAL_2024_25'];f=e['FWD_2026']
    # Strict cross-period positivity and minimum count.
    if min(d['N'],v['N'],f['N']) < 20:return False
    if not (d['EV']>0 and v['EV']>0 and f['EV']>0):return False
    if not (d['PF']>1 and v['PF']>1 and f['PF']>1):return False
    # Avoid trivial tiny subsets and unstable razor-thin edges.
    if f['EV']<0.05 or v['EV']<0.03:return False
    return True

def score(e):
    d=e['DISC_2021_23'];v=e['VAL_2024_25'];f=e['FWD_2026']
    # Conservative: maximize worst EV, then forward count, then all-history R/DD.
    return (min(d['EV'],v['EV'],f['EV']), f['N'], e['ALL_2021_25']['R_DD'])

def bootstrap_rule(df,rule,reps=10000,seed=40040):
    m=apply_rule(df,rule)
    q=df.loc[m,['R','signal_time_utc']].copy()
    if len(q)<20:return {'N':len(q)}
    q['month']=q.signal_time_utc.dt.to_period('M').astype(str)
    months=[g.R.sum() for _,g in q.groupby('month')]
    a=np.asarray(months,float)
    rng=np.random.default_rng(seed)
    sums=np.empty(reps)
    for i in range(reps):
        sums[i]=rng.choice(a,size=len(a),replace=True).sum()
    return {'N':len(q),'months':len(a),'observed_sumR':float(q.R.sum()),
            'p_sumR_gt_0':float((sums>0).mean()),
            'ci95':[float(np.quantile(sums,.025)),float(np.quantile(sums,.975))]}

def main():
    ft,fz=load_flow()
    hraw=load_hist();fraw=load_sec()
    hist=add_bins(to_df(extract_events(*prep(hraw,ft,fz,int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-01-01',tz='UTC').timestamp())))))
    fwd=add_bins(to_df(extract_events(*prep(fraw,ft,fz,int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-09-01',tz='UTC').timestamp())))))

    hist.to_csv(OUT/'fast_candidates_historical.csv',index=False)
    fwd.to_csv(OUT/'fast_candidates_forward.csv',index=False)

    baseline={
      'historical':met(hist.R.to_numpy(float)),
      'forward':met(fwd.R.to_numpy(float))
    }

    # Feature marginal tables
    marg={}
    for f in ['z_band','confirm_bin','trend_state','crowd_bin','atr_bin','response_bin','reclaim_bin']:
        marg[f]={}
        for val in sorted(hist[f].dropna().astype(str).unique()):
            rule={f:[val]}
            marg[f][val]=evaluate_rule(hist,fwd,rule)

    candidates=[]
    for rule in enumerate_rules(hist,fwd):
        e=evaluate_rule(hist,fwd,rule)
        if pass_gate(e):
            candidates.append((score(e),rule,e))
    candidates.sort(key=lambda x:x[0],reverse=True)

    # Deduplicate near-identical masks, keep top 20 unique selections.
    uniq=[];seen=set()
    for sc,rule,e in candidates:
        sig=(tuple(apply_rule(hist,rule).tolist()),tuple(apply_rule(fwd,rule).tolist()))
        h=hash(sig)
        if h in seen:continue
        seen.add(h);uniq.append((sc,rule,e))
        if len(uniq)>=20:break

    best=None
    if uniq:
        best={'rule':uniq[0][1],'metrics':uniq[0][2],
              'bootstrap_hist':bootstrap_rule(hist,uniq[0][1],seed=40040),
              'bootstrap_fwd':bootstrap_rule(fwd,uniq[0][1],seed=40041)}

    # Also report robust single-feature rules separately: easier to implement/interpret.
    singles=[]
    for sc,rule,e in candidates:
        if len(rule)==1:
            singles.append({'rule':rule,'metrics':e,'score':list(sc)})
    singles=singles[:20]

    result={
      'lab':'LAB040_FAST_LANE_DISCRIMINATOR',
      'population':'FAST candidate 1.0<=|Z|<2.05, M5 confirm .30 <=3h, sign-flip cancel, market entry, v200 SL4.5/TP10/H24 for attribution',
      'baseline':baseline,
      'feature_marginals':marg,
      'pass_count':len(candidates),
      'top_rules':[{'rank':i+1,'rule':r,'metrics':e,'score':list(sc)} for i,(sc,r,e) in enumerate(uniq)],
      'top_single_feature_rules':singles,
      'best':best,
      'gate':'N>=20 in discovery, validation, forward; EV>0 and PF>1 in all three; validation EV>=0.03; forward EV>=0.05',
      'limitations':[
        '2021-2023 discovery, 2024-2025 internal validation, 2026 reused forward-shadow; 2026 is not pristine OOS.',
        'Rule family is restricted to simple one-feature unions or two-feature ANDs to reduce overfit.',
        'BTC only; ETH/SOL transfer remains mandatory before production.',
        'Exit shell is v200 to isolate entry discrimination; final hybrid must rerun full portfolio sequence.',
        'Confirmation is completed-M5 close approximation, not exact live quote timer behavior.'
      ]
    }
    (OUT/'summary.json').write_text(json.dumps(result,indent=2))

    rows=[]
    for i,(sc,r,e) in enumerate(uniq):
        row={'rank':i+1,'rule':rule_text(r),'score_minEV':sc[0],'score_fwdN':sc[1]}
        for p in ['DISC_2021_23','VAL_2024_25','ALL_2021_25','FWD_2026']:
            m=e[p]
            for k in ['N','EV','PF','SumR','MaxDD_R','R_DD']:
                row[f'{p}_{k}']=m[k]
        rows.append(row)
    pd.DataFrame(rows).to_csv(OUT/'top_rules.csv',index=False)

    def fmt(m):
        return f"N={m['N']} EV={m['EV']:+.4f} PF={m['PF']:.3f} Sum={m['SumR']:+.2f}R DD={m['MaxDD_R']:.2f} R/DD={m['R_DD']:.3f}"
    lines=['# LAB040 — FAST_LANE_DISCRIMINATOR','',
           'Population: 1.0 <= |Z| < 2.05, M5 confirm .30 ATR <=3h, sign-flip cancel, market entry, v200 exits.','',
           f"- Raw historical: {fmt(baseline['historical'])}",
           f"- Raw 2026: {fmt(baseline['forward'])}",'',
           f"Passing simple causal rules: **{len(candidates)}**",'']
    if best:
        lines += ['## Best cross-period rule',f"**{rule_text(best['rule'])}**",
                  f"- Discovery 2021-23: {fmt(best['metrics']['DISC_2021_23'])}",
                  f"- Validation 2024-25: {fmt(best['metrics']['VAL_2024_25'])}",
                  f"- All 2021-25: {fmt(best['metrics']['ALL_2021_25'])}",
                  f"- 2026: {fmt(best['metrics']['FWD_2026'])}",
                  f"- Hist bootstrap: {json.dumps(best['bootstrap_hist'])}",
                  f"- 2026 bootstrap: {json.dumps(best['bootstrap_fwd'])}",'']
    lines += ['## Top robust rules']
    for i,(sc,r,e) in enumerate(uniq[:10]):
        lines += [f"{i+1}. {rule_text(r)} | DISC {fmt(e['DISC_2021_23'])} | VAL {fmt(e['VAL_2024_25'])} | 2026 {fmt(e['FWD_2026'])}"]
    lines += ['','## Limitations']+[f'- {x}' for x in result['limitations']]
    (OUT/'REPORT.md').write_text('\n'.join(lines))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__':
    main()
