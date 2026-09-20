from pathlib import Path
import json, zipfile, importlib.util
import numpy as np
import pandas as pd
from numba import njit

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'
OUT=ROOT/'output'
OUT.mkdir(parents=True,exist_ok=True)

# Reuse LAB041 exact parsing / v200 exit geometry / metrics.
_lab041_path=Path(__file__).resolve().parents[1]/'CROWDFADE_FAST_LANE_COMPOSITE_GATE_PORTFOLIO_LAB_041'/'run.py'
_spec=importlib.util.spec_from_file_location('lab041_core_fast',_lab041_path)
lab041=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lab041)
lab041.DATA=DATA
core=lab041.core

FAST_Z_LO=lab041.FAST_Z_LO
FAST_Z_HI=lab041.FAST_Z_HI
FAST_CONFIRM_TTL=lab041.FAST_CONFIRM_TTL
FAST_PAUSE_ATR=lab041.FAST_PAUSE_ATR
MAXDAY=lab041.MAXDAY
SL=lab041.FAST_SL
TP=lab041.FAST_TP
HOLD=lab041.FAST_HOLD
COST_BPS=lab041.COST_BPS

BASE_CONFIRM=0.30
EARLY_LEVELS=[0.10,0.15,0.20,0.25,0.30]
RETRACE_LEVELS=[0.10,0.20,0.30]
RETRACE_TTL=1200  # 20m, preregistered

# ---------- helpers ----------
def met(x):
    return core.metrics(np.asarray(x,float))

def fmt(m):
    return f"N={m['N']} EV={m['EV']:+.4f} PF={m['PF']:.3f} Sum={m['SumR']:+.2f}R DD={m['MaxDD_R']:.2f} R/DD={m['R_DD']:.3f}"

def g1_branch(one_align,response):
    if not one_align:
        return 0
    if 0.50 <= response < 1.00:
        return 1
    if response >= 2.50:
        return 2
    return 0

@njit(cache=True)
def g1_branch_nb(one_align,response):
    if not one_align:
        return 0
    if response>=0.50 and response<1.00:
        return 1
    if response>=2.50:
        return 2
    return 0

# ---------- paired baseline G1 episode audit ----------
@njit(cache=True)
def baseline_g1_audit(ts,O,H,L,C,dt5,C5,Z5,A5,H1,H4):
    cap=len(dt5)
    R=np.zeros(cap);ST=np.zeros(cap,np.int64);ET=np.zeros(cap,np.int64);XT=np.zeros(cap,np.int64)
    SIDE=np.zeros(cap,np.int8);SIGP=np.zeros(cap);ATR=np.zeros(cap);OZ=np.zeros(cap)
    RESP=np.zeros(cap);BRANCH=np.zeros(cap,np.int8)
    FIRST_TOUCH_010=np.full(cap,-1,np.int64)
    FIRST_CLOSE_010=np.full(cap,-1,np.int64)
    FIRST_CLOSE_015=np.full(cap,-1,np.int64)
    FIRST_CLOSE_020=np.full(cap,-1,np.int64)
    FIRST_CLOSE_025=np.full(cap,-1,np.int64)
    FIRST_CLOSE_030=np.full(cap,-1,np.int64)
    MFE=np.zeros(cap);MAE=np.zeros(cap);ENTRYMOVE=np.zeros(cap)
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

        ps=np.searchsorted(ts,t+1);pe=np.searchsorted(ts,t+FAST_CONFIRM_TTL,'right')
        ci=-1;maxcrowd=0.;maxthesis=0.
        ft010=-1;fc010=-1;fc015=-1;fc020=-1;fc025=-1;fc030=-1
        pre_mfe=0.;pre_mae=0.
        for q in range(ps,min(len(ts),pe)):
            fav_touch=((H[q]-sig) if side>0 else (sig-L[q]))/siga
            adv_touch=((sig-L[q]) if side>0 else (H[q]-sig))/siga
            fav_close=side*(C[q]-sig)/siga
            crowd_exc=((H[q]-sig) if side<0 else (sig-L[q]))/siga
            thesis_exc=((sig-L[q]) if side<0 else (H[q]-sig))/siga

            if fav_touch>pre_mfe:pre_mfe=fav_touch
            if adv_touch>pre_mae:pre_mae=adv_touch
            if crowd_exc>maxcrowd:maxcrowd=crowd_exc
            if thesis_exc>maxthesis:maxthesis=thesis_exc

            if ft010<0 and fav_touch>=0.10:ft010=ts[q]
            if fc010<0 and fav_close>=0.10:fc010=ts[q]
            if fc015<0 and fav_close>=0.15:fc015=ts[q]
            if fc020<0 and fav_close>=0.20:fc020=ts[q]
            if fc025<0 and fav_close>=0.25:fc025=ts[q]
            if fc030<0 and fav_close>=0.30:
                fc030=ts[q];ci=q;break
        if ci<0:
            k+=1;continue

        zk=np.searchsorted(dt5,ts[ci],'right')-1
        if zk<0:
            k+=1;continue
        if z*Z5[zk]<0.0:
            k=np.searchsorted(dt5,ts[ci])+1;continue

        align1=(H1[k]==side);align4=(H4[k]==side)
        one_align=(align1!=align4)
        response=maxthesis/(maxcrowd+1e-9)
        branch=g1_branch_nb(one_align,response)
        if branch==0:
            k=np.searchsorted(dt5,ts[ci])+1;continue

        entry=C[ci];ei=ci
        risk=SL*siga;sl=entry-side*risk;tp=entry+side*TP*siga
        xe=min(len(ts)-1,np.searchsorted(ts,ts[ei]+HOLD,'left'))
        xp=C[xe];ex=xe
        for q in range(ei+1,xe+1):
            sh=(side>0 and L[q]<=sl) or (side<0 and H[q]>=sl)
            th=(side>0 and H[q]>=tp) or (side<0 and L[q]<=tp)
            if sh:xp=sl;ex=q;break
            if th:xp=tp;ex=q;break
        rr=side*(xp-entry)/risk-(COST_BPS/10000.)*entry/risk

        R[n]=rr;ST[n]=t;ET[n]=ts[ei];XT[n]=ts[ex];SIDE[n]=side;SIGP[n]=sig;ATR[n]=siga;OZ[n]=z
        RESP[n]=response;BRANCH[n]=branch
        FIRST_TOUCH_010[n]=ft010;FIRST_CLOSE_010[n]=fc010;FIRST_CLOSE_015[n]=fc015
        FIRST_CLOSE_020[n]=fc020;FIRST_CLOSE_025[n]=fc025;FIRST_CLOSE_030[n]=fc030
        MFE[n]=pre_mfe;MAE[n]=pre_mae;ENTRYMOVE[n]=side*(entry-sig)/siga
        n+=1

        dc+=1;last=entry;la=siga;has=True;nextts=ts[ex]+1;k=np.searchsorted(dt5,nextts)

    return (R[:n],ST[:n],ET[:n],XT[:n],SIDE[:n],SIGP[:n],ATR[:n],OZ[:n],RESP[:n],BRANCH[:n],
            FIRST_TOUCH_010[:n],FIRST_CLOSE_010[:n],FIRST_CLOSE_015[:n],FIRST_CLOSE_020[:n],
            FIRST_CLOSE_025[:n],FIRST_CLOSE_030[:n],MFE[:n],MAE[:n],ENTRYMOVE[:n])

def audit_df(z):
    (R,st,et,xt,side,sigp,atr,oz,resp,branch,ft010,fc010,fc015,fc020,fc025,fc030,mfe,mae,emove)=z
    d=pd.DataFrame({
        'R':R,'signal_ts':st,'entry_ts':et,'exit_ts':xt,'side':side,'signal_price':sigp,'signal_atr':atr,
        'orig_z':oz,'response_ratio':resp,
        'branch':np.where(branch==1,'MID_RESPONSE_0.50_1.00','STRONG_RESPONSE_GE_2.50'),
        'first_touch_010_ts':ft010,'first_close_010_ts':fc010,'first_close_015_ts':fc015,
        'first_close_020_ts':fc020,'first_close_025_ts':fc025,'first_close_030_ts':fc030,
        'pre_entry_mfe_atr':mfe,'pre_entry_mae_atr':mae,'entry_move_atr':emove
    })
    for col in ['first_touch_010','first_close_010','first_close_015','first_close_020','first_close_025','first_close_030']:
        tscol=col+'_ts'
        d[col+'_min']=np.where(d[tscol]>=0,(d[tscol]-d.signal_ts)/60.0,np.nan)
    d['confirm_min']=(d.entry_ts-d.signal_ts)/60.0
    d['signal_time_utc']=pd.to_datetime(d.signal_ts,unit='s',utc=True)
    return d

# ---------- paired counterfactual entries on SAME baseline G1 signals ----------
def evaluate_exit(ts,H,L,C,entry_idx,side,entry,atr):
    risk=SL*atr;sl=entry-side*risk;tp=entry+side*TP*atr
    xe=min(len(ts)-1,np.searchsorted(ts,ts[entry_idx]+HOLD,'left'))
    xp=C[xe];ex=xe
    for q in range(entry_idx+1,xe+1):
        sh=(side>0 and L[q]<=sl) or (side<0 and H[q]>=sl)
        th=(side>0 and H[q]>=tp) or (side<0 and L[q]<=tp)
        if sh:xp=sl;ex=q;break
        if th:xp=tp;ex=q;break
    rr=side*(xp-entry)/risk-(COST_BPS/10000.)*entry/risk
    return rr,int(ts[ex])

def paired_counterfactual(raw,audit):
    ts,O,H,L,C=raw
    rows=[]
    for _,r in audit.iterrows():
        base={'signal_ts':int(r.signal_ts),'baseline_R':float(r.R),'side':int(r.side),
              'signal_atr':float(r.signal_atr),'entry_move_atr':float(r.entry_move_atr),
              'pre_entry_mfe_atr':float(r.pre_entry_mfe_atr),'pre_entry_mae_atr':float(r.pre_entry_mae_atr)}
        # Early-entry oracle on already-known baseline G1 signals. Diagnostic only.
        for lv in EARLY_LEVELS:
            col=f'first_close_{int(lv*100):03d}_ts'
            ets=int(r[col])
            key=f'ORACLE_EARLY_{lv:.2f}'
            if ets<0:
                base[key+'_filled']=False;base[key+'_R']=np.nan
            else:
                ei=np.searchsorted(ts,ets,'left')
                entry=float(C[ei])
                rr,_=evaluate_exit(ts,H,L,C,ei,int(r.side),entry,float(r.signal_atr))
                base[key+'_filled']=True;base[key+'_R']=rr
        # Passive retrace after current 0.30 confirmation; causal once G1 is known.
        ci=np.searchsorted(ts,int(r.entry_ts),'left')
        confirm_px=float(C[ci])
        for rv in RETRACE_LEVELS:
            key=f'RETRACE_{rv:.2f}'
            limit=confirm_px-int(r.side)*rv*float(r.signal_atr)
            pe=np.searchsorted(ts,int(r.entry_ts)+RETRACE_TTL,'right')
            fill=-1
            for q in range(ci+1,min(len(ts),pe)):
                if (int(r.side)>0 and L[q]<=limit) or (int(r.side)<0 and H[q]>=limit):
                    fill=q;break
            if fill<0:
                base[key+'_filled']=False;base[key+'_R']=np.nan
            else:
                rr,_=evaluate_exit(ts,H,L,C,fill,int(r.side),limit,float(r.signal_atr))
                base[key+'_filled']=True;base[key+'_R']=rr
        rows.append(base)
    return pd.DataFrame(rows)

# ---------- causal stateful early-entry variants ----------
@njit(cache=True)
def causal_early(ts,O,H,L,C,dt5,C5,Z5,A5,H1,H4,confirm_atr):
    cap=len(dt5)
    R=np.zeros(cap);ST=np.zeros(cap,np.int64);ET=np.zeros(cap,np.int64);XT=np.zeros(cap,np.int64)
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

        ps=np.searchsorted(ts,t+1);pe=np.searchsorted(ts,t+FAST_CONFIRM_TTL,'right')
        ci=-1;maxcrowd=0.;maxthesis=0.
        target=sig+side*confirm_atr*siga
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

        align1=(H1[k]==side);align4=(H4[k]==side)
        one_align=(align1!=align4)
        response=maxthesis/(maxcrowd+1e-9)
        branch=g1_branch_nb(one_align,response)
        if branch==0:
            k=np.searchsorted(dt5,ts[ci])+1;continue

        entry=C[ci];ei=ci
        risk=SL*siga;sl=entry-side*risk;tp=entry+side*TP*siga
        xe=min(len(ts)-1,np.searchsorted(ts,ts[ei]+HOLD,'left'))
        xp=C[xe];ex=xe
        for q in range(ei+1,xe+1):
            sh=(side>0 and L[q]<=sl) or (side<0 and H[q]>=sl)
            th=(side>0 and H[q]>=tp) or (side<0 and L[q]<=tp)
            if sh:xp=sl;ex=q;break
            if th:xp=tp;ex=q;break
        rr=side*(xp-entry)/risk-(COST_BPS/10000.)*entry/risk
        R[n]=rr;ST[n]=t;ET[n]=ts[ei];XT[n]=ts[ex];n+=1
        dc+=1;last=entry;la=siga;has=True;nextts=ts[ex]+1;k=np.searchsorted(dt5,nextts)
    return R[:n],ST[:n],ET[:n],XT[:n]

# ---------- causal stateful retrace-after-0.30 variants ----------
@njit(cache=True)
def causal_retrace(ts,O,H,L,C,dt5,C5,Z5,A5,H1,H4,retrace_atr):
    cap=len(dt5)
    R=np.zeros(cap);ST=np.zeros(cap,np.int64);ET=np.zeros(cap,np.int64);XT=np.zeros(cap,np.int64)
    n=0;k=0;last=0.;la=0.;has=False;day=-1;dc=0;nextts=0;nofill=0
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

        ps=np.searchsorted(ts,t+1);pe=np.searchsorted(ts,t+FAST_CONFIRM_TTL,'right')
        ci=-1;maxcrowd=0.;maxthesis=0.
        target=sig+side*BASE_CONFIRM*siga
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

        align1=(H1[k]==side);align4=(H4[k]==side)
        one_align=(align1!=align4)
        response=maxthesis/(maxcrowd+1e-9)
        branch=g1_branch_nb(one_align,response)
        if branch==0:
            k=np.searchsorted(dt5,ts[ci])+1;continue

        confirm_px=C[ci]
        limit=confirm_px-side*retrace_atr*siga
        pend_end=ts[ci]+RETRACE_TTL
        pj=ci+1;fill=-1
        while pj<len(ts) and ts[pj]<=pend_end:
            if (side>0 and L[pj]<=limit) or (side<0 and H[pj]>=limit):
                fill=pj;break
            pj+=1
        if fill<0:
            nofill+=1
            k=np.searchsorted(dt5,ts[ci])+1
            continue

        entry=limit;ei=fill
        risk=SL*siga;sl=entry-side*risk;tp=entry+side*TP*siga
        xe=min(len(ts)-1,np.searchsorted(ts,ts[ei]+HOLD,'left'))
        xp=C[xe];ex=xe
        for q in range(ei+1,xe+1):
            sh=(side>0 and L[q]<=sl) or (side<0 and H[q]>=sl)
            th=(side>0 and H[q]>=tp) or (side<0 and L[q]<=tp)
            if sh:xp=sl;ex=q;break
            if th:xp=tp;ex=q;break
        rr=side*(xp-entry)/risk-(COST_BPS/10000.)*entry/risk
        R[n]=rr;ST[n]=t;ET[n]=ts[ei];XT[n]=ts[ex];n+=1
        dc+=1;last=entry;la=siga;has=True;nextts=ts[ex]+1;k=np.searchsorted(dt5,nextts)
    return R[:n],ST[:n],ET[:n],XT[:n],nofill

def seq_metrics(z,months):
    R=z[0]
    m=met(R);m['trades_per_month']=len(R)/months
    return m

def quantiles(s):
    a=pd.Series(s).dropna().to_numpy(float)
    if len(a)==0:return {}
    return {'N':int(len(a)),'mean':float(np.mean(a)),'median':float(np.median(a)),
            'p10':float(np.quantile(a,.10)),'p25':float(np.quantile(a,.25)),
            'p75':float(np.quantile(a,.75)),'p90':float(np.quantile(a,.90))}

def diagnostic_summary(d):
    return {
        'first_touch_0.10_min':quantiles(d.first_touch_010_min),
        'first_close_0.10_min':quantiles(d.first_close_010_min),
        'confirmation_0.30_min':quantiles(d.confirm_min),
        'entry_move_atr':quantiles(d.entry_move_atr),
        'pre_entry_mfe_atr':quantiles(d.pre_entry_mfe_atr),
        'pre_entry_mae_atr':quantiles(d.pre_entry_mae_atr)
    }

def outcome_bins(d):
    q=d.copy()
    q['result']=np.where(q.R>0,'WIN','LOSS_NONWIN')
    q['latency_bin']=pd.cut(q.confirm_min,[0,5,15,30,60,120,181],include_lowest=True,
                            labels=['<=5','5-15','15-30','30-60','60-120','120-180'])
    q['overshoot_bin']=pd.cut(q.entry_move_atr,[0,.32,.40,.50,.75,1.0,99],include_lowest=True,
                              labels=['0.30-.32','.32-.40','.40-.50','.50-.75','.75-1.0','>=1.0'])
    q['pre_mae_bin']=pd.cut(q.pre_entry_mae_atr,[0,.25,.50,1.0,1.5,99],include_lowest=True,
                            labels=['<.25','.25-.50','.50-1.0','1.0-1.5','>=1.5'])
    out={}
    for col in ['result','latency_bin','overshoot_bin','pre_mae_bin','branch']:
        out[col]={}
        for k,g in q.groupby(col,observed=False):
            if len(g):out[col][str(k)]=met(g.R.to_numpy(float))
    return out

def paired_cf_summary(cf):
    out={}
    for lv in EARLY_LEVELS:
        k=f'ORACLE_EARLY_{lv:.2f}'
        vals=cf.loc[cf[k+'_filled'],k+'_R'].dropna().to_numpy(float)
        out[k]={'metrics':met(vals),'fill_rate':float(cf[k+'_filled'].mean()),
                'paired_delta_vs_baseline_R':float((cf.loc[cf[k+'_filled'],k+'_R']-cf.loc[cf[k+'_filled'],'baseline_R']).sum())}
    for rv in RETRACE_LEVELS:
        k=f'RETRACE_{rv:.2f}'
        vals=cf.loc[cf[k+'_filled'],k+'_R'].dropna().to_numpy(float)
        out[k]={'metrics':met(vals),'fill_rate':float(cf[k+'_filled'].mean()),
                'paired_delta_vs_baseline_R':float((cf.loc[cf[k+'_filled'],k+'_R']-cf.loc[cf[k+'_filled'],'baseline_R']).sum())}
    return out

def run_period(raw,ft,fz,start,end,months,label):
    m5=lab041.prep_fast(raw,ft,fz,start,end)
    audit=audit_df(baseline_g1_audit(*m5))
    audit.to_csv(OUT/f'{label}_baseline_g1_lateness.csv',index=False)
    cf=paired_counterfactual(raw,audit)
    cf.to_csv(OUT/f'{label}_paired_counterfactuals.csv',index=False)

    causal_early_res={}
    for lv in EARLY_LEVELS:
        z=causal_early(*m5,lv)
        causal_early_res[f'{lv:.2f}']=seq_metrics(z,months)

    causal_retrace_res={}
    for rv in RETRACE_LEVELS:
        z=causal_retrace(*m5,rv)
        m=seq_metrics(z,months);m['no_fill']=int(z[-1])
        causal_retrace_res[f'{rv:.2f}']=m

    result={
        'baseline':seq_metrics((audit.R.to_numpy(float),),months),
        'diagnostics':diagnostic_summary(audit),
        'outcome_bins':outcome_bins(audit),
        'paired_counterfactuals':paired_cf_summary(cf),
        'causal_early_response':causal_early_res,
        'causal_retrace_after_030':causal_retrace_res
    }

    if label=='historical':
        y=audit.signal_time_utc.dt.year
        result['latency_by_year']={}
        for yr,g in audit.groupby(y):
            result['latency_by_year'][str(yr)]={'metrics':met(g.R.to_numpy(float)),'diagnostics':diagnostic_summary(g)}
        # 2025 H1/H2 targeted diagnostic, no filter promotion.
        d25=audit.loc[y==2025].copy()
        if len(d25):
            half=np.where(d25.signal_time_utc.dt.month<=6,'H1','H2')
            result['2025_halves']={}
            for h,g in d25.groupby(half):
                result['2025_halves'][h]={'metrics':met(g.R.to_numpy(float)),'diagnostics':diagnostic_summary(g)}
    else:
        result['latency_by_month']={}
        for mo,g in audit.groupby(audit.signal_time_utc.dt.strftime('%Y-%m')):
            result['latency_by_month'][str(mo)]={'metrics':met(g.R.to_numpy(float)),'diagnostics':diagnostic_summary(g)}

    return result

def main():
    ft,fz=lab041.load_flow()
    hraw=lab041.load_hist();fraw=lab041.load_sec()

    hist=run_period(hraw,ft,fz,
        int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),
        int(pd.Timestamp('2026-01-01',tz='UTC').timestamp()),60,'historical')
    fwd=run_period(fraw,ft,fz,
        int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),
        int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()),6,'forward')

    result={
      'lab':'LAB041C_FAST_ENTRY_LATENESS_AND_FIRST_RESPONSE_AUDIT',
      'baseline':'G1 ALLOW_ALL from LAB041/041B; FAST Z1.0-2.05; ONE_ALIGN; response 0.50-1.00 or >=2.50; market at first raw-close >=0.30 ATR; SL4.5/TP10/H24',
      'first_reversal_definition':'first raw close >= +0.10 signal ATR in trade direction; first H/L touch >=0.10 also recorded',
      'early_scenarios':'0.10/0.15/0.20/0.25/0.30 ATR. Paired ORACLE rows use later baseline-G1 membership and are diagnostic only; separate causal stateful reruns evaluate G1 using information available at each earlier threshold.',
      'retrace_scenarios':'after valid baseline-style 0.30 confirmation, passive limit 0.10/0.20/0.30 ATR back from confirmation price, TTL20m; full stateful rerun',
      'historical':hist,'forward':fwd,
      'limitations':[
        'Historical path is 1-minute OHLC; 2026 forward-shadow path is second OHLC, so latency precision differs.',
        '2026 Mar-Aug is reused forward-shadow, not pristine OOS.',
        'Paired early-entry counterfactuals are oracle diagnostics because baseline G1 membership is only known at the later 0.30 confirmation.',
        'Causal early-entry reruns avoid that lookahead but change G1 population and later sequence.',
        'Broker spread/slippage/freeze effects are represented only by flat research cost, not full MT5 execution.'
      ]
    }
    (OUT/'summary.json').write_text(json.dumps(result,indent=2))

    rows=[]
    for period,d in [('historical',hist),('2026',fwd)]:
        b=d['baseline']
        rows.append({'period':period,'family':'BASELINE','variant':'MARKET_0.30',
                     **{k:b[k] for k in ['N','EV','PF','SumR','MaxDD_R','R_DD','trades_per_month']}})
        for k,m in d['causal_early_response'].items():
            rows.append({'period':period,'family':'CAUSAL_EARLY','variant':k,
                         **{x:m[x] for x in ['N','EV','PF','SumR','MaxDD_R','R_DD','trades_per_month']}})
        for k,m in d['causal_retrace_after_030'].items():
            rows.append({'period':period,'family':'CAUSAL_RETRACE','variant':k,
                         **{x:m[x] for x in ['N','EV','PF','SumR','MaxDD_R','R_DD','trades_per_month']},
                         'no_fill':m['no_fill']})
    pd.DataFrame(rows).to_csv(OUT/'comparison.csv',index=False)

    lines=['# LAB041C — FAST_ENTRY_LATENESS_AND_FIRST_RESPONSE_AUDIT','',
           '## Baseline',f"- Hist: {fmt(hist['baseline'])}",f"- 2026: {fmt(fwd['baseline'])}",'',
           '## Lateness diagnostics',
           f"- Hist: {json.dumps(hist['diagnostics'])}",
           f"- 2026: {json.dumps(fwd['diagnostics'])}",'',
           '## Causal early-response stateful replay']
    for k in [f'{x:.2f}' for x in EARLY_LEVELS]:
        lines.append(f"- {k} ATR: hist {fmt(hist['causal_early_response'][k])} | 2026 {fmt(fwd['causal_early_response'][k])}")
    lines += ['','## Causal retrace after valid 0.30 confirmation']
    for k in [f'{x:.2f}' for x in RETRACE_LEVELS]:
        hm=hist['causal_retrace_after_030'][k];fm=fwd['causal_retrace_after_030'][k]
        lines.append(f"- retrace {k}: hist {fmt(hm)} noFill={hm['no_fill']} | 2026 {fmt(fm)} noFill={fm['no_fill']}")
    lines += ['','## 2025 halves',json.dumps(hist.get('2025_halves',{}),indent=2),'',
              '## Paired oracle diagnostics',json.dumps({'historical':hist['paired_counterfactuals'],'forward':fwd['paired_counterfactuals']},indent=2),'',
              '## Limitations']+[f"- {x}" for x in result['limitations']]
    (OUT/'REPORT.md').write_text('\n'.join(lines))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__':
    main()
