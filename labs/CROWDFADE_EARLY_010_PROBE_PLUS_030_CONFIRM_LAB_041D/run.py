from pathlib import Path
import json, importlib.util
import numpy as np
import pandas as pd
from numba import njit

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'
OUT=ROOT/'output'
OUT.mkdir(parents=True,exist_ok=True)

# Reuse LAB041 exact loaders / FAST prep / metrics.
_lab041_path=Path(__file__).resolve().parents[1]/'CROWDFADE_FAST_LANE_COMPOSITE_GATE_PORTFOLIO_LAB_041'/'run.py'
_spec=importlib.util.spec_from_file_location('lab041_core_fast',_lab041_path)
lab041=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lab041)
lab041.DATA=DATA
core=lab041.core

FAST_Z_LO=lab041.FAST_Z_LO
FAST_Z_HI=lab041.FAST_Z_HI
FAST_PAUSE_ATR=lab041.FAST_PAUSE_ATR
MAXDAY=lab041.MAXDAY
COST_BPS=lab041.COST_BPS

PROBE_ATR=0.10
CONFIRM_ATR=0.30
CONFIRM_TTL=10800
PROBE_WEIGHT=0.20
CONFIRM_WEIGHT=0.80
SL=4.5
TP=10.0
HOLD=86400

@njit(cache=True)
def g1_branch(one_align,response):
    if not one_align:
        return 0
    if response>=0.50 and response<1.00:
        return 1
    if response>=2.50:
        return 2
    return 0

@njit(cache=True)
def tranche_exit(ts,H,L,C,entry_idx,side,entry,atr,hold_sec):
    risk=SL*atr
    sl=entry-side*risk
    tp=entry+side*TP*atr
    xe=min(len(ts)-1,np.searchsorted(ts,ts[entry_idx]+hold_sec,'left'))
    xp=C[xe];ex=xe;reason=0
    for q in range(entry_idx+1,xe+1):
        sh=(side>0 and L[q]<=sl) or (side<0 and H[q]>=sl)
        th=(side>0 and H[q]>=tp) or (side<0 and L[q]<=tp)
        if sh:
            xp=sl;ex=q;reason=-1;break
        if th:
            xp=tp;ex=q;reason=1;break
    rr=side*(xp-entry)/risk-(COST_BPS/10000.)*entry/risk
    return rr,ex,reason

@njit(cache=True)
def baseline_030(ts,O,H,L,C,dt5,C5,Z5,A5,H1,H4):
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

        ps=np.searchsorted(ts,t+1);pe=np.searchsorted(ts,t+CONFIRM_TTL,'right')
        ci=-1;maxcrowd=0.;maxthesis=0.
        target=sig+side*CONFIRM_ATR*siga
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
        if g1_branch(one_align,response)==0:
            k=np.searchsorted(dt5,ts[ci])+1;continue

        entry=C[ci]
        rr,ex,_=tranche_exit(ts,H,L,C,ci,side,entry,siga,HOLD)
        R[n]=rr;ST[n]=t;ET[n]=ts[ci];XT[n]=ts[ex];n+=1
        dc+=1;last=entry;la=siga;has=True;nextts=ts[ex]+1;k=np.searchsorted(dt5,nextts)
    return R[:n],ST[:n],ET[:n],XT[:n]

@njit(cache=True)
def staged_010_030(ts,O,H,L,C,dt5,C5,Z5,A5,H1,H4):
    cap=len(dt5)
    WR=np.zeros(cap);ST=np.zeros(cap,np.int64);PET=np.zeros(cap,np.int64);CET=np.zeros(cap,np.int64);XT=np.zeros(cap,np.int64)
    PROBER=np.zeros(cap);CONFR=np.zeros(cap);CONFIRMED=np.zeros(cap,np.int8);REASON=np.zeros(cap,np.int8)
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

        ps=np.searchsorted(ts,t+1);pe=np.searchsorted(ts,t+CONFIRM_TTL,'right')
        probe=-1;confirm=-1
        maxcrowd=0.;maxthesis=0.

        # Phase 1: first causal +0.10 close where early G1 is already valid.
        for q in range(ps,min(len(ts),pe)):
            crowd_exc=((H[q]-sig) if side<0 else (sig-L[q]))/siga
            thesis_exc=((sig-L[q]) if side<0 else (H[q]-sig))/siga
            if crowd_exc>maxcrowd:maxcrowd=crowd_exc
            if thesis_exc>maxthesis:maxthesis=thesis_exc

            favclose=side*(C[q]-sig)/siga
            if favclose>=PROBE_ATR:
                zk=np.searchsorted(dt5,ts[q],'right')-1
                if zk>=0 and z*Z5[zk]>=0.0:
                    align1=(H1[k]==side);align4=(H4[k]==side)
                    one_align=(align1!=align4)
                    response=maxthesis/(maxcrowd+1e-9)
                    if g1_branch(one_align,response)!=0:
                        probe=q;break
        if probe<0:
            k+=1;continue

        probe_entry=C[probe]
        # Probe protective levels are active while waiting.
        probe_risk=SL*siga
        probe_sl=probe_entry-side*probe_risk
        probe_tp=probe_entry+side*TP*siga

        # Phase 2: from probe to +0.30 confirm, watching sign-flip/timeout/protective exit.
        q=probe+1
        terminal=-1
        term_reason=0   # 1 confirm, -1 flip, -2 timeout, -3 probe SL, +3 probe TP
        while q<len(ts) and ts[q]<=t+CONFIRM_TTL:
            # protective probe exit first
            sh=(side>0 and L[q]<=probe_sl) or (side<0 and H[q]>=probe_sl)
            th=(side>0 and H[q]>=probe_tp) or (side<0 and L[q]<=probe_tp)
            if sh:
                terminal=q;term_reason=-3;break
            if th:
                terminal=q;term_reason=3;break

            crowd_exc=((H[q]-sig) if side<0 else (sig-L[q]))/siga
            thesis_exc=((sig-L[q]) if side<0 else (H[q]-sig))/siga
            if crowd_exc>maxcrowd:maxcrowd=crowd_exc
            if thesis_exc>maxthesis:maxthesis=thesis_exc

            zk=np.searchsorted(dt5,ts[q],'right')-1
            if zk>=0 and z*Z5[zk]<0.0:
                terminal=q;term_reason=-1;break

            favclose=side*(C[q]-sig)/siga
            if favclose>=CONFIRM_ATR:
                if zk>=0:
                    align1=(H1[k]==side);align4=(H4[k]==side)
                    one_align=(align1!=align4)
                    response=maxthesis/(maxcrowd+1e-9)
                    if g1_branch(one_align,response)!=0:
                        terminal=q;term_reason=1;confirm=q;break
            q+=1

        if terminal<0:
            terminal=min(len(ts)-1,np.searchsorted(ts,t+CONFIRM_TTL,'right')-1)
            term_reason=-2

        probe_rr=0.;confirm_rr=0.;final_ex=terminal
        confirmed=0

        if term_reason==1:
            confirmed=1
            # Probe continues independently from original probe entry.
            prr,pex,_=tranche_exit(ts,H,L,C,probe,side,probe_entry,siga,HOLD)

            confirm_entry=C[confirm]
            crr,cex,_=tranche_exit(ts,H,L,C,confirm,side,confirm_entry,siga,HOLD)

            probe_rr=prr
            confirm_rr=crr
            final_ex=pex if pex>cex else cex
            weighted=PROBE_WEIGHT*probe_rr+CONFIRM_WEIGHT*confirm_rr
        else:
            # No 0.30 confirmation. Close probe immediately at market at terminal event.
            exit_px=C[terminal]
            probe_rr=side*(exit_px-probe_entry)/probe_risk-(COST_BPS/10000.)*probe_entry/probe_risk
            weighted=PROBE_WEIGHT*probe_rr
            confirm_rr=0.

        WR[n]=weighted;ST[n]=t;PET[n]=ts[probe];CET[n]=ts[confirm] if confirm>=0 else 0;XT[n]=ts[final_ex]
        PROBER[n]=probe_rr;CONFR[n]=confirm_rr;CONFIRMED[n]=confirmed;REASON[n]=term_reason;n+=1

        dc+=1
        last=probe_entry
        la=siga
        has=True
        nextts=ts[final_ex]+1
        k=np.searchsorted(dt5,nextts)

    return (WR[:n],ST[:n],PET[:n],CET[:n],XT[:n],PROBER[:n],CONFR[:n],CONFIRMED[:n],REASON[:n])

def seq_df_baseline(z):
    R,st,et,xt=z
    return pd.DataFrame({'R':R,'signal_ts':st,'entry_ts':et,'exit_ts':xt})

def seq_df_staged(z):
    wr,st,pet,cet,xt,pr,cr,cf,rs=z
    reason=np.where(rs==1,'CONFIRMED',np.where(rs==-1,'SIGN_FLIP',np.where(rs==-2,'TIMEOUT',np.where(rs==-3,'PROBE_SL','PROBE_TP'))))
    return pd.DataFrame({'R':wr,'signal_ts':st,'probe_entry_ts':pet,'confirm_entry_ts':cet,'exit_ts':xt,
                         'probe_R':pr,'confirm_R':cr,'confirmed':cf.astype(bool),'terminal_reason':reason})

def metrics_df(df):
    m=core.metrics(df.R.to_numpy(float))
    return m

def split_metrics(df,mode):
    t=pd.to_datetime(df.signal_ts,unit='s',utc=True)
    if mode=='year':
        key=t.dt.year.astype(str)
    elif mode=='month':
        key=t.dt.strftime('%Y-%m')
    else:
        key=np.where((t.dt.year==2025)&(t.dt.month<=6),'2025_H1',
             np.where((t.dt.year==2025)&(t.dt.month>=7),'2025_H2','OTHER'))
    out={}
    for k,g in df.groupby(key):
        if str(k)!='OTHER':
            out[str(k)]=metrics_df(g)
    return out

def confirmed_stats(df):
    return {
      'N':int(len(df)),
      'confirmed_N':int(df.confirmed.sum()),
      'confirm_rate':float(df.confirmed.mean()) if len(df) else 0.,
      'terminal_reason_counts':{str(k):int(v) for k,v in df.terminal_reason.value_counts().items()},
      'probe_only_sumR':float((0.20*df.probe_R).sum()),
      'confirm_component_sumR':float((0.80*df.confirm_R).sum())
    }

def run_period(raw,ft,fz,start,end,label):
    m5=lab041.prep_fast(raw,ft,fz,start,end)
    bdf=seq_df_baseline(baseline_030(*m5))
    sdf=seq_df_staged(staged_010_030(*m5))
    bdf.to_csv(OUT/f'{label}_baseline_030.csv',index=False)
    sdf.to_csv(OUT/f'{label}_staged_010_030.csv',index=False)

    return {
      'baseline':metrics_df(bdf),
      'staged':metrics_df(sdf),
      'baseline_periods':split_metrics(bdf,'year' if label=='historical' else 'month'),
      'staged_periods':split_metrics(sdf,'year' if label=='historical' else 'month'),
      'baseline_2025_halves':split_metrics(bdf,'half') if label=='historical' else {},
      'staged_2025_halves':split_metrics(sdf,'half') if label=='historical' else {},
      'staged_execution':confirmed_stats(sdf)
    }

def fmt(m):
    return f"N={m['N']} EV={m['EV']:+.4f} PF={m['PF']:.3f} Sum={m['SumR']:+.2f}R DD={m['MaxDD_R']:.2f} R/DD={m['R_DD']:.3f}"

def main():
    ft,fz=lab041.load_flow()
    hraw=lab041.load_hist();fraw=lab041.load_sec()

    hist=run_period(hraw,ft,fz,
        int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),
        int(pd.Timestamp('2026-01-01',tz='UTC').timestamp()),'historical')
    fwd=run_period(fraw,ft,fz,
        int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),
        int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()),'forward')

    result={
      'lab':'LAB041D_EARLY_010_PROBE_PLUS_030_CONFIRM',
      'staged_rule':{
        'probe':'20% FAST risk at first causal +0.10 ATR close where early G1 is valid',
        'confirm':'add 80% FAST risk at +0.30 ATR only if sign unchanged and full G1 remains valid',
        'probe_abort':'close probe at market on crowd sign-flip or 3h timeout before confirmation',
        'risk_management':'probe and confirm tranches each use SL4.5 / TP10 / H24 from their own entry; weighted trade R = 0.20*probe_R + 0.80*confirm_R'
      },
      'historical':hist,'forward':fwd,
      'limitations':[
        'BTC only.',
        'Historical path is 1-minute OHLC; 2026 uses second data, so sub-minute staged timing is more precise in 2026.',
        '2026 Mar-Aug is reused forward-shadow, not pristine OOS.',
        'Early probe uses only causal early-G1 information; no later 0.30 membership is used to decide the probe.',
        'Two tranches are modeled independently after confirmation; a future EA may need net-position implementation details depending on broker/account mode.',
        'Flat research cost only; exact spread/slippage/freeze behavior still requires forward execution audit.'
      ]
    }
    (OUT/'summary.json').write_text(json.dumps(result,indent=2))

    rows=[]
    for period,d in [('historical',hist),('2026',fwd)]:
        for name in ['baseline','staged']:
            m=d[name]
            rows.append({'period':period,'variant':name,**{k:m[k] for k in ['N','EV','PF','SumR','MaxDD_R','R_DD','MaxConsecutiveLosses']}})
    pd.DataFrame(rows).to_csv(OUT/'comparison.csv',index=False)

    lines=['# LAB041D — EARLY_010_PROBE_PLUS_030_CONFIRM','',
           '20% FAST risk at +0.10 ATR causal early-G1; 80% added at +0.30 ATR only if full G1 confirms.','',
           '## Full sample',
           f"- Historical baseline 0.30: {fmt(hist['baseline'])}",
           f"- Historical staged 20/80: {fmt(hist['staged'])}",
           f"- 2026 baseline 0.30: {fmt(fwd['baseline'])}",
           f"- 2026 staged 20/80: {fmt(fwd['staged'])}",'',
           '## 2025 H1/H2',
           f"- baseline: {json.dumps(hist['baseline_2025_halves'])}",
           f"- staged: {json.dumps(hist['staged_2025_halves'])}",'',
           '## Staged execution',
           f"- historical: {json.dumps(hist['staged_execution'])}",
           f"- 2026: {json.dumps(fwd['staged_execution'])}",'',
           '## Historical by year',json.dumps({'baseline':hist['baseline_periods'],'staged':hist['staged_periods']},indent=2),'',
           '## 2026 by month',json.dumps({'baseline':fwd['baseline_periods'],'staged':fwd['staged_periods']},indent=2),'',
           '## Limitations']+[f"- {x}" for x in result['limitations']]
    (OUT/'REPORT.md').write_text('\n'.join(lines))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__':
    main()
