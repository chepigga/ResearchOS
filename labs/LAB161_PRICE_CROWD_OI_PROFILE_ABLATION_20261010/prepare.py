from pathlib import Path
import os,ast,importlib.util,zipfile,json,hashlib
import numpy as np,pandas as pd
from numba import njit
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'results/LAB161_20261010';DATA=Path(os.environ.get('LAB160C_DATA',ROOT.parent/'data'));OUT.mkdir(exist_ok=True)
sp=importlib.util.spec_from_file_location('atlas',ROOT/'labs/LAB160_PRICE_TRAJECTORY_STATE_ATLAS_20261010/run_lab160.py');atlas=importlib.util.module_from_spec(sp);sp.loader.exec_module(atlas)
@njit
def outcomes(c,a,steps=288):
 n=len(c);out=np.full((n,7),np.nan)
 for i in range(n-steps):
  if not np.isfinite(c[i]+a[i]) or a[i]<=0:continue
  uh=-1;dh=-1;ua=-1;da=-1;mx=0.;mn=0.;ok=True
  for j in range(1,steps+1):
   if not np.isfinite(c[i+j]):ok=False;break
   x=(c[i+j]-c[i])/a[i];mx=max(mx,x);mn=min(mn,x)
   if uh<0 and x>=3:uh=j
   if dh<0 and x<=-3:dh=j
   if ua<0 and x<=-1.5:ua=j
   if da<0 and x>=1.5:da=j
  if not ok:continue
  u=uh>=0 and (ua<0 or uh<ua);d=dh>=0 and (da<0 or dh<da)
  assert not(u and d)
  out[i]=np.array([1 if u else (2 if d else 0),mx,-mn,(c[i+steps]-c[i])/a[i],uh*5 if uh>=0 else np.nan,dh*5 if dh>=0 else np.nan,1.])
 return out

def features(p,flow):
 # Input price is open-stamped. Every feature output is closed-stamped.
 p=p.copy();counts=p.close.resample('1h').count();h=p.resample('1h').agg({'high':'max','low':'min','close':'last'});h.loc[counts!=12]=np.nan;prev=h.close.shift();tr=pd.concat([h.high-h.low,(h.high-prev).abs(),(h.low-prev).abs()],axis=1).max(axis=1);tr[(counts!=12)|prev.isna()]=np.nan
 atr=tr.rolling(14).mean();atr.index+=pd.Timedelta(hours=1);p.index+=pd.Timedelta(minutes=5);d=p.copy();d['atr']=atr.reindex(p.index,method='ffill');a=d.atr;c=d.close
 groups={'PRICE':[],'CROWD':[],'OI':[],'PROFILE':[]}
 def put(group,k,v):d[k]=v;groups[group].append(k)
 for k in [1,6,12,72,288]:put('PRICE',f'ret_{k}',(c-c.shift(k))/a)
 for k in [72,288,576]:
  hi=d.high.rolling(k).max();lo=d.low.rolling(k).min();put('PRICE',f'location_{k}',(c-lo)/(hi-lo));put('PRICE',f'range_{k}',(hi-lo)/a)
 for k in [72,288]:put('PRICE',f'ema_dist_{k}',(c-c.ewm(span=k,adjust=False,min_periods=k).mean())/a)
 put('PRICE','atr_pct',a/c);put('PRICE','rv_6h',c.pct_change(fill_method=None).rolling(72).std()/(a/c));put('PRICE','volume_ratio',d.volume.rolling(12).mean()/d.volume.rolling(288).mean());put('PRICE','bar_range',(d.high-d.low)/a);put('PRICE','bar_body',(c-d.open)/a)
 f=flow.reindex(pd.date_range(flow.index.min(),flow.index.max(),freq='5min'));r=f.count_long_short_ratio.where(f.count_long_short_ratio>0);z=(r-r.rolling(72).mean())/r.rolling(72).std(ddof=0).replace(0,np.nan)
 ff=pd.DataFrame({'ratio':r,'crowd_z':z,'crowd_abs_z':z.abs(),'crowd_dz_1h':z-z.shift(12),'ratio_change_1h':r/r.shift(12)-1,'ratio_change_6h':r/r.shift(72)-1},index=f.index)
 for k in [6,12,48,288]:ff[f'oi_change_{k}']=f.sum_open_interest/f.sum_open_interest.shift(k)-1
 ff.index+=pd.Timedelta(minutes=5);ff=ff.reindex(d.index)
 for k in ff:put('OI' if k.startswith('oi_') else 'CROWD',k,ff[k])
 print('profiles',len(p),flush=True);pr=atlas.profiles(*[p[k].to_numpy(float) for k in ['high','low','close','volume']]);pr=pd.DataFrame(pr,index=d.index,columns=['poc','val','vah','shape','density','width','peak_share'])
 for k in ['poc','val','vah']:put('PROFILE',f'profile_dist_{k}',(c-pr[k])/a)
 for j in range(4):put('PROFILE',f'profile_shape_{j}',(pr['shape']==j).astype(float).where(pr['shape'].notna()))
 for k in ['density','peak_share']:put('PROFILE',f'profile_{k}',pr[k])
 put('PROFILE','profile_value_width',(pr.vah-pr.val)/a);put('PROFILE','profile_migration_6h',(pr.poc-pr.poc.shift(72))/a)
 # Require uninterrupted48h price context; no compressed clocks / hidden bridging across missing bars.
 valid_price=d.close.rolling(577).count()==577
 d['eligible_features']=valid_price & np.isfinite(d[sum(groups.values(),[])]).all(axis=1)
 return d,groups

def main():
 p,duplicates=atlas.loadprice(DATA/'btc_5m.zip');p=p.loc['2020-12-28':];p=p.reindex(pd.date_range(p.index.min(),p.index.max(),freq='5min'))
 with zipfile.ZipFile(DATA/'BTCUSDT_flow_2021-01-2026-08.csv.zip') as z:f=pd.read_csv(z.open([n for n in z.namelist() if n.endswith('.csv')][0]))
 f['time']=pd.to_datetime(f.create_time,utc=True);f=f.drop_duplicates();assert not f.time.duplicated().any();f=f.set_index('time').sort_index();end=min(p.index.max(),f.index.max());p=p.loc[:end]
 d,groups=features(p,f);y=outcomes(d.close.to_numpy(),d.atr.to_numpy());
 for i,k in enumerate(['target','up_mfe','down_mfe','terminal','up_hit_minutes','down_hit_minutes','valid_future']):d[k]=y[:,i]
 d=d.loc['2021-01-01':];d['eligible']=d.eligible_features & d.target.notna();d.to_pickle(OUT/'LAB161_dataset.pkl');(OUT/'LAB161_features.json').write_text(json.dumps(groups,indent=2))
 src=ROOT/'labs/LAB160D_MISSED_MOVE_AUDIT_20261010/run_audit.py';tree=ast.parse(src.read_text());node=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='legs'];ns={'pd':pd,'np':np};exec(compile(ast.Module(body=node,type_ignores=[]),str(src),'exec'),ns)
 waves=pd.DataFrame(ns['legs'](d,1.)+ns['legs'](d,2.));waves['move_id']=['W%05d'%i for i in range(len(waves))];waves.to_csv(OUT/'LAB161_waves.csv',index=False)
 # Fixed prefix check: future perturbation cannot change earlier causal features.
 prefix=p.iloc[:1800];pf=f.loc[:prefix.index[-1]];short,_=features(prefix,pf);keys=sum(groups.values(),[]);long,_=features(p.iloc[:1900],f.loc[:p.index[1899]])
 assert np.allclose(short[keys].to_numpy(),long.loc[short.index,keys].to_numpy(),equal_nan=True)
 audit={'rows':len(d),'eligible':int(d.eligible.sum()),'start':str(d.index.min()),'end':str(d.index.max()),'last_eligible':str(d[d.eligible].index.max()),'exact_price_duplicates_removed':duplicates,'price_missing':int(p.close.isna().sum()),'feature_count':{k:len(v) for k,v in groups.items()},'causal_prefix_invariance':True,'flow_assumed_delay_minutes':5,'sources':{x:hashlib.sha256((DATA/x).read_bytes()).hexdigest() for x in ['btc_5m.zip','BTCUSDT_flow_2021-01-2026-08.csv.zip']}}
 d.groupby(d.index.year).agg(rows=('eligible','size'),eligible=('eligible','sum')).to_csv(OUT/'LAB161_data_coverage.csv');(OUT/'LAB161_data_audit.json').write_text(json.dumps(audit,indent=2));print(json.dumps(audit),flush=True)
if __name__=='__main__':main()
