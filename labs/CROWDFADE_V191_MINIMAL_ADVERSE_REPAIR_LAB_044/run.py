from pathlib import Path
import json, importlib.util
import numpy as np
import pandas as pd
from numba import njit

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'; OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)

# Reuse LAB043 validated loaders, prep, v192 control, metrics and frozen v191 management.
p43=Path(__file__).resolve().parents[1]/'CROWDFADE_V191D_TO_V191F_ABLATION_LAB_043'/'run.py'
spec=importlib.util.spec_from_file_location('lab043',p43)
lab43=importlib.util.module_from_spec(spec); spec.loader.exec_module(lab43)
lab43.DATA=DATA

COST_BPS=lab43.COST_BPS
MAXDAY=lab43.MAXDAY
PAUSE_ATR=lab43.PAUSE_ATR
V191_Z=lab43.V191_Z
V191_CONFIRM_ATR=lab43.V191_CONFIRM_ATR

# Pre-registered LAB044 variants. No threshold optimization.
V191D=0
ADV_ONLY=1
FRESH45_ADV=2
ADV_EXITOFF=3
FRESH45_ADV_EXITOFF=4
FULL_V191F=5
NAMES={
0:'V191D_CONTROL',
1:'V191D_PLUS_ADVERSE075',
2:'V191D_PLUS_FRESH45_PLUS_ADVERSE075',
3:'V191D_PLUS_ADVERSE075_EXITZ_OFF',
4:'V191D_PLUS_FRESH45_ADVERSE075_EXITZ_OFF',
5:'FULL_V191F_CONTROL'
}

@njit(cache=True)
def cfg(v):
    # ttl seconds, exit_z, same_side, min_abs_z, adverse_gate, response_gate
    if v==V191D:
        return 10800,0.75,0,0.0,0,0
    if v==ADV_ONLY:
        return 10800,0.75,0,0.0,1,0
    if v==FRESH45_ADV:
        return 2700,0.75,0,0.0,1,0
    if v==ADV_EXITOFF:
        return 10800,0.0,0,0.0,1,0
    if v==FRESH45_ADV_EXITOFF:
        return 2700,0.0,0,0.0,1,0
    # exact LAB043 full-v191f shell
    return 2700,0.0,1,0.75,1,1

@njit(cache=True)
def sim(ts,O,H,L,C,dt5,H5,L5,C5,Z5,A5,variant):
    cap=len(dt5)
    R=np.zeros(cap);ST=np.zeros(cap,np.int64);ET=np.zeros(cap,np.int64);XT=np.zeros(cap,np.int64)
    SIDE=np.zeros(cap,np.int8);RS=np.zeros(cap,np.int8);AGE=np.zeros(cap);CZ=np.zeros(cap)
    ADV=np.zeros(cap);RESP=np.zeros(cap)
    n=0;k=0;day=-1;dc=0;nextts=0;last=0.;la=0.;has=False
    ttl,exit_z,same_side,min_abs_z,use_adv,use_resp=cfg(variant)

    while k<len(dt5)-3:
        t=dt5[k]
        if t<nextts:k+=1;continue
        d=t//86400
        if d!=day:day=d;dc=0
        if dc>=MAXDAY:k+=1;continue

        z0=Z5[k]
        side=-1 if z0>=V191_Z else (1 if z0<=-V191_Z else 0)
        if side==0:k+=1;continue
        sig=C5[k];atr=A5[k]
        if has and abs(sig-last)<PAUSE_ATR*la:k+=1;continue

        target=sig+side*V191_CONFIRM_ATR*atr
        ps=np.searchsorted(ts,t+1);pe=np.searchsorted(ts,t+ttl,'right')
        ci=-1;maxadv=0.;maxfav=0.
        for q in range(ps,min(len(ts),pe)):
            adv=((H[q]-sig) if side<0 else (sig-L[q]))/atr
            fav=((sig-L[q]) if side<0 else (H[q]-sig))/atr
            if adv>maxadv:maxadv=adv
            if fav>maxfav:maxfav=fav

            if use_adv==1 and maxadv>0.75:
                ci=-2
                break

            if (side>0 and C[q]>=target) or (side<0 and C[q]<=target):
                ci=q
                break

        if ci<0:
            k+=1
            continue

        zi=np.searchsorted(dt5,ts[ci],'right')-1
        if zi<0:k+=1;continue
        cz=Z5[zi]

        # v191d original consistency unless same-side requested.
        if same_side==1:
            if (side>0 and cz>=0.0) or (side<0 and cz<=0.0):
                k=np.searchsorted(dt5,ts[ci])+1;continue
        else:
            if (side>0 and cz>=0.75) or (side<0 and cz<=-0.75):
                k=np.searchsorted(dt5,ts[ci])+1;continue

        if min_abs_z>0 and abs(cz)<min_abs_z:
            k=np.searchsorted(dt5,ts[ci])+1;continue

        response=maxfav/(maxadv+1e-9)
        if use_resp==1 and response<0.50:
            k=np.searchsorted(dt5,ts[ci])+1;continue

        entry=C[ci]
        rr,ex,reason=lab43.manage_v191(ts,H,L,C,dt5,Z5,ci,side,entry,atr,exit_z)
        R[n]=rr;ST[n]=t;ET[n]=ts[ci];XT[n]=ts[ex];SIDE[n]=side;RS[n]=reason
        AGE[n]=(ts[ci]-t)/60.;CZ[n]=cz;ADV[n]=maxadv;RESP[n]=response;n+=1

        dc+=1;last=entry;la=atr;has=True;nextts=ts[ex]+1;k=np.searchsorted(dt5,nextts)

    return R[:n],ST[:n],ET[:n],XT[:n],SIDE[:n],RS[:n],AGE[:n],CZ[:n],ADV[:n],RESP[:n]

REASONS=lab43.REASONS

def make_df(z):
    R,st,et,xt,side,rs,age,cz,adv,resp=z
    return pd.DataFrame({
      'R':R,'signal_ts':st,'entry_ts':et,'exit_ts':xt,'side':side,
      'exit_reason':[REASONS.get(int(x),'?') for x in rs],
      'confirm_age_min':age,'confirm_z':cz,'max_adverse_atr':adv,'response_ratio':resp})

def summarize(df,kind):
    t=pd.to_datetime(df.signal_ts,unit='s',utc=True)
    key=t.dt.year.astype(str) if kind=='year' else t.dt.strftime('%Y-%m')
    return {
      'all':lab43.metrics(df.R.to_numpy(float)),
      'periods':{str(k):lab43.metrics(g.R.to_numpy(float)) for k,g in df.groupby(key)},
      'side':{'BUY':lab43.metrics(df[df.side>0].R.to_numpy(float)),
              'SELL':lab43.metrics(df[df.side<0].R.to_numpy(float))},
      'exit_reasons':{str(k):int(v) for k,v in df.exit_reason.value_counts().items()},
      'confirm_age':{
        'median_min':float(df.confirm_age_min.median()) if len(df) else None,
        'p90_min':float(df.confirm_age_min.quantile(.9)) if len(df) else None,
        'max_min':float(df.confirm_age_min.max()) if len(df) else None}
    }

def run_period(raw,ft,fz,start,end,label):
    p=lab43.prep(raw,ft,fz,start,end)
    out={}

    d192=lab43.df192(lab43.sim_v192(*p))
    d192.to_csv(OUT/f'{label}_V192_CANONICAL_CONTROL.csv',index=False)
    out['V192_CANONICAL_CONTROL']=lab43.summarize(d192,'year' if label=='historical' else 'month')

    for v in range(6):
        d=make_df(sim(*p,v))
        d.to_csv(OUT/f'{label}_{NAMES[v]}.csv',index=False)
        out[NAMES[v]]=summarize(d,'year' if label=='historical' else 'month')
    return out

def matched(label):
    names=['V191D_CONTROL','V191D_PLUS_ADVERSE075','V191D_PLUS_FRESH45_PLUS_ADVERSE075',
           'V191D_PLUS_ADVERSE075_EXITZ_OFF','V191D_PLUS_FRESH45_ADVERSE075_EXITZ_OFF','FULL_V191F_CONTROL']
    dfs={n:pd.read_csv(OUT/f'{label}_{n}.csv') for n in names}
    rows=[]
    base=dfs['V191D_CONTROL']
    kb=set(zip(base.signal_ts,base.side))
    for n in names[1:]:
        b=dfs[n];kn=set(zip(b.signal_ts,b.side))
        rem=base[[((x,y) in kb-kn) for x,y in zip(base.signal_ts,base.side)]]
        add=b[[((x,y) in kn-kb) for x,y in zip(b.signal_ts,b.side)]]
        rows.append({'variant':n,'N':len(b),'delta_N_vs_v191d':len(b)-len(base),
          'removed_signal_count':len(kb-kn),'added_signal_count':len(kn-kb),
          'removed_trade_sumR':float(rem.R.sum()),'added_trade_sumR':float(add.R.sum()),
          'full_sequence_deltaR':float(b.R.sum()-base.R.sum())})
    return rows

def fmt(m):
    return f"N={m['N']} WR={m['WR']:.1%} EV={m['EV']:+.4f} PF={m['PF']:.3f} Sum={m['SumR']:+.2f}R DD={m['MaxDD_R']:.2f} R/DD={m['R_DD']:.3f} MCL={m['MaxConsecutiveLosses']}"

def main():
    ft,fz=lab43.load_flow();hist=lab43.load_hist();sec=lab43.load_sec()
    h=run_period(hist,ft,fz,int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-01-01',tz='UTC').timestamp()),'historical')
    f=run_period(sec,ft,fz,int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()),'forward')
    mh=matched('historical');mf=matched('forward')

    result={
      'lab':'CROWDFADE_V191_MINIMAL_ADVERSE_REPAIR_LAB_044',
      'question':'Can the v191 frequency shell be repaired using only the cross-sample adverse-excursion signal, with or without freshness45 and ExitZ?',
      'preregistered_variants':{
        'V191D_CONTROL':'Exact LAB043 v191d control.',
        'V191D_PLUS_ADVERSE075':'v191d + cancel episode when pre-confirm adverse excursion exceeds 0.75 ATR; ExitZ retained; 3h confirm window retained.',
        'V191D_PLUS_FRESH45_PLUS_ADVERSE075':'same + 45m confirmation TTL; ExitZ retained.',
        'V191D_PLUS_ADVERSE075_EXITZ_OFF':'adverse gate only, but ExitZ disabled; 3h confirm window retained.',
        'V191D_PLUS_FRESH45_ADVERSE075_EXITZ_OFF':'adverse gate + 45m freshness + ExitZ disabled.',
        'FULL_V191F_CONTROL':'LAB043 full v191f shell control.'
      },
      'historical':h,'forward_2026_shadow':f,
      'matched_vs_v191d':{'historical':mh,'forward_2026_shadow':mf},
      'limitations':['BTCUSDT only.','Historical 2021-2025 = 1-minute OHLC; 2026 Mar-Aug = second OHLC.','2026 is reused forward-shadow/stress, not pristine OOS.','No thresholds were optimized in LAB044; 0.75 ATR and 45m were frozen from prior live diagnosis / LAB043.','v191 MT5 remains tick/timer-driven; replay uses raw close crossing for confirmation.','v192 remains immutable reference and is reconstructed on the common replay frame.','Flat 0.5bps cost proxy; broker-specific IC/GetLeveraged divergence still needs forward validation.']}
    (OUT/'summary.json').write_text(json.dumps(result,indent=2))

    rows=[]
    for period,d in [('historical',h),('2026',f)]:
        for name,v in d.items():rows.append({'period':period,'variant':name,**v['all']})
    pd.DataFrame(rows).to_csv(OUT/'comparison.csv',index=False)
    pd.DataFrame(mh).assign(period='historical').to_csv(OUT/'matched_vs_v191d_historical.csv',index=False)
    pd.DataFrame(mf).assign(period='2026').to_csv(OUT/'matched_vs_v191d_2026.csv',index=False)

    lines=['# LAB044 — MINIMAL ADVERSE REPAIR','',
      result['question'],'',
      'No exit geometry or threshold optimization was allowed. v192 is immutable control.','',
      '## Full sample']
    for period,d in [('Historical 2021–2025',h),('2026 Mar–Aug shadow',f)]:
        lines+=['',f'### {period}']
        for name,v in d.items():lines.append(f"- {name}: {fmt(v['all'])}")
    lines+=['','## Matched/reachability delta vs v191d — historical']
    for x in mh:lines.append('- '+json.dumps(x))
    lines+=['','## Matched/reachability delta vs v191d — 2026']
    for x in mf:lines.append('- '+json.dumps(x))
    lines+=['','## Period consistency']
    for period,d in [('Historical',h),('2026',f)]:
        lines+=['',f'### {period}']
        for name,v in d.items():lines.append(f"- {name}: {json.dumps(v['periods'])}")
    lines+=['','## Exit / age diagnostics']
    for period,d in [('Historical',h),('2026',f)]:
        lines+=['',f'### {period}']
        for name,v in d.items():
            lines.append(f"- {name}: exits={json.dumps(v['exit_reasons'])}; age={json.dumps(v['confirm_age'])}")
    lines+=['','## Limitations']+[f"- {x}" for x in result['limitations']]
    (OUT/'REPORT.md').write_text('\n'.join(lines))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__':main()
