from pathlib import Path
import argparse, json, zipfile, hashlib, ast
import numpy as np
import pandas as pd
from numba import njit

HOURS=[1,3,6,12,24,48]
LEVELS=np.array([.5,1.,2.,3.])
@njit
def profiles(h,l,c,v):
 n=len(c);out=np.full((n,7),np.nan)
 for i in range(287,n):
  lo=np.min(l[i-287:i+1]);hi=np.max(h[i-287:i+1])
  if not np.isfinite(lo+hi) or hi<=lo:continue
  step=(hi-lo)/40.;vv=np.zeros(40)
  for j in range(i-287,i+1):
   if not np.isfinite(v[j]):continue
   a=l[j];b=h[j]
   if b<=a:
    k=min(39,max(0,int((c[j]-lo)/step)));vv[k]+=v[j];continue
   k0=max(0,int((a-lo)/step));k1=min(39,int((b-lo)/step))
   for k in range(k0,k1+1):
    overlap=min(b,lo+(k+1)*step)-max(a,lo+k*step)
    if overlap>0:vv[k]+=v[j]*overlap/(b-a)
  total=vv.sum()
  if total<=0:continue
  poc=np.argmax(vv);left=poc;right=poc;s=vv[poc]
  while s<.7*total and (left>0 or right<39):
   lv=vv[left-1] if left>0 else -1.;rv=vv[right+1] if right<39 else -1.
   if rv>=lv and right<39:right+=1;s+=vv[right]
   elif left>0:left-=1;s+=vv[left]
   else:break
  lower=0.;upper=0.
  for k in range(40):
   if k+.5<40/3:lower+=vv[k]
   if k+.5>80/3:upper+=vv[k]
  order=np.argsort(vv);a=order[-1];b=order[-2];sh=0
  if abs(a-b)>=10 and vv[b]>=.7*vv[a]:sh=3
  elif poc+.5>=80/3 and upper>1.15*lower:sh=1
  elif poc+.5<=40/3 and lower>1.15*upper:sh=2
  k=min(39,max(0,int((c[i]-lo)/step)))
  out[i]=np.array([lo+(poc+.5)*step,lo+left*step,lo+(right+1)*step,float(sh),vv[k]/(total/40),hi-lo,vv[poc]/total])
 return out

@njit
def labels(h,l,c,atr,steps):
 n=len(c);out=np.full((n,15),np.nan)
 for i in range(n-steps):
  if not np.isfinite(c[i]+atr[i]) or atr[i]<=0:continue
  up=0.;down=0.;tu=0;td=0;hit=np.full(8,-1.)
  ok=True
  for j in range(1,steps+1):
   if not np.isfinite(h[i+j]+l[i+j]+c[i+j]):ok=False;break
   u=(h[i+j]-c[i])/atr[i];d=(c[i]-l[i+j])/atr[i]
   if u>up:up=u;tu=j
   if d>down:down=d;td=j
   for k in range(4):
    if hit[k]<0 and u>=LEVELS[k]:hit[k]=j*5.
    if hit[k+4]<0 and d>=LEVELS[k]:hit[k+4]=j*5.
  if ok:
   out[i,0]=(c[i+steps]-c[i])/atr[i];out[i,1]=up;out[i,2]=down
   out[i,3]=tu*5;out[i,4]=td*5
   for k in range(8):out[i,5+k]=hit[k]
   # -1 ambiguous; 0 not reached first within horizon; 1 target first
   bu=hit[2];bd=hit[5];su=hit[1];sd=hit[6]
   out[i,13]= -1 if bu>=0 and bu==bd else (1.0 if bu>=0 and (bd<0 or bu<bd) else 0.0)
   out[i,14]= -1 if sd>=0 and sd==su else (1.0 if sd>=0 and (su<0 or sd<su) else 0.0)
 return out

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def loadprice(p):
 with zipfile.ZipFile(p) as z:d=pd.concat([pd.read_csv(z.open(n)) for n in z.namelist() if n.endswith('.csv')],ignore_index=True)
 d['time']=pd.to_datetime(d.time,format='%Y.%m.%d %H:%M',utc=True)
 exact=int(d.duplicated().sum());d=d.drop_duplicates()
 if d.time.duplicated().any():raise ValueError('conflicting OHLCV duplicates')
 d=d.sort_values('time').set_index('time')
 assert (d.high>=d[['open','close','low']].max(axis=1)).all()
 assert (d.low<=d[['open','close','high']].min(axis=1)).all()
 assert (d.volume>=0).all()
 return d,exact

def run(a):
 out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
 p,dups=loadprice(a.price);source_start=str(p.index.min());source_end=str(p.index.max())
 p=p.loc['2020-12-28':].reindex(pd.date_range(max(p.index.min(),pd.Timestamp('2020-12-28',tz='UTC')),p.index.max(),freq='5min'))
 ts=p.index+pd.Timedelta(minutes=5)
 hour=p.resample('1h').agg({'open':'first','high':'max','low':'min','close':'last'})
 counts=p.close.resample('1h').count();hour.loc[counts!=12,:]=np.nan
 prev=hour.close.shift();tr=pd.concat([hour.high-hour.low,(hour.high-prev).abs(),(hour.low-prev).abs()],axis=1).max(axis=1)
 tr[(counts!=12)|prev.isna()]=np.nan
 atr=tr.rolling(14,min_periods=14).mean();atr.index+=pd.Timedelta(hours=1)
 atr=atr.reindex(ts,method='ffill').to_numpy()
 f=pd.read_csv(a.flow);f['time']=pd.to_datetime(f.create_time,utc=True);f=f.drop_duplicates()
 if f.time.duplicated().any():raise ValueError('conflicting flow duplicates')
 f=f.set_index('time').sort_index();f=f.reindex(pd.date_range(f.index.min(),f.index.max(),freq='5min'))
 ratio=f.count_long_short_ratio.where(f.count_long_short_ratio>0)
 z=(ratio-ratio.rolling(72).mean())/ratio.rolling(72).std(ddof=0).replace(0,np.nan)
 ff=pd.DataFrame({'ratio':ratio,'z':z,'z_change_1h':z-z.shift(12), 'oi_value':f.sum_open_interest_value,'oi_quantity':f.sum_open_interest,
 'oi4h_value':f.sum_open_interest_value/f.sum_open_interest_value.shift(48)-1,'oi4h_quantity':f.sum_open_interest/f.sum_open_interest.shift(48)-1})
 # strict one-bar assumed publication delay; exact alignment on regular clock
 ff.index+=pd.Timedelta(minutes=5);ff=ff.reindex(ts)
 print('Computing profiles',len(p),flush=True)
 pr=profiles(*[p[k].to_numpy(float) for k in ['high','low','close','volume']])
 d=pd.DataFrame(pr,columns=['poc','val','vah','shape_code','density','profile_range','poc_volume_share'],index=ts)
 d['close']=p.close.to_numpy();d['atr']=atr
 for k in ff:d[k]=ff[k].to_numpy()
 d['shape']=d.shape_code.map({0:'D',1:'P',2:'b',3:'DOUBLE'}).fillna('NA')
 d['location']=np.select([d.close<d.val,d.close>d.vah,d.val.notna()],['BELOW','ABOVE','INSIDE'],default='NA')
 d['poc_migration6h']=(d.poc-d.poc.shift(72))/d.atr
 d['price6h_atr']=(d.close-d.close.shift(72))/d.atr
 # past price trend valid only across a full uninterrupted six hours
 d.loc[p.close.rolling(73).count().to_numpy()!=73,'price6h_atr']=np.nan
 d['trend']=np.select([d.price6h_atr>.5,d.price6h_atr<-.5,d.price6h_atr.notna()],['UP','DOWN','FLAT'],default='NA')
 d['z_bucket']=pd.cut(d.z.abs(),[0,.6,1,1.5,np.inf],right=False,labels=['LOW','MID','HIGH','EXTREME']).astype(str)
 d['crowd']=np.where(d.z>=0,'POS_','NEG_')+d.z_bucket
 d['oi_bucket']=pd.cut(d.oi4h_value,[-np.inf,0,.0035,.00867,np.inf],right=False,labels=['NEG','LOW','MID','HIGH']).astype(str)
 d['split']=np.select([d.index<pd.Timestamp('2024-01-01',tz='UTC'),d.index<pd.Timestamp('2025-01-01',tz='UTC')],['DISCOVERY','VALIDATION'],default='CHECK')
 for boundary in ['2024-01-01','2025-01-01']:
  b=pd.Timestamp(boundary,tz='UTC');d.loc[(d.index>=b-pd.Timedelta(hours=48))&(d.index<b),'split']='PURGED'
 d['valid_state']=np.isfinite(d[['atr','z','oi4h_value','poc','price6h_atr']]).all(axis=1)
 d.index.name='time';scope=d.index>=pd.Timestamp('2021-01-01',tz='UTC')
 d=d.loc[scope].copy();d.to_parquet(out/'LAB160_states.parquet')
 audit={'status':'completed_exploratory_atlas','price_source_start':source_start,'price_source_end':source_end,'price_exact_duplicates':dups,
 'price_missing_grid_rows':int(p.close.isna().sum()),'atlas_observations':len(d),'valid_states':int(d.valid_state.sum()),
 'price_sha256':sha(a.price),'flow_sha256':sha(a.flow),'flow_delay_minutes':5,'profile':'M5 reconstructed uniform-range volume,24h,40 bins','atr':'closed H1 SMA14 true range, lineage parity'}
 summaries=[];primary=None
 cols=['terminal_atr','up_mfe_atr','down_mfe_atr','up_extreme_minutes','down_extreme_minutes']+[f'{s}_hit_{v:g}_minutes' for s in ['up','down'] for v in LEVELS]+['up2_before_down1','down2_before_up1']
 for h in HOURS:
  print('Labels',h,flush=True)
  arr=labels(*[p[k].to_numpy(float) for k in ['high','low','close']],atr,h*12)
  y=pd.DataFrame(arr[scope],columns=cols,index=d.index)
  y['path_class']=np.select([d.trend=='FLAT',((d.trend=='UP')&(y.terminal_atr>=.5))|((d.trend=='DOWN')&(y.terminal_atr<=-.5)),((d.trend=='UP')&(y.terminal_atr<=-.5))|((d.trend=='DOWN')&(y.terminal_atr>=.5))],['NEUTRAL_PRIOR','CONTINUATION','REVERSAL'],default='SMALL_OR_UNRESOLVED')
  y.loc[y.terminal_atr.isna(),'path_class']='MISSING'
  y.to_parquet(out/f'LAB160_labels_{h}h.parquet')
  if h==6:primary=y
  for split in ['DISCOVERY','VALIDATION','CHECK']:
   v=y[(d.split==split)&d.valid_state].dropna(subset=['terminal_atr'])
   summaries.append({'horizon_h':h,'split':split,'n':len(v),'median_terminal_atr':v.terminal_atr.median(),'median_up_mfe_atr':v.up_mfe_atr.median(),'median_down_mfe_atr':v.down_mfe_atr.median(),
    'p_up2_first':(v.up2_before_down1==1).mean(),'p_down2_first':(v.down2_before_up1==1).mean(),'up_ambiguous':int((v.up2_before_down1==-1).sum()),'down_ambiguous':int((v.down2_before_up1==-1).sum()),
    'p_up2_any':(v.up_hit_2_minutes>=0).mean(),'p_down2_any':(v.down_hit_2_minutes>=0).mean()})
 pd.DataFrame(summaries).to_csv(out/'LAB160_horizon_summary.csv',index=False)
 b=d.join(primary);b=b[b.valid_state & (b.split!='PURGED') & b.terminal_atr.notna()].copy()
 b['week']=b.index.strftime('%G-%V');b['month']=b.index.strftime('%Y-%m')
 keys={'PRICE':['trend'],'FLOW':['trend','crowd','oi_bucket'],'PROFILE':['trend','crowd','oi_bucket','shape','location']}
 ablation=[];candidates=[];celltables=[];monthly=[]
 for direction,target in [('UP','up2_before_down1'),('DOWN','down2_before_up1')]:
  bb=b[b[target]>=0].copy();train=bb[bb.split=='DISCOVERY'];base=train[target].mean();preds={}
  for model,kk in keys.items():
   st=train.groupby(kk)[target].agg(['sum','count']);st['prob']=(st['sum']+100*base)/(st['count']+100)
   idx=pd.MultiIndex.from_frame(bb[kk]) if len(kk)>1 else pd.Index(bb[kk[0]])
   pred=st.prob.reindex(idx).fillna(base).to_numpy();preds[model]=pred
   bb['err_'+model]=(pred-bb[target].to_numpy())**2
  for split in ['VALIDATION','CHECK']:
   v=bb[bb.split==split];rng=np.random.default_rng(160)
   weekly=v.groupby('week').agg(n=(target,'size'),delta=('err_PROFILE','sum'),flow=('err_FLOW','sum'))
   delta=(weekly.delta-weekly.flow).to_numpy();nn=weekly.n.to_numpy();boot=[]
   for _ in range(1000):
    ix=rng.integers(0,len(nn),len(nn));boot.append(delta[ix].sum()/nn[ix].sum())
   for model in keys:ablation.append({'direction':direction,'split':split,'model':model,'n':len(v),'brier':v['err_'+model].mean(),
    'profile_minus_flow_brier':np.sum(delta)/np.sum(nn),'delta_ci_low':np.quantile(boot,.025),'delta_ci_high':np.quantile(boot,.975)})
  kk=keys['PROFILE'];tables={}
  for split in ['DISCOVERY','VALIDATION','CHECK']:
   v=bb[bb.split==split];t=v.groupby(kk).agg(n=(target,'size'),wins=(target,'sum'),weeks=('week','nunique'),terminal_median=('terminal_atr','median'))
   t['prob']=t.wins/t.n;t['lift']=t.prob-v[target].mean();tables[split]=t
   ct=t.reset_index();ct['split']=split;ct['direction']=direction;celltables.append(ct)
  combined=tables['DISCOVERY'].add_prefix('train_').join(tables['VALIDATION'].add_prefix('val_'),how='inner')
  screen=combined[(combined.train_n>=500)&(combined.val_n>=100)&(combined.val_weeks>=10)&(combined.train_lift>=.03)&(combined.val_lift>=.03)].copy()
  screen['rank_score']=screen[['train_lift','val_lift']].min(axis=1)
  screen=screen.sort_values('rank_score',ascending=False).head(10).join(tables['CHECK'].add_prefix('check_'))
  for cell,row in screen.iterrows():
   mask=np.ones(len(bb),bool)
   for k,value in zip(kk,cell):mask &= (bb[k].to_numpy()==value)
   selected=bb.loc[mask];check=selected[selected.split=='CHECK'];tt=check.index
   episodes=int((tt.to_series().diff()!=pd.Timedelta(minutes=5)).sum())
   separated=0;last=None
   for t in tt:
    if last is None or t-last>=pd.Timedelta(hours=48):separated+=1;last=t
   record=dict(zip(kk,cell));record.update(row.to_dict());record.update(direction=direction,check_episode_starts=episodes,check_48h_separated=separated)
   candidates.append(record)
   for month,g in selected.groupby('month'):monthly.append({**dict(zip(kk,cell)),'direction':direction,'month':month,'n':len(g),'prob':g[target].mean()})
 pd.DataFrame(ablation).to_csv(out/'LAB160_ablation.csv',index=False)
 pd.concat(celltables).to_csv(out/'LAB160_state_cells.csv',index=False)
 pd.DataFrame(candidates).to_csv(out/'LAB160_candidates.csv',index=False)
 pd.DataFrame(monthly).to_csv(out/'LAB160_candidate_monthly.csv',index=False)
 (out/'LAB160_audit.json').write_text(json.dumps(audit,indent=2))
 print(json.dumps(audit,indent=2),flush=True)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--price',required=True);ap.add_argument('--flow',required=True);ap.add_argument('--out',required=True);run(ap.parse_args())
