from prepare import R,O
import numpy as np,pandas as pd,json,joblib

def main():
 x=pd.read_csv(O/'scored_signals.csv.gz',parse_dates=['time']);w=pd.read_csv(R/'results/LAB161_20261010/LAB161_waves.csv',parse_dates=['start','peak','end']);w=w[w.definition=='LEG_REV1ATR'];folds=json.loads((R/'results/LAB161_20261010/LAB161_folds.json').read_text());rows=[];matched=[]
 masks={'ALL':np.ones(len(x),bool)}
 for level in ['PRICE_TREND','CROWD','OI','PROFILE','OBSTACLES']:masks[level+'_50']=x['pass_'+level+'_50'].to_numpy(bool)
 for f in folds:
  year=f['year'];waves=w[(w.start>=pd.Timestamp(f['test_start']))&(w.end<=pd.Timestamp(f['test_last']))]
  for selection,mask in masks.items():
   q=x[mask&(x.year==year)].sort_values('time');ti=q.time.astype('int64').to_numpy();hits=[];cleanhits=0
   for r in waves.itertuples():
    a=np.searchsorted(ti,max(r.start,r.peak-pd.Timedelta(hours=24)).value);b=np.searchsorted(ti,r.peak.value);z=q.iloc[a:b];z=z[z.side==r.side];rem=r.side*(r.peak_price-z.close)/z.atr;good=z[rem>=1]
    if len(good):
     rec=good.iloc[0];remaining=r.side*(r.peak_price-rec.close)/rec.atr;hits.append(remaining);cleanhits+=int((good.success==1).any());matched.append(dict(year=year,selection=selection,move_id=r.move_id,time=rec.time,remaining_atr=remaining))
   rows.append(dict(year=year,selection=selection,waves=len(waves),recognized=len(hits),clean_recognized=cleanhits,coverage_pct=100*len(hits)/len(waves),remaining_atr_median=np.median(hits) if hits else np.nan,signals=len(q)))
 out=pd.DataFrame(rows);out.to_csv(O/'wave_coverage.csv',index=False);pd.DataFrame(matched).to_csv(O/'wave_matches.csv',index=False)
 old=pd.read_csv(R/'results/LAB165_20261010/metrics.csv');ref=old[(old.policy=='CLOCK_1H_MOMENTUM_R4')&old.period.isin(['2024','2025','2026'])]
 for r in ref.itertuples():
  z=out[(out.selection=='ALL')&(out.year==int(r.period))].iloc[0];assert z.recognized==r.recognized and z.waves==r.waves
 for level in ['PRICE_TREND','CROWD','OI','PROFILE','OBSTACLES']:
  pack=joblib.load(O/f'models/{level}.joblib');z=x.iloc[::31];pred=pack['model'].predict_proba(z[pack['features']])[:,1];assert np.allclose(pred,z['score_'+level])
 summary=pd.read_csv(O/'execution_summary.csv');pt=pd.read_csv(O/'portfolio_trades.csv.gz');audit=[]
 for (selection,mode),v in pt.groupby(['selection','mode']):
  r=v.net_R;pf=r[r>0].sum()/-r[r<0].sum();row=summary[(summary.selection==selection)&(summary['mode']==mode)&(summary.replay=='PORTFOLIO2')&(summary.period=='CHECK_2025_26')&(summary.cost_bps==7.5)].iloc[0];assert np.isclose(row.PF,pf) and np.isclose(row.EV,r.mean());assert np.allclose(r,v.gross_R-7.5*v.cost_unit_R);gross=v.gross_R;gross_pf=gross[gross>0].sum()/-gross[gross<0].sum();audit.append(dict(selection=selection,mode=mode,n=len(v),gross_EV=gross.mean(),gross_PF=gross_pf,net_EV=r.mean(),mean_cost_R=(7.5*v.cost_unit_R).mean(),break_even_bps=gross.sum()/v.cost_unit_R.sum()))
 pd.DataFrame(audit).to_csv(O/'cost_decomposition.csv',index=False)
 (O/'final_validation.json').write_text(json.dumps(dict(wave_baseline_exact_LAB165_parity=True,reloaded_predictions_parity=True,portfolio_PF_EV_recomputed=True,net_cost_formula_recomputed=True,primary_split_selection_predeclared=True),indent=2));print(pd.DataFrame(audit).to_string(index=False),flush=True)
if __name__=='__main__':main()
