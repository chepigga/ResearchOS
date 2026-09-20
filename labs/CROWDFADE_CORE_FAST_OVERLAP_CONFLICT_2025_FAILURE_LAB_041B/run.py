from pathlib import Path
import json, zipfile, importlib.util
import numpy as np
import pandas as pd
from numba import njit

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'
OUT=ROOT/'output'
OUT.mkdir(parents=True,exist_ok=True)

# Reuse LAB041 exact lineage for loaders, CORE, metrics and portfolio semantics.
_lab041_path=Path(__file__).resolve().parents[1]/'CROWDFADE_FAST_LANE_COMPOSITE_GATE_PORTFOLIO_LAB_041'/'run.py'
_spec=importlib.util.spec_from_file_location('lab041_core_fast',_lab041_path)
lab041=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lab041)

core=lab041.core

# G1 frozen from LAB041.
FAST_Z_LO=lab041.FAST_Z_LO
FAST_Z_HI=lab041.FAST_Z_HI
FAST_CONFIRM=lab041.FAST_CONFIRM
FAST_CONFIRM_TTL=lab041.FAST_CONFIRM_TTL
FAST_PAUSE_ATR=lab041.FAST_PAUSE_ATR
FAST_SL=lab041.FAST_SL
FAST_TP=lab041.FAST_TP
FAST_HOLD=lab041.FAST_HOLD
MAXDAY=lab041.MAXDAY
COST_BPS=lab041.COST_BPS

# Conflict policies (entry-time only; CORE always has priority and is never blocked):
# 0 ALLOW_ALL
# 1 BLOCK_ANY_CORE_OPEN
# 2 BLOCK_OPPOSITE_CORE_OPEN (no hedge at FAST entry; same-side stacking allowed)
# 3 BLOCK_SAME_SIDE_CORE_OPEN (diagnostic: no pyramiding; opposite overlap allowed)
POLICIES={
    0:'ALLOW_ALL',
    1:'BLOCK_ANY_CORE_OPEN',
    2:'BLOCK_OPPOSITE_CORE_OPEN',
    3:'BLOCK_SAME_SIDE_CORE_OPEN'
}

def active_core_at(t,centry,cexit,cside):
    # Python audit helper. CORE lane is sequential and sorted.
    i=np.searchsorted(centry,t,side='right')-1
    if i>=0 and centry[i] <= t < cexit[i]:
        return int(cside[i]), int(i)
    return 0,-1

@njit(cache=True)
def fast_g1_conflict(ts,O,H,L,C,dt5,C5,Z5,A5,H1,H4,
                     centry,cexit,cside,policy):
    cap=len(dt5)
    R=np.zeros(cap);ST=np.zeros(cap,np.int64);ET=np.zeros(cap,np.int64);XT=np.zeros(cap,np.int64)
    SIDE=np.zeros(cap,np.int8);RESP=np.zeros(cap);CMIN=np.zeros(cap);ABSZ=np.zeros(cap)
    BRANCH=np.zeros(cap,np.int8);ALIGNTF=np.zeros(cap,np.int8)
    ENTRYOV=np.zeros(cap,np.int8)
    n=0;k=0;last=0.;la=0.;has=False;day=-1;dc=0;nextts=0
    blocked_any=0;blocked_same=0;blocked_opp=0

    while k<len(dt5)-3:
        t=dt5[k]
        if t<nextts:
            k+=1;continue
        d=t//86400
        if d!=day:
            day=d;dc=0
        if dc>=MAXDAY:
            k+=1;continue

        z=Z5[k];az=abs(z)
        if az<FAST_Z_LO or az>=FAST_Z_HI:
            k+=1;continue
        side=-1 if z>0 else 1
        sig=C5[k];siga=A5[k]
        if has and abs(sig-last)<FAST_PAUSE_ATR*la:
            k+=1;continue

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
        if ci<0:
            k+=1;continue

        zk=np.searchsorted(dt5,ts[ci],'right')-1
        if zk<0:
            k+=1;continue
        if z*Z5[zk]<0.0:
            k=np.searchsorted(dt5,ts[ci])+1
            continue

        entry=C[ci]
        confirm_min=(ts[ci]-t)/60.0
        response=maxthesis/(maxcrowd+1e-9)

        # Exact G1: ONE_ALIGN + response 0.50-1.00 OR >=2.50.
        align1=(H1[k]==side)
        align4=(H4[k]==side)
        one_align=(align1!=align4)
        branch=0
        if response>=0.50 and response<1.00:
            branch=1
        elif response>=2.50:
            branch=2
        if (not one_align) or branch==0:
            k=np.searchsorted(dt5,ts[ci])+1
            continue

        align_tf=1 if align1 else 2  # 1=H1 aligned, 2=H4 aligned

        # Conflict state at FAST entry.
        oi=np.searchsorted(centry,ts[ci],'right')-1
        ov=0
        if oi>=0 and centry[oi] <= ts[ci] and ts[ci] < cexit[oi]:
            if cside[oi]==side:ov=1   # same-side CORE overlap
            else:ov=-1                # opposite-side CORE overlap

        block=False
        if policy==1 and ov!=0:block=True
        elif policy==2 and ov==-1:block=True
        elif policy==3 and ov==1:block=True
        if block:
            blocked_any+=1
            if ov==1:blocked_same+=1
            elif ov==-1:blocked_opp+=1
            # Blocked FAST does not consume pause/day quota/occupancy.
            k=np.searchsorted(dt5,ts[ci])+1
            continue

        ei=ci
        risk=FAST_SL*siga;sl=entry-side*risk;tp=entry+side*FAST_TP*siga
        xe=min(len(ts)-1,np.searchsorted(ts,ts[ei]+FAST_HOLD,'left'))
        xp=C[xe];ex=xe
        for q in range(ei+1,xe+1):
            sh=(side>0 and L[q]<=sl) or (side<0 and H[q]>=sl)
            th=(side>0 and H[q]>=tp) or (side<0 and L[q]<=tp)
            if sh:
                xp=sl;ex=q;break
            if th:
                xp=tp;ex=q;break

        rr=side*(xp-entry)/risk-(COST_BPS/10000.)*entry/risk
        R[n]=rr;ST[n]=t;ET[n]=ts[ei];XT[n]=ts[ex];SIDE[n]=side
        RESP[n]=response;CMIN[n]=confirm_min;ABSZ[n]=az;BRANCH[n]=branch;ALIGNTF[n]=align_tf;ENTRYOV[n]=ov
        n+=1

        dc+=1;last=entry;la=siga;has=True;nextts=ts[ex]+1;k=np.searchsorted(dt5,nextts)

    return (R[:n],ST[:n],ET[:n],XT[:n],SIDE[:n],RESP[:n],CMIN[:n],ABSZ[:n],
            BRANCH[:n],ALIGNTF[:n],ENTRYOV[:n],blocked_any,blocked_same,blocked_opp)

def fast_df(z,policy_name):
    R,st,et,xt,side,resp,cmin,az,branch,align_tf,entry_ov,bany,bsame,bopp=z
    d=pd.DataFrame({
        'R':R,'signal_ts':st,'entry_ts':et,'exit_ts':xt,'side':side,
        'response_ratio':resp,'confirm_min':cmin,'abs_z':az,
        'branch':np.where(branch==1,'MID_RESPONSE_0.50_1.00','STRONG_RESPONSE_GE_2.50'),
        'align_tf':np.where(align_tf==1,'H1_ALIGN','H4_ALIGN'),
        'entry_overlap':np.where(entry_ov==1,'CORE_SAME',np.where(entry_ov==-1,'CORE_OPPOSITE','NONE')),
        'lane':'G1_RESPONSE','policy':policy_name
    })
    meta={'blocked_any':int(bany),'blocked_same':int(bsame),'blocked_opposite':int(bopp)}
    return d,meta

def met(x):
    return core.metrics(np.asarray(x,float))

def lane_metrics(df,months):
    m=met(df.R.to_numpy(float));m['trades_per_month']=len(df)/months;return m

def portfolio(core_df,fast_df,fast_mult,months):
    return lab041.portfolio(core_df,fast_df,fast_mult,months)

def interval_overlap_audit(cdf,fdf):
    # Full interval audit for ALLOW_ALL accepted FAST trades.
    centry=cdf.entry_ts.to_numpy(np.int64);cexit=cdf.exit_ts.to_numpy(np.int64);cside=cdf.side.to_numpy(np.int8)
    rows=[]
    for _,r in fdf.iterrows():
        fe=int(r.entry_ts);fx=int(r.exit_ts);fs=int(r.side)
        # all CORE intervals overlapping FAST lifetime, not just at FAST entry
        ix=np.flatnonzero((centry<fx)&(cexit>fe))
        anyov=len(ix)>0
        same=sum(int(cside[i])==fs for i in ix)
        opp=sum(int(cside[i])!=fs for i in ix)
        later_opp=sum((centry[i]>fe) and (int(cside[i])!=fs) for i in ix)
        later_same=sum((centry[i]>fe) and (int(cside[i])==fs) for i in ix)
        rows.append({
            'signal_ts':int(r.signal_ts),'entry_ts':fe,'exit_ts':fx,'side':fs,'R':float(r.R),
            'entry_overlap':r.entry_overlap,'any_lifetime_overlap':anyov,
            'same_core_overlap_count':int(same),'opposite_core_overlap_count':int(opp),
            'later_core_same_entries':int(later_same),'later_core_opposite_entries':int(later_opp),
            'branch':r.branch,'align_tf':r.align_tf,'response_ratio':float(r.response_ratio),
            'confirm_min':float(r.confirm_min),'abs_z':float(r.abs_z)
        })
    return pd.DataFrame(rows)

def breakdown(df,col):
    out={}
    for k,g in df.groupby(col,dropna=False):
        out[str(k)]=met(g.R.to_numpy(float))
    return out

def year_month(df,mode):
    t=pd.to_datetime(df.signal_ts,unit='s',utc=True)
    key=t.dt.year.astype(str) if mode=='year' else t.dt.strftime('%Y-%m')
    out={}
    for k,g in df.groupby(key):
        out[str(k)]=met(g.R.to_numpy(float))
    return out

def failure_2025_audit(fdf,overlap_df):
    t=pd.to_datetime(fdf.signal_ts,unit='s',utc=True)
    d=fdf.loc[t.dt.year==2025].copy()
    od=overlap_df.loc[pd.to_datetime(overlap_df.signal_ts,unit='s',utc=True).dt.year==2025].copy()
    d['month']=pd.to_datetime(d.signal_ts,unit='s',utc=True).dt.strftime('%Y-%m')
    d['direction']=np.where(d.side>0,'BUY','SELL')
    d['z_band']=pd.cut(d.abs_z,[1.0,1.25,1.50,1.75,2.05],right=False,
                       labels=['1.00-1.25','1.25-1.50','1.50-1.75','1.75-2.05'])
    d['confirm_bin']=pd.cut(d.confirm_min,[0,15,30,60,120,181],right=True,include_lowest=True,
                            labels=['<=15','15-30','30-60','60-120','120-180'])
    return {
        'overall':met(d.R.to_numpy(float)),
        'month':breakdown(d,'month'),
        'direction':breakdown(d,'direction'),
        'branch':breakdown(d,'branch'),
        'align_tf':breakdown(d,'align_tf'),
        'entry_overlap':breakdown(d,'entry_overlap'),
        'lifetime_overlap':breakdown(od,'any_lifetime_overlap'),
        'z_band':breakdown(d,'z_band'),
        'confirm_speed':breakdown(d,'confirm_bin')
    }

def policy_run(raw,ft,fz,start,end,months,label):
    m15=core.prep(raw,ft,fz,start,end)
    m5=lab041.prep_fast(raw,ft,fz,start,end)
    cdf=lab041.df_core(lab041.core_events(*m15))
    centry=cdf.entry_ts.to_numpy(np.int64);cexit=cdf.exit_ts.to_numpy(np.int64);cside=cdf.side.to_numpy(np.int8)

    result={'CORE':lane_metrics(cdf,months),'policies':{},'portfolios':{}}
    fdfs={}
    for pid,pname in POLICIES.items():
        z=fast_g1_conflict(*m5,centry,cexit,cside,pid)
        fdf,meta=fast_df(z,pname)
        fdfs[pname]=fdf
        lm=lane_metrics(fdf,months)
        lm['blocked']=meta
        lm['periods']=year_month(fdf,'year' if label=='historical' else 'month')
        result['policies'][pname]=lm
        fdf.to_csv(OUT/f'{label}_{pname}_FAST.csv',index=False)
        for mult in [0.25,0.40]:
            k=f'{pname}_RISK{mult:.2f}'
            pm,pdf=portfolio(cdf,fdf,mult,months)
            result['portfolios'][k]=pm
            pdf.to_csv(OUT/f'{label}_{k}_portfolio.csv',index=False)

    # Detailed overlap audit is based on ALLOW_ALL.
    ov=interval_overlap_audit(cdf,fdfs['ALLOW_ALL'])
    ov.to_csv(OUT/f'{label}_ALLOW_ALL_overlap_audit.csv',index=False)
    result['overlap_audit']={
        'entry_overlap':breakdown(fdfs['ALLOW_ALL'],'entry_overlap'),
        'lifetime_any_overlap':breakdown(ov,'any_lifetime_overlap'),
        'counts':{
            'fast_total':int(len(ov)),
            'entry_none':int((ov.entry_overlap=='NONE').sum()),
            'entry_same':int((ov.entry_overlap=='CORE_SAME').sum()),
            'entry_opposite':int((ov.entry_overlap=='CORE_OPPOSITE').sum()),
            'lifetime_any':int(ov.any_lifetime_overlap.sum()),
            'later_core_same':int((ov.later_core_same_entries>0).sum()),
            'later_core_opposite':int((ov.later_core_opposite_entries>0).sum())
        }
    }
    if label=='historical':
        result['failure_2025']=failure_2025_audit(fdfs['ALLOW_ALL'],ov)
    cdf.to_csv(OUT/f'{label}_CORE.csv',index=False)
    return result

def promotion_checks(hist,fwd):
    # Compare stricter policies to the LAB041 ALLOW_ALL G1@0.25 preferred candidate.
    base_h=hist['portfolios']['ALLOW_ALL_RISK0.25']
    base_f=fwd['portfolios']['ALLOW_ALL_RISK0.25']
    out={}
    for pname in ['BLOCK_ANY_CORE_OPEN','BLOCK_OPPOSITE_CORE_OPEN','BLOCK_SAME_SIDE_CORE_OPEN']:
        for mult in [0.25,0.40]:
            k=f'{pname}_RISK{mult:.2f}'
            hm=hist['portfolios'][k];fm=fwd['portfolios'][k]
            fast_h=hist['policies'][pname];fast_f=fwd['policies'][pname]
            checks={
                'historical_sum_not_below_allow025':bool(hm['SumR']>=base_h['SumR']),
                'historical_rdd_not_below_allow025':bool(hm['R_DD']>=base_h['R_DD']),
                'forward_sum_not_below_allow025':bool(fm['SumR']>=base_f['SumR']),
                'forward_rdd_not_below_allow025':bool(fm['R_DD']>=base_f['R_DD']),
                'fast_hist_ev_nonnegative':bool(fast_h['EV']>=0),
                'fast_2026_ev_positive':bool(fast_f['EV']>0),
                'frequency_still_above_core_35pm':bool(fm['trades_per_month']>=35.0),
                'max_risk_le_1_40':bool(max(hm['max_concurrent_risk_units'],fm['max_concurrent_risk_units'])<=1.40)
            }
            out[k]={'checks':checks,'pass':bool(all(checks.values()))}
    return out

def fmt(m):
    n=m.get('N',m.get('trades',0))
    return f"N={n} ({m.get('trades_per_month',0):.1f}/mo) EV={m['EV']:+.4f} PF={m['PF']:.3f} Sum={m['SumR']:+.2f}R DD={m['MaxDD_R']:.2f} R/DD={m['R_DD']:.3f}"

def main():
    ft,fz=lab041.load_flow()
    hraw=lab041.load_hist();fraw=lab041.load_sec()

    hist=policy_run(hraw,ft,fz,int(pd.Timestamp('2021-01-01',tz='UTC').timestamp()),
                    int(pd.Timestamp('2026-01-01',tz='UTC').timestamp()),60,'historical')
    fwd=policy_run(fraw,ft,fz,int(pd.Timestamp('2026-03-01',tz='UTC').timestamp()),
                   int(pd.Timestamp('2026-09-01',tz='UTC').timestamp()),6,'forward')

    checks=promotion_checks(hist,fwd)

    result={
        'lab':'LAB041B_CORE_FAST_OVERLAP_CONFLICT_AND_2025_FAILURE_AUDIT',
        'frozen_g1':'ONE_ALIGN AND (response 0.50-1.00 OR response>=2.50); exact LAB041 entry/exit geometry',
        'conflict_policies':POLICIES,
        'historical':hist,'forward':fwd,
        'stricter_policy_promotion_checks':checks,
        'limitations':[
            'BTC only.',
            '2026 Mar-Aug is reused forward-shadow, not pristine OOS.',
            'Conflict policies act only when a FAST entry is about to occur; CORE is never blocked.',
            'Later CORE entries during an already-open FAST trade are audited but not force-closed in this LAB.',
            '2025 decomposition is diagnostic only. No new failure-regime filter is promoted from this audit.',
            'FAST confirmation retains LAB039/LAB040 first-raw-close approximation to live timer/quote behavior.'
        ]
    }
    (OUT/'summary.json').write_text(json.dumps(result,indent=2))

    rows=[]
    for period,d in [('historical',hist),('2026',fwd)]:
        rows.append({'period':period,'variant':'CORE',**{x:d['CORE'][x] for x in ['N','trades_per_month','EV','PF','SumR','MaxDD_R','R_DD']}})
        for p,m in d['policies'].items():
            rows.append({'period':period,'variant':p+'_FAST',**{x:m[x] for x in ['N','trades_per_month','EV','PF','SumR','MaxDD_R','R_DD']}})
        for p,m in d['portfolios'].items():
            rows.append({'period':period,'variant':p,'N':m['trades'],'trades_per_month':m['trades_per_month'],
                         'EV':m['EV'],'PF':m['PF'],'SumR':m['SumR'],'MaxDD_R':m['MaxDD_R'],'R_DD':m['R_DD'],
                         'max_concurrent_risk_units':m['max_concurrent_risk_units']})
    pd.DataFrame(rows).to_csv(OUT/'comparison.csv',index=False)

    lines=['# LAB041B — CORE_FAST_OVERLAP_CONFLICT_AND_2025_FAILURE_AUDIT','',
           'G1 is frozen. No new alpha filter is selected in this audit.','',
           '## Entry/lifetime overlap — ALLOW_ALL',
           json.dumps({'historical':hist['overlap_audit'],'forward':fwd['overlap_audit']},indent=2),'',
           '## FAST conflict policies']
    for p in POLICIES.values():
        lines.append(f"- {p}: hist {fmt(hist['policies'][p])} | 2026 {fmt(fwd['policies'][p])}")
    lines += ['','## Portfolio @ 0.25x FAST']
    for p in POLICIES.values():
        k=p+'_RISK0.25'
        lines.append(f"- {p}: hist {fmt(hist['portfolios'][k])} maxRisk={hist['portfolios'][k]['max_concurrent_risk_units']:.2f}u | 2026 {fmt(fwd['portfolios'][k])} maxRisk={fwd['portfolios'][k]['max_concurrent_risk_units']:.2f}u")
    lines += ['','## Portfolio @ 0.40x FAST']
    for p in POLICIES.values():
        k=p+'_RISK0.40'
        lines.append(f"- {p}: hist {fmt(hist['portfolios'][k])} maxRisk={hist['portfolios'][k]['max_concurrent_risk_units']:.2f}u | 2026 {fmt(fwd['portfolios'][k])} maxRisk={fwd['portfolios'][k]['max_concurrent_risk_units']:.2f}u")
    lines += ['','## 2025 failure audit',json.dumps(hist['failure_2025'],indent=2),'',
              '## Stricter policy promotion checks',json.dumps(checks,indent=2),'',
              '## Limitations']+[f"- {x}" for x in result['limitations']]
    (OUT/'REPORT.md').write_text('\n'.join(lines))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__':
    main()
