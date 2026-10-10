from pathlib import Path
import json,hashlib,importlib.util,argparse
import numpy as np
import pandas as pd
from numba import njit
ROOT=Path(__file__).resolve().parents[2]
HORIZONS=[1,3,6,12,24,48]
NAMES=['QUIET','SMALL','TWO_SIDED','ROUND_TRIP_UP','ROUND_TRIP_DOWN','DIRECT_UP','DIRECT_DOWN','AFTER_PULLBACK_UP','AFTER_PULLBACK_DOWN','ORDER_UNCERTAIN_UP','ORDER_UNCERTAIN_DOWN']
METRICS=['terminal_atr','up_mfe_atr','down_mfe_atr','up_peak_minutes','down_peak_minutes','adverse_before_up_lower','adverse_before_up_upper','adverse_before_down_lower','adverse_before_down_upper','retention','close_efficiency','close_max_drawdown_atr','close_max_runup_atr','up_recovery_minutes','down_recovery_minutes','dominant_side','class_code','extreme_tie']+[f'path_{i:02}' for i in range(1,17)]
@njit
def classify(u,d,end,pre_u_lo,pre_u_hi,pre_d_lo,pre_d_hi):
 m=max(u,d)
 if m<.5:return 0
 if m<1:return 1
 if u>=1 and d>=1 and abs(end)<.5*m:return 2
 side=1 if u>d or (u==d and end>=0) else -1
 if side*end<.5*m:return 3 if side==1 else 4
 lower=pre_u_lo if side==1 else pre_d_lo
 upper=pre_u_hi if side==1 else pre_d_hi
 if lower>=.5:return 7 if side==1 else 8
 if upper<.5:return 5 if side==1 else 6
 return 9 if side==1 else 10

@njit
def paths(h,l,c,atr,steps):
 n=len(c);a=np.full((n,34),np.nan)
 for i in range(n-steps):
  if not np.isfinite(c[i]+atr[i]) or atr[i]<=0:continue
  ref=c[i];scale=atr[i];u=0.;d=0.;ut=0;dt=0
  pu_lo=0.;pu_hi=0.;pd_lo=0.;pd_hi=0.;low=0.;high=0.;prev=0.;variation=0.;clmax=0.;clmin=0.;dd=0.;ru=0.;ok=True
  for j in range(1,steps+1):
   if not np.isfinite(h[i+j]+l[i+j]+c[i+j]):ok=False;break
   uh=(h[i+j]-ref)/scale;dl=(ref-l[i+j])/scale;e=(c[i+j]-ref)/scale
   if uh>u:u=uh;ut=j;pu_lo=low;pu_hi=max(low,dl)
   if dl>d:d=dl;dt=j;pd_lo=high;pd_hi=max(high,uh)
   low=max(low,dl);high=max(high,uh)
   variation+=abs(e-prev);prev=e
   dd=max(dd,clmax-e);ru=max(ru,e-clmin);clmax=max(clmax,e);clmin=min(clmin,e)
  if not ok:continue
  end=(c[i+steps]-ref)/scale;dom=1 if u>d or (u==d and end>=0) else -1
  code=classify(u,d,end,pu_lo,pu_hi,pd_lo,pd_hi)
  # first close back to reference after the worst adverse LOW before up peak (mirror DOWN)
  recover_u=-1.;recover_d=-1.;min_i=0;max_i=0;lv=0.;hv=0.
  for j in range(1,ut):
   x=(ref-l[i+j])/scale
   if x>lv:lv=x;min_i=j
  for j in range(1,dt):
   x=(h[i+j]-ref)/scale
   if x>hv:hv=x;max_i=j
  if min_i>0:
   for j in range(min_i+1,ut+1):
    if c[i+j]>=ref:recover_u=(j-min_i)*5.;break
  if max_i>0:
   for j in range(max_i+1,dt+1):
    if c[i+j]<=ref:recover_d=(j-max_i)*5.;break
  a[i,:18]=np.array([end,u,d,ut*5.,dt*5.,pu_lo,pu_hi,pd_lo,pd_hi,dom*end/max(max(u,d),1e-12),abs(end)/max(variation,1e-12),dd,ru,recover_u,recover_d,float(dom),float(code),1. if u==d else 0.])
  for k in range(16):
   j=max(1,int(np.ceil((k+1)*steps/16.)))
   a[i,18+k]=(c[i+j]-ref)/scale
 return a

def bootstrap_probability(v,column,seed=1602):
 # cluster by UTC calendar week, weights preserve all-row estimator
 w=v.groupby('week')[column].agg(['sum','count']);n=len(w)
 if n<10:return np.nan,np.nan
 rng=np.random.default_rng(seed);s=w['sum'].to_numpy();c=w['count'].to_numpy();z=[]
 for _ in range(500):
  ix=rng.integers(n,size=n);z.append(s[ix].sum()/c[ix].sum())
 return float(np.quantile(z,.025)),float(np.quantile(z,.975))

def summarize(g):
 return dict(n=len(g),terminal_median=g.terminal_atr.median(),max_excursion_median=g.max_excursion.median(),up_mfe_median=g.up_mfe_atr.median(),down_mfe_median=g.down_mfe_atr.median(),prepeak_adverse_median=g.prepeak_adverse.median(),prepeak_adverse_q75=g.prepeak_adverse.quantile(.75),peak_minutes_median=g.peak_minutes.median(),retention_median=g.retention.median(),close_efficiency_median=g.close_efficiency.median())

def main(a):
 out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
 sp=importlib.util.spec_from_file_location('lab160',ROOT/'labs/LAB160_PRICE_TRAJECTORY_STATE_ATLAS_20261010/run_lab160.py');old=importlib.util.module_from_spec(sp);sp.loader.exec_module(old)
 p,_=old.loadprice(a.price);p.index+=pd.Timedelta(minutes=5)
 s=pd.read_parquet(ROOT/'results/LAB160_20261010/LAB160_states.parquet');p=p.reindex(s.index)
 assert p.close.notna().all() and np.allclose(p.close,s.close)
 s['past1h_atr']=(s.close-s.close.shift(12))/s.atr;s['past24h_atr']=(s.close-s.close.shift(288))/s.atr
 hi=p.high.rolling(288).max();lo=p.low.rolling(288).min();s['price_range_location']=(s.close-lo)/(hi-lo)
 s['price_location']=pd.cut(s.price_range_location,[-np.inf,1/3,2/3,np.inf],labels=['LOWER','MIDDLE','UPPER']).astype(str)
 s['crowd_state']=np.select([s.z<=-1,s.z>=1,s.z.notna()],['NEG','POS','MID'],default='NA')
 s['oi_state']=pd.cut(s.oi4h_quantity,[-np.inf,-.0035,.0035,np.inf],labels=['FALLING','STABLE','RISING']).astype(str)
 s['oi_value_state']=pd.cut(s.oi4h_value,[-np.inf,-.0035,.0035,np.inf],labels=['FALLING','STABLE','RISING']).astype(str)
 s['migration_state']=pd.cut(s.poc_migration6h,[-np.inf,-.25,.25,np.inf],labels=['DOWN','FLAT','UP']).astype(str)
 s['density_state']=pd.cut(s.density,[0,.5,1.5,np.inf],labels=['LOW','MID','HIGH'],include_lowest=True).astype(str)
 s['year']=s.index.year;s['week']=s.index.strftime('%G-%V')
 s['overlay_valid']=s.valid_state & np.isfinite(s.oi4h_quantity)
 s.to_parquet(out/'LAB160B_states.parquet')
 keys=['trend','crowd_state','oi_state','shape','location'];parent=keys[:3]
 anatomy=[];magnitudes=[];relations=[];allcells=[];marginals=[];shortlist=[];examples=[];medpaths=[];coverage=[]
 for h in HORIZONS:
  print('HORIZON',h,flush=True)
  aa=paths(p.high.to_numpy(float),p.low.to_numpy(float),p.close.to_numpy(float),s.atr.to_numpy(float),h*12)
  d=pd.DataFrame(aa,index=s.index,columns=METRICS);d.index.name='time'
  d['path_class']=d.class_code.map(dict(enumerate(NAMES))).fillna('MISSING')
  d['max_excursion']=d[['up_mfe_atr','down_mfe_atr']].max(axis=1)
  d['prepeak_adverse']=np.where(d.dominant_side==1,d.adverse_before_up_lower,d.adverse_before_down_lower)
  d['peak_minutes']=np.where(d.dominant_side==1,d.up_peak_minutes,d.down_peak_minutes)
  d['magnitude']=pd.cut(d.max_excursion,[0,.5,1,2,3,5,np.inf],right=False,labels=['<0.5','0.5-1','1-2','2-3','3-5','>=5']).astype(str)
  d['past_relation']=np.select([(d.dominant_side==1)&(s.trend=='UP')|(d.dominant_side==-1)&(s.trend=='DOWN'),(d.dominant_side==1)&(s.trend=='DOWN')|(d.dominant_side==-1)&(s.trend=='UP')],['CONTINUATION','REVERSAL'],default='NEUTRAL_PRIOR')
  # relation is only meaningful for retained directional classes
  d.loc[~d.path_class.str.startswith(('DIRECT','AFTER_PULLBACK','ORDER_UNCERTAIN')),'past_relation']='NOT_RETAINED_DIRECTIONAL'
  minutes=s.index.asi8//(60*10**9);d['fixed_anchor']=(minutes%(h*60)==0)
  d.to_parquet(out/f'LAB160B_paths_{h}h.parquet')
  b=s.join(d);b=b[b.terminal_atr.notna() & (b.split!='PURGED')].copy()
  for split,g in b.groupby('split'):
   coverage.append(dict(horizon_h=h,split=split,price_n=len(g),overlay_n=int(g.overlay_valid.sum()),fixed_price_anchors=int(g.fixed_anchor.sum())))
   for cls,q in g.groupby('path_class'):
    for sampling,v in [('ALL_M5',q),('FIXED_NONOVERLAP',q[q.fixed_anchor])]:
     denom=len(g) if sampling=='ALL_M5' else int(g.fixed_anchor.sum())
     anatomy.append(dict(horizon_h=h,split=split,path_class=cls,sampling=sampling,share=len(v)/denom,**summarize(v)))
   for (cls,mag),q in g.groupby(['path_class','magnitude']):magnitudes.append(dict(horizon_h=h,split=split,path_class=cls,magnitude=mag,n=len(q)))
   for (cls,rel),q in g.groupby(['path_class','past_relation']):relations.append(dict(horizon_h=h,split=split,path_class=cls,past_relation=rel,n=len(q)))
  # all period/year anatomy without dropping incomplete feature observations
  for (year,cls),g in b.groupby(['year','path_class']):anatomy.append(dict(horizon_h=h,split=str(year),path_class=cls,sampling='ALL_M5',share=len(g)/len(b[b.year==year]),**summarize(g)))
  v=b[b.overlay_valid].copy()
  for feature in ['trend','crowd','oi_state','oi_value_state','shape','location','migration_state','density_state','price_location']:
   for (split,value),g in v.groupby(['split',feature]):
    cnt=g.path_class.value_counts()
    for cls in NAMES:marginals.append(dict(horizon_h=h,split=split,feature=feature,value=value,path_class=cls,n=len(g),events=int(cnt.get(cls,0)),prob=float(cnt.get(cls,0))/len(g)))
  tables={}
  for split,g in v.groupby('split'):
   total=g.groupby(keys).agg(n=('path_class','size'),weeks=('week','nunique'),anchor_n=('fixed_anchor','sum'))
   cnt=pd.crosstab([g[k] for k in keys],g.path_class).reindex(columns=NAMES,fill_value=0)
   anc=g[g.fixed_anchor];ac=pd.crosstab([anc[k] for k in keys],anc.path_class).reindex(index=total.index,columns=NAMES,fill_value=0)
   pc=pd.crosstab([g[k] for k in parent],g.path_class).reindex(columns=NAMES,fill_value=0);pc=pc.div(pc.sum(axis=1),axis=0)
   tc=pd.crosstab(g.trend,g.path_class).reindex(columns=NAMES,fill_value=0);tc=tc.div(tc.sum(axis=1),axis=0)
   cells=[]
   for cls in NAMES:
    z=total.copy();z['events']=cnt[cls].reindex(total.index,fill_value=0);z['prob']=z.events/z.n
    z['anchor_events']=ac[cls];z['anchor_prob']=z.anchor_events/z.anchor_n.replace(0,np.nan)
    z['base_prob']=(g.path_class==cls).mean();z['lift']=z.prob-z.base_prob
    temp=z.reset_index();idx=pd.MultiIndex.from_frame(temp[parent]);temp['parent_prob']=pc[cls].reindex(idx).to_numpy();temp['trend_prob']=tc[cls].reindex(temp.trend).to_numpy()
    temp['profile_lift']=temp.prob-temp.parent_prob;temp['trend_lift']=temp.prob-temp.trend_prob
    temp['path_class']=cls;cells.append(temp)
   tab=pd.concat(cells,ignore_index=True);tab['horizon_h']=h;tab['split']=split;allcells.append(tab);tables[split]=tab.set_index(keys+['path_class'])
  comb=tables['DISCOVERY'].add_prefix('train_').join(tables['VALIDATION'].add_prefix('val_'),how='inner')
  keep=(comb.train_n>=500)&(comb.val_n>=150)&(comb.train_weeks>=10)&(comb.val_weeks>=10)&(comb.train_events>=50)&(comb.val_events>=20)&(comb.train_lift>=.03)&(comb.val_lift>=.03)&(comb.train_trend_lift>0)&(comb.val_trend_lift>0)
  choose=comb[keep].copy();choose['ranking']=choose[['train_trend_lift','val_trend_lift']].min(axis=1)
  choose=choose.reset_index().sort_values('ranking',ascending=False).groupby('path_class',sort=False).head(3).set_index(keys+['path_class'])
  choose=choose.join(tables['CHECK'].add_prefix('check_'),how='left')
  for cell,r in choose.iterrows():
   row=dict(zip(keys+['path_class'],cell));row.update(r.to_dict());row['horizon_h']=h
   q=v[v.split=='CHECK']
   for k,value in zip(keys,cell[:-1]):q=q[q[k]==value]
   q=q.copy();q['hit']=(q.path_class==cell[-1]).astype(int)
   row['check_ci_low'],row['check_ci_high']=bootstrap_probability(q,'hit')
   row['check_support']=bool(row.get('check_anchor_n',0)>=30 and row.get('check_weeks',0)>=10)
   shortlist.append(row)
  # representative future shapes from clock-based, nonoverlapping check anchors
  pathscols=[f'path_{i:02}' for i in range(1,17)]
  q=b[(b.split=='CHECK')&b.fixed_anchor]
  for cls,g in q.groupby('path_class'):
   if len(g)==0:continue
   median=g[pathscols].median();scaled=g[pathscols].div(g.max_excursion,axis=0);target=scaled.median()
   distance=(scaled-target).pow(2).mean(axis=1);ix=distance.idxmin();rr=g.loc[ix]
   examples.append(dict(horizon_h=h,path_class=cls,time=str(ix),terminal_atr=float(rr.terminal_atr),max_excursion=float(rr.max_excursion),prepeak_adverse=float(rr.prepeak_adverse),z=float(rr.z),oi4h_quantity=float(rr.oi4h_quantity),shape=rr['shape'],location=rr.location))
   for k in range(16):medpaths.append(dict(horizon_h=h,path_class=cls,fraction=(k+1)/16,n=len(g),median_atr=float(median.iloc[k]),q25_atr=float(g[pathscols[k]].quantile(.25)),q75_atr=float(g[pathscols[k]].quantile(.75))))
  # targeted delayed large paths preserve -1.2 then +5 cases: aggregate without trade barriers
  delayed=b[(b.max_excursion>=3)&(b.prepeak_adverse>=1)&b.path_class.str.startswith('AFTER_PULLBACK')]
  dl=[]
  for split,g in b.groupby('split'):
   qd=delayed[delayed.split==split]
   dl.append(dict(horizon_h=h,split=split,n=len(qd),share=len(qd)/len(g),anchor_n=int(qd.fixed_anchor.sum()),median_move=qd.max_excursion.median(),median_pre_adverse=qd.prepeak_adverse.median()))
  pd.DataFrame(dl).to_csv(out/f'LAB160B_delayed_large_{h}h.csv',index=False)
 for name,rows in [('anatomy',anatomy),('magnitude',magnitudes),('past_relation',relations),('state_cells',allcells),('marginals',marginals),('shortlist',shortlist),('examples',examples),('median_paths',medpaths),('coverage',coverage)]:
  table=pd.concat(rows,ignore_index=True) if name=='state_cells' else pd.DataFrame(rows)
  table.to_csv(out/f'LAB160B_{name}.csv',index=False)
 audit={'rows':len(s),'horizons':HORIZONS,'source_price_sha256':hashlib.sha256(Path(a.price).read_bytes()).hexdigest(),'source_states_sha256':hashlib.sha256((ROOT/'results/LAB160_20261010/LAB160_states.parquet').read_bytes()).hexdigest(),'class_names':NAMES,'no_entry_rules':True,'no_barrier_race':True,'flow_delay_minutes_assumed':5,'check_not_pristine':True,'shortlist_size':len(shortlist)}
 (out/'LAB160B_audit.json').write_text(json.dumps(audit,indent=2));print(json.dumps(audit),flush=True)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--price',required=True);ap.add_argument('--out',required=True);main(ap.parse_args())
