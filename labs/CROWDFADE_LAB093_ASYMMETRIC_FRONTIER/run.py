from pathlib import Path
import json, numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)
SRC=ROOT.parent/'CROWDFADE_LAB089_FREQUENCY_FRONTIER_LAB_092'/'output'/'frequency_frontier_events.csv'

MODES=['ALL_3_OF_3','PRICE_LS','PRICE_OI','PRICE_PLUS_1OF2','ANY_2_OF_3','BASE']
TARGET_MIN=25.0
TARGET_MAX=30.0

def metrics(g):
    x=g.netR.to_numpy(float)
    if len(x)==0:return {'N':0}
    w=x[x>0].sum(); l=-x[x<0].sum()
    eq=np.cumsum(x); peak=np.maximum.accumulate(np.r_[0,eq]); dd=peak[1:]-eq
    return {'N':len(x),'EV_R':float(x.mean()),'WR':float((x>0).mean()),
            'PF':float(w/l) if l>0 else np.nan,'SumR':float(x.sum()),
            'MaxDD_R':float(dd.max()) if len(dd) else 0.0,
            'Recovery':float(x.sum()/dd.max()) if len(dd) and dd.max()>0 else np.nan}

def monthly(g):
    z=g.copy()
    z['month']=pd.to_datetime(z.entry_ts,unit='s',utc=True).dt.to_period('M').astype(str)
    m=z.groupby('month').agg(N=('netR','size'),SumR=('netR','sum')).reset_index()
    return {
      'months':len(m),
      'trades_per_month_mean':float(m.N.mean()),
      'trades_per_month_median':float(m.N.median()),
      'trades_per_month_min':int(m.N.min()),
      'trades_per_month_max':int(m.N.max()),
      'positive_months':int((m.SumR>0).sum()),
      'negative_months':int((m.SumR<0).sum()),
      'monthly_SumR_mean':float(m.SumR.mean()),
      'monthly_SumR_median':float(m.SumR.median())
    }

def build_combo(ev,ds,buy_mode,sell_mode):
    b=ev[(ev.dataset==ds)&(ev.side==1)&(ev.admission==buy_mode)]
    s=ev[(ev.dataset==ds)&(ev.side==-1)&(ev.admission==sell_mode)]
    g=pd.concat([b,s],ignore_index=True).sort_values('entry_ts')
    return g

def main():
    ev=pd.read_csv(SRC)
    rows=[]
    for buy in MODES:
      for sell in MODES:
        rec={'buy_mode':buy,'sell_mode':sell}
        for ds in ['historical','forward_2026']:
            g=build_combo(ev,ds,buy,sell)
            m=metrics(g); mo=monthly(g)
            p='hist_' if ds=='historical' else 'fwd_'
            for k,v in {**m,**mo}.items(): rec[p+k]=v
        rec['hist_in_target']=TARGET_MIN<=rec['hist_trades_per_month_mean']<=TARGET_MAX
        rec['fwd_in_target']=TARGET_MIN<=rec['fwd_trades_per_month_mean']<=TARGET_MAX
        rec['both_in_target']=rec['hist_in_target'] and rec['fwd_in_target']
        rec['pf_floor_pass']=rec['hist_PF']>=1.5 and rec['fwd_PF']>=1.5
        rec['all_fwd_months_positive']=rec['fwd_negative_months']==0
        rec['score']=(
          1000*int(rec['both_in_target'])+
          500*int(rec['pf_floor_pass'])+
          250*int(rec['all_fwd_months_positive'])+
          50*min(rec['hist_PF'],rec['fwd_PF'])+
          20*min(rec['hist_EV_R'],rec['fwd_EV_R'])-
          0.5*rec['hist_MaxDD_R']-
          abs(rec['hist_trades_per_month_mean']-27.5)-
          abs(rec['fwd_trades_per_month_mean']-27.5)
        )
        rows.append(rec)
    df=pd.DataFrame(rows).sort_values('score',ascending=False).reset_index(drop=True)
    df.to_csv(OUT/'asymmetric_frontier.csv',index=False)

    target=df[(df.hist_in_target)&(df.fwd_in_target)].copy()
    target.to_csv(OUT/'target_25_30.csv',index=False)

    robust=df[(df.hist_PF>=1.5)&(df.fwd_PF>=1.5)&(df.fwd_negative_months==0)].copy()
    robust.to_csv(OUT/'robust_pf15_all2026positive.csv',index=False)

    top=df.head(12).copy()
    summary={
      'lab':'LAB093_ASYMMETRIC_BUY_SELL_FRONTIER',
      'source':'LAB092 frequency_frontier_events.csv; exact same signals/execution, only BUY/SELL admission mixed asymmetrically',
      'target_trades_per_month':[TARGET_MIN,TARGET_MAX],
      'modes':MODES,
      'top_candidates':top.to_dict('records'),
      'limitations':['2026 Mar-Aug is reused diagnostic, not pristine OOS.',
                     'Sequential DD ignores concurrency/margin interaction.',
                     'This LAB does not retune thresholds or execution; only combines frozen LAB092 admission modes by side.']
    }
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2,default=float))
    (OUT/'REPORT.md').write_text('# LAB093 — ASYMMETRIC BUY/SELL FRONTIER\n\n'+json.dumps(summary,indent=2,default=float)+'\n\n## Top\n\n'+top.to_markdown(index=False)+'\n\n## Target 25-30/mo\n\n'+target.to_markdown(index=False))
    print((OUT/'REPORT.md').read_text())

if __name__=='__main__':main()
