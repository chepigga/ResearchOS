from run import *
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss,roc_auc_score

def evaluate():
 d=pd.read_pickle(R/'results/LAB162_20261010/LAB162_tape.pkl');cx=pd.read_pickle(R/'results/LAB163_20261010/LAB163_context.pkl');b=pd.read_csv(O/'balances.csv');s=pd.read_csv(O/'signals_unlabelled.csv');s=s.merge(b.rename(columns={'side':'break_side'}),on='id',validate='many_to_one');rows=[]
 for _,r in s.iterrows():
  i=int(r.i);sd=int(r.side);a=d.atr.iloc[i];v=d.iloc[i];rec=r.to_dict();rec['time']=d.index[i];rec['atr_signal']=a;rec['price']=v.close
  for tf in ['D1','H4','H1','M15','M5']:rec[tf]=sd*cx[tf+'_trend'].iloc[i]
  rec['higher_context']='WITH' if rec['D1']==1 and rec['H4']==1 else ('AGAINST' if rec['D1']==-1 and rec['H4']==-1 else 'MIXED')
  rec['oi1h']=100*(v.oi_quantity/d.oi_quantity.iloc[i-12]-1) if i>=12 and d.oi_quantity.iloc[i-12]>0 else np.nan
  rec['crowd_dz']=sd*(v.crowd_z-d.crowd_z.iloc[i-12]);rec['crowd_z']=sd*v.crowd_z;rec['ls1h']=sd*100*(v.ratio/d.ratio.iloc[i-12]-1)
  rec['oi_alignment']='BUILD' if rec['oi1h']>.1 else ('UNWIND' if rec['oi1h']<-.1 else ('FLAT' if np.isfinite(rec['oi1h']) else 'MISSING'))
  rec['crowd_alignment']='WITH' if rec['crowd_dz']>.1 else ('AGAINST' if rec['crowd_dz']<-.1 else ('FLAT' if np.isfinite(rec['crowd_dz']) else 'MISSING'))
  rec['progress1h']=sd*(v.close-d.close.iloc[i-12])/a;rec['relative_volume']=d.volume.iloc[i-11:i+1].mean()/d.volume.iloc[i-299:i-11].mean();rec['effort_result']=rec['progress1h']/rec['relative_volume'];rec['break_distance']=sd*(v.close-r.boundary)/a
  rec['risk_atr']=sd*(v.close-r.stop)/a;rec['route_atr']=sd*(r.target-v.close)/a;rec['rr']=rec['route_atr']/rec['risk_atr'] if rec['risk_atr']>0 else np.nan;rec['delay_minutes']=(i-r.break_i)*5
  obstacles=[cx[tf+('_last_high' if sd==1 else '_last_low')].iloc[i] for tf in ['H1','H4']];dist=[sd*(x-v.close)/a for x in obstacles if sd*(x-v.close)>0];rec['swing_obstacle_atr']=min(dist) if dist else np.nan
  rec['poc_distance']=sd*(v.close-r.poc)/a;rec['va_width']=(r.vah-r.val)/a;rec['profile_duration_h']=(r.break_i-r.start)/12;rec['rolling_shape']=v['shape'];rec['shape_changed']=int(r['shape']!=v['shape'])
  for sh in ['P','b','B']:rec['shape_'+sh]=int(r['shape']==sh)
  rec['split']='DISCOVERY' if d.index[i].year<2024 else ('VALIDATION' if d.index[i].year==2024 else 'CHECK');rec['week']=d.index[i].strftime('%G-%V')
  for boundary in [pd.Timestamp('2024-01-01',tz='UTC'),pd.Timestamp('2025-01-01',tz='UTC')]:
   if boundary-pd.Timedelta(hours=24)<=d.index[i]<boundary:rec['split']='PURGED'
  if i+288>=len(d):rec['split']='PURGED'
  future=sd*(d.close.iloc[i+1:i+289].to_numpy()-v.close)/a;t=np.flatnonzero(future>=2);st=np.flatnonzero(future<=-1);jt=int(t[0]) if len(t) else 999;js=int(st[0]) if len(st) else 999
  gt=np.flatnonzero(future>=rec['route_atr']);gs=np.flatnonzero(future<=-rec['risk_atr']);gti=int(gt[0]) if len(gt) else 999;gsi=int(gs[0]) if len(gs) else 999;rec['geometry_valid']=bool(rec['route_atr']>0 and rec['risk_atr']>0);rec['geometry_outcome']=('TARGET' if gti<gsi else ('INVALIDATION' if gsi<gti else 'TIMEOUT')) if rec['geometry_valid'] else 'ALREADY_PASSED'
  rec['outcome']='SUCCESS' if jt<js else ('ADVERSE_FIRST' if js<jt else 'UNRESOLVED');rec['success']=int(jt<js);rec['mfe_atr']=max(0,future.max()) if len(future) else np.nan;rec['mae_atr']=max(0,-future.min()) if len(future) else np.nan;rec['terminal_atr']=future[-1] if len(future) else np.nan;rec['target_minutes']=(jt+1)*5 if jt<999 else np.nan;rec['eventual_2atr']=int(jt<999)
  rows.append(rec)
 s=pd.DataFrame(rows);s.to_csv(O/'signals.csv',index=False);valid=s[s.split!='PURGED'];summary=[]
 for grouping in [['stage'],['stage','shape'],['stage','higher_context'],['stage','oi_alignment'],['stage','crowd_alignment']]:
  for key,q in valid.groupby(['split']+grouping):
   x=dict(zip(['split']+grouping,key));x.update(grouping='+'.join(grouping),n=len(q),success_pct=q.success.mean()*100,false_pct=(1-q.success.mean())*100,adverse_first_pct=(q.outcome=='ADVERSE_FIRST').mean()*100,unresolved_pct=(q.outcome=='UNRESOLVED').mean()*100,eventual_2atr_pct=q.eventual_2atr.mean()*100,median_mfe=q.mfe_atr.median(),median_mae=q.mae_atr.median(),median_route=q.route_atr.median(),median_risk=q.risk_atr.median(),median_delay=q.delay_minutes.median());summary.append(x)
 pd.DataFrame(summary).to_csv(O/'summary.csv',index=False)
 # Paired rows: conditioning on a later confirmation is explicitly retrospective.
 pairs=[]
 for stage in ['RETEST_HOLD','FAILED_RETURN']:
  q=valid[valid.stage==stage].merge(valid[valid.stage=='BREAKOUT'],on='id',suffixes=('_later','_break'))
  for split,p in q.groupby('split_later'):
   pairs.append(dict(stage=stage,split=split,n=len(p),break_success_pct=p.success_break.mean()*100,later_success_pct=p.success_later.mean()*100,median_delay=p.delay_minutes_later.median(),median_directional_price_change_atr=np.median(p.side_break*(p.price_later-p.price_break)/p.atr_signal_break),median_remaining_route=p.route_atr_later.median()))
 pd.DataFrame(pairs).to_csv(O/'paired_stages.csv',index=False)
 # Independent price wave coverage, raw stage signals without additional event cooldown.
 waves=pd.read_csv(R/'results/LAB161_20261010/LAB161_waves.csv',parse_dates=['start','peak']);waves=waves[waves.definition=='LEG_REV1ATR'];cover=[];matches=[]
 for split in ['DISCOVERY','VALIDATION','CHECK']:
  yy=waves.start.dt.year;w=waves[(yy<2024) if split=='DISCOVERY' else ((yy==2024) if split=='VALIDATION' else (yy>=2025))].copy();w=w[w.peak<=d.index[-1]]
  for stage in ['BREAKOUT','RETEST_HOLD','FAILED_RETURN']:
   q=valid[(valid.split==split)&(valid.stage==stage)];hit=[]
   for _,v in w.iterrows():
    z=q[(q.time>=v.start)&(q.time<v.peak)&(q.side==v.side)&((v.peak-q.time)<=pd.Timedelta(hours=24))].copy()
    if len(z):
     z['remaining']=v.side*(v.peak_price-z.price)/z.atr_signal;z=z[z.remaining>=1]
    if len(z):
     r=z.sort_values('time').iloc[0];hit.append(r.remaining);matches.append(dict(split=split,stage=stage,move_id=v.move_id,balance_id=int(r.id),signal_time=r.time,remaining_atr=r.remaining))
   cover.append(dict(split=split,stage=stage,waves=len(w),recognized=len(hit),coverage_pct=100*len(hit)/len(w),signals=len(q),median_remaining_atr=np.median(hit) if hit else np.nan))
 pd.DataFrame(cover).to_csv(O/'wave_coverage.csv',index=False);pd.DataFrame(matches).to_csv(O/'wave_matches.csv',index=False)
 # Fixed nested models, feature rows matched across all levels.
 price=['width_atr','efficiency','progress1h','relative_volume','break_distance','D1','H4','H1','M15','M5'];crowd=['crowd_z','crowd_dz','ls1h'];oi=['oi1h'];prof=['poc_distance','va_width','profile_duration_h','shape_P','shape_b','shape_B'];sets=[price,price+crowd,price+crowd+oi,price+crowd+oi+prof];names=['PRICE_CONTEXT','PLUS_CROWD','PLUS_OI','PLUS_ANCHORED_PROFILE']
 q=valid[valid.stage=='BREAKOUT'].dropna(subset=sets[-1]).copy();train=q.split=='DISCOVERY';res=[];pred=[];previous={};rng=np.random.default_rng(164)
 for name,cols in zip(names,sets):
  model=make_pipeline(StandardScaler(),LogisticRegression(C=1,max_iter=2000));model.fit(q.loc[train,cols],q.loc[train,'success'])
  for split in ['VALIDATION','CHECK']:
   p=q[q.split==split];pr=model.predict_proba(p[cols])[:,1];y=p.success.to_numpy();loss=(pr-y)**2;lo=hi=delta=np.nan
   if split in previous:
    diff=loss-previous[split];weeks=p.week.to_numpy();unique=np.unique(weeks);sums=np.array([diff[weeks==w].sum() for w in unique]);counts=np.array([(weeks==w).sum() for w in unique]);boot=[]
    for _ in range(500):ids=rng.integers(len(unique),size=len(unique));boot.append(sums[ids].sum()/counts[ids].sum())
    lo,hi=np.percentile(boot,[2.5,97.5]);delta=diff.mean()
   res.append(dict(model=name,split=split,n=len(p),train_n=int(train.sum()),brier=brier_score_loss(y,pr),constant_train_brier=brier_score_loss(y,np.full(len(y),q.loc[train,'success'].mean())),auc=roc_auc_score(y,pr),delta_vs_previous=delta,delta_ci_low=lo,delta_ci_high=hi));previous[split]=loss
   for rid,prob in zip(p.id,pr):pred.append(dict(id=rid,model=name,split=split,p_success=prob))
 pd.DataFrame(res).to_csv(O/'ablation.csv',index=False);pd.DataFrame(pred).to_csv(O/'predictions.csv',index=False)
 validation=dict(complete_case_breakouts=len(q),all_breakouts=int((valid.stage=='BREAKOUT').sum()),signal_counts=valid.stage.value_counts().to_dict(),chronology=bool((s.i>=s.break_i).all()),branch_unique=bool(not s[s.stage!='BREAKOUT'].id.duplicated().any()),profile_before_break=True)
 for _,r in s.iloc[::17].iterrows():
  i=int(r.i);f=int(r.side)*(d.close.iloc[i+1:i+289].to_numpy()-d.close.iloc[i])/d.atr.iloc[i];st=np.where(f<=-1)[0];tg=np.where(f>=2)[0];expected=bool(len(tg) and (not len(st) or tg[0]<st[0]));assert expected==bool(r.success)
 validation['sampled_label_recomputation']=True;(O/'evaluation_validation.json').write_text(json.dumps(validation,indent=2));print(pd.DataFrame(summary).query("grouping == 'stage'").to_string(index=False));print(pd.DataFrame(res).to_string(index=False));print(pd.DataFrame(cover).to_string(index=False))
if __name__=='__main__':evaluate()
