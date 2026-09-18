from pathlib import Path
import importlib.util,json
import numpy as np,pandas as pd

ROOT=Path('labs/CROWDFADE_H1_H4_RISK_MULTIPLIER_LAB_023')
OUT=ROOT/'output'; OUT.mkdir(parents=True,exist_ok=True)
MULTS=[1.0,1.25,1.5,2.0]

def load_lab022():
    path=Path('labs/CROWDFADE_H1_H4_TREND_CROWD_ALIGNMENT_LAB_022/run.py')
    spec=importlib.util.spec_from_file_location('lab022_hist',path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    m.DATA=ROOT/'data';m.KDIR=m.DATA/'klines1m'
    return m

def metrics(x):
    x=np.asarray(x,float)
    eq=np.cumsum(x); peak=np.maximum.accumulate(np.r_[0.,eq])[1:]; dd=peak-eq
    p=x[x>0].sum(); n=abs(x[x<0].sum())
    maxdd=float(dd.max()) if len(dd) else 0.
    # longest losing run
    mx=cur=0
    for v in x:
        if v<0: cur+=1; mx=max(mx,cur)
        else: cur=0
    return {
      'N':int(len(x)),'WR':float((x>0).mean()),'EV_baseR_per_trade':float(x.mean()),
      'Sum_baseR':float(x.sum()),'PF':float(p/n) if n else 99.,
      'MaxDD_baseR':maxdd,'R_DD':float(x.sum()/maxdd) if maxdd else 99.,
      'MaxConsecutiveLosses':int(mx)
    }

def main():
    m=load_lab022()
    p,q=m.prep()
    arr=[p.ts.to_numpy(np.int64),p.o.to_numpy(float),p.h.to_numpy(float),p.l.to_numpy(float),p.c.to_numpy(float),
         q.close_ts.to_numpy(np.int64),q.c.to_numpy(float),q.z.to_numpy(float),q.atr.to_numpy(float),
         q.h1_state.to_numpy(np.int64),q.h4_state.to_numpy(np.int64),
         q.yr.to_numpy(np.int64),q.daykey.to_numpy(np.int64)]
    m.sim(*[x[:1000] for x in arr])
    r,side,crowd,h1,h4,yr=m.sim(*arr)

    target=(h1!=0)&(h4!=0)&(h1==h4)&(side==h1)
    baseline=m.stats(r)
    target_raw=m.stats(r[target])

    seq=pd.DataFrame({
      'trade_index':np.arange(1,len(r)+1),
      'year':yr.astype(int),'raw_R':r,'target_boost_state':target.astype(int),
      'side':np.where(side>0,'LONG','SHORT'),
      'H1':np.where(h1>0,'UP',np.where(h1<0,'DOWN','NEUTRAL')),
      'H4':np.where(h4>0,'UP',np.where(h4<0,'DOWN','NEUTRAL'))
    })

    results=[]
    for mult in MULTS:
        wr=r*np.where(target,mult,1.0)
        eq=np.cumsum(wr); peak=np.maximum.accumulate(np.r_[0.,eq])[1:]; dd=peak-eq
        seq[f'weighted_R_{mult:g}x']=wr
        seq[f'equity_{mult:g}x']=eq
        seq[f'drawdown_{mult:g}x']=dd

        annual={str(y):metrics(wr[yr==y]) for y in range(2021,2026)}
        res={'multiplier':mult,'target_risk_multiple':mult,'all':metrics(wr),
             'positive_years':int(sum(v['Sum_baseR']>0 for v in annual.values())),
             'annual':annual,
             'target_trade_count':int(target.sum()),
             'target_share':float(target.mean()),
             'target_weighted_contribution_baseR':float((r[target]*mult).sum()),
             'non_target_contribution_baseR':float(r[~target].sum())}
        results.append(res)

    seq.to_csv(OUT/'equity_sequence_2021_2025.csv',index=False)
    out={
      'lab':'CROWDFADE_H1_H4_RISK_MULTIPLIER_LAB_023',
      'period':'2021-2025 historical discovery',
      'rule':'Boost lot/risk only when H1 and H4 are non-neutral, aligned, and CrowdFade trade direction equals aligned trend (therefore crowd is against trend).',
      'multipliers':MULTS,
      'baseline_unweighted':baseline,
      'target_bucket_raw':target_raw,
      'target_trade_count':int(target.sum()),
      'target_share':float(target.mean()),
      'results':results,
      'risk_percent_examples':{
        'base_0.10pct':{str(x):0.10*x for x in MULTS},
        'base_0.15pct':{str(x):0.15*x for x in MULTS},
        'base_0.25pct':{str(x):0.25*x for x in MULTS}
      }
    }
    (OUT/'summary.json').write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
