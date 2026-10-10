from pathlib import Path
import importlib.util,json,zipfile
import numpy as np,pandas as pd
R=Path(__file__).resolve().parents[2];O=R/'results/LAB166_20261010';O.mkdir(exist_ok=True)
sp=importlib.util.spec_from_file_location('profile162',R/'labs/LAB162_WAVE_PROFILE_FLOW_TRAJECTORIES_20261010/prepare.py');prmod=importlib.util.module_from_spec(sp);sp.loader.exec_module(prmod)

def features(d,cx,nodes,oi,ix):
 q=d.iloc[ix];c=q.close.to_numpy();atr=q.atr.to_numpy();side=np.where(q.ret_12>=0,1,-1);x=pd.DataFrame(index=q.index);groups={k:[] for k in ['PRICE_TREND','CROWD','OI','PROFILE','OBSTACLES']}
 def put(g,k,val):x[k]=np.asarray(val);groups[g].append(k)
 for tf in ['D1','H4','H1','M15','M5']:
  put('PRICE_TREND',tf+'_alignment',side*cx[tf+'_trend'].iloc[ix].to_numpy());put('PRICE_TREND',tf+'_phase',cx[tf+'_phase'].iloc[ix].to_numpy())
 for k in [1,6,12,48,72,288]:put('PRICE_TREND','return_'+str(k),side*(c-d.close.shift(k).iloc[ix].to_numpy())/atr)
 put('PRICE_TREND','acceleration_1h',side*(d.close-d.close.shift(12)-(d.close.shift(12)-d.close.shift(24))).iloc[ix].to_numpy()/atr)
 path=d.close.diff().abs().rolling(12).sum();put('PRICE_TREND','efficiency_1h',np.abs(d.close-d.close.shift(12)).iloc[ix].to_numpy()/path.iloc[ix].to_numpy())
 for k in [72,288,576]:put('PRICE_TREND','location_'+str(k),np.where(side==1,q['location_'+str(k)],1-q['location_'+str(k)]));put('PRICE_TREND','range_'+str(k),q['range_'+str(k)])
 for k in ['atr_pct','rv_6h','volume_ratio','bar_range']:put('PRICE_TREND',k,q[k])
 put('PRICE_TREND','body_aligned',side*q.bar_body.to_numpy());put('PRICE_TREND','effort_result',np.abs(q.ret_12.to_numpy())/q.volume_ratio.to_numpy())
 up=(d.high-np.maximum(d.close,d.open)).iloc[ix].to_numpy()/atr;down=(np.minimum(d.close,d.open)-d.low).iloc[ix].to_numpy()/atr;put('PRICE_TREND','forward_wick',np.where(side==1,up,down));put('PRICE_TREND','opposite_wick',np.where(side==1,down,up))
 for name in ['crowd_z','crowd_dz_1h','ratio_change_1h','ratio_change_6h']:put('CROWD',name,side*q[name].to_numpy())
 put('CROWD','ratio',q.ratio);put('CROWD','crowd_abs_z',q.crowd_abs_z)
 for k in [12,48,288]:put('OI','oi_change_'+str(k),100*(oi/oi.shift(k)-1).iloc[ix].to_numpy())
 put('OI','oi_acceleration',100*((oi/oi.shift(12)-1)-(oi.shift(12)/oi.shift(24)-1)).iloc[ix].to_numpy());put('OI','oi_price_interaction',x.oi_change_12*x.return_12)
 p=nodes.iloc[ix]
 for name in ['poc','val','vah','hvn2','lvn']:put('PROFILE',name+'_signed_distance',side*(c-p[name].to_numpy())/atr)
 put('PROFILE','value_width',(p.vah-p.val)/atr);put('PROFILE','in_value',((c>=p.val)&(c<=p.vah)).astype(float));put('PROFILE','poc_migration_1h',side*(nodes.poc-nodes.poc.shift(12)).iloc[ix].to_numpy()/atr);put('PROFILE','poc_migration_6h',side*(nodes.poc-nodes.poc.shift(72)).iloc[ix].to_numpy()/atr)
 for k,shape in enumerate(['D','P','b','B']):put('PROFILE','shape_'+shape,(p.shape_code==k).astype(float))
 put('PROFILE','shape_change_1h',(nodes.shape_code!=nodes.shape_code.shift(12)).iloc[ix].to_numpy().astype(float));put('PROFILE','valley_ratio',p.valley_ratio)
 # Positive distances to known levels; absent levels are encoded, not inferred from future.
 for family in ['swing','profile']:
  vv=[]
  if family=='swing':
   for tf in ['H1','H4']:vv.append(side*(np.where(side==1,cx[tf+'_last_high'].iloc[ix],cx[tf+'_last_low'].iloc[ix])-c)/atr)
  else:
   for name in ['poc','val','vah','hvn2','lvn']:vv.append(side*(p[name].to_numpy()-c)/atr)
  mat=np.column_stack(vv);mat=np.where(np.isfinite(mat)&(mat>.1),mat,np.inf);nearest=np.min(mat,axis=1);put('OBSTACLES',family+'_present',np.isfinite(nearest).astype(float));put('OBSTACLES',family+'_room_atr',np.minimum(nearest,10))
 put('OBSTACLES','nearest_room_atr',np.minimum(x.swing_room_atr,x.profile_room_atr));put('OBSTACLES','room_over1atr',(x.nearest_room_atr>=1).astype(float));put('OBSTACLES','room_over2atr',(x.nearest_room_atr>=2).astype(float))
 return x.replace([np.inf,-np.inf],np.nan),groups,side

def main():
 d=pd.read_pickle(R/'results/LAB161_20261010/LAB161_dataset.pkl');cx=pd.read_pickle(R/'results/LAB163_20261010/LAB163_context.pkl')
 print('Rebuilding reproducible profile nodes from intact price cache',flush=True);p=prmod.profile_nodes(*[d[k].to_numpy(float) for k in ['high','low','close','volume']]);nodes=pd.DataFrame(p,index=d.index,columns=['poc','val','vah','hvn2','lvn','shape_code','valley_ratio','profile_low','profile_high','bin_width','smooth_poc','profile_volume'])
 with zipfile.ZipFile(R.parent/'data/BTCUSDT_flow_2021-01-2026-08.csv.zip') as z:f=pd.read_csv(z.open('BTCUSDT_flow.csv'))
 f=f.drop_duplicates();f.index=pd.to_datetime(f.create_time,utc=True)+pd.Timedelta(minutes=5);oi=f.sum_open_interest.where(f.sum_open_interest>0).reindex(d.index)
 minutes=d.index.asi8//60_000_000_000;mask=d.eligible.to_numpy()&(minutes%360==0);ix=np.flatnonzero(mask);x,groups,side=features(d,cx,nodes,oi,ix)
 x['time']=x.index;x['i']=ix;x['side']=side;x['atr']=d.atr.iloc[ix].to_numpy();x['close']=d.close.iloc[ix].to_numpy();x['shape']=nodes.shape_code.iloc[ix].map({0:'D',1:'P',2:'b',3:'B'}).to_numpy();x['success']=(d.target.iloc[ix].to_numpy()==np.where(side==1,1,2)).astype(int);mfe=np.where(side==1,d.up_mfe.iloc[ix],d.down_mfe.iloc[ix]);x['false_type']=np.select([x.success==1,mfe>=3],['SUCCESS','AFTER_ADVERSE'],default='NEVER3');x['mfe_atr']=mfe;x['year']=x.time.dt.year;x['week']=x.time.dt.strftime('%G-%V');x['split']=np.select([x.year<=2022,x.year==2023,x.year==2024],['FIT','CAL','VALIDATION'],default='CHECK')
 for boundary in pd.date_range('2022-01-01','2027-01-01',freq='YS',tz='UTC'):
  x.loc[(x.time>=boundary-pd.Timedelta(hours=24))&(x.time<boundary),'split']='PURGED'
 x.loc[x.time>d.index[-1]-pd.Timedelta(hours=24),'split']='PURGED'
 old=pd.read_csv(R/'results/LAB165_20261010/signals.csv.gz',parse_dates=['time']);old=old[old.policy=='CLOCK_1H_MOMENTUM_R4'];v=x[(x.year>=2024)&(x.split!='PURGED')];assert set(v.time)==set(old.time);merged=v[['time','side','success']].merge(old[['time','side','clean_success']],on='time',suffixes=('_new','_old'));assert (merged.side_new==merged.side_old).all() and (merged.success==merged.clean_success).all()
 # Prefix feature calculation: only bars <=cutoff and earlier closed-TF context.
 cut=int(ix[len(ix)//2])+1;sel=ix[ix<cut][-100:];short,_,_=features(d.iloc[:cut],cx.iloc[:cut],nodes.iloc[:cut],oi.iloc[:cut],sel);long,_,_=features(d,cx,nodes,oi,sel);assert np.allclose(short.to_numpy(),long.to_numpy(),equal_nan=True)
 for r in x.iloc[::37].itertuples():
  future=r.side*(d.close.iloc[r.i+1:r.i+289].to_numpy()-r.close)/r.atr;good=np.flatnonzero(future>=3);bad=np.flatnonzero(future<=-1.5);assert r.success==int(len(good)>0 and(not len(bad) or good[0]<bad[0]))
 x.to_csv(O/'features.csv.gz',index=False,compression='gzip');(O/'feature_groups.json').write_text(json.dumps(groups,indent=2));missing=x[sum(groups.values(),[])].isna().mean().sort_values(ascending=False);missing.to_csv(O/'feature_missingness.csv',header=['fraction'])
 (O/'prepare_validation.json').write_text(json.dumps(dict(rows=len(x),split_counts=x.split.value_counts().to_dict(),clock_signal_exact_LAB165_parity=True,label_sample_recomputed=True,features_prefix_invariance=True,source_tape_rebuilt_due_to_truncated_LAB162_cache=True,oi_nonpositive_source_rows=int((f.sum_open_interest<=0).sum()),profile_shape_counts=x['shape'].value_counts().to_dict()),indent=2));d[['open','high','low','close','atr']].to_pickle(O/'price_runtime.pkl');print((O/'prepare_validation.json').read_text(),flush=True)
if __name__=='__main__':main()
