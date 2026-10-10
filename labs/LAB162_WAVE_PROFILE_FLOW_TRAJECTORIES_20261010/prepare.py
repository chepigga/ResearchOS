from pathlib import Path
import json,os,zipfile
import numpy as np,pandas as pd
from numba import njit
R=Path(__file__).resolve().parents[2];O=R/'results/LAB162_20261010';O.mkdir(exist_ok=True);DATA=Path(os.environ.get('LAB160C_DATA',R.parent/'data'))
@njit
def profile_nodes(h,l,c,v):
 n=len(c);out=np.full((n,12),np.nan)
 for i in range(287,n):
  low=np.min(l[i-287:i+1]);high=np.max(h[i-287:i+1]);step=(high-low)/40
  if not np.isfinite(step) or step<=0:continue
  vv=np.zeros(40)
  for j in range(i-287,i+1):
   if not np.isfinite(v[j]):continue
   if h[j]<=l[j]:vv[min(39,max(0,int((c[j]-low)/step)))]+=v[j];continue
   a=max(0,int((l[j]-low)/step));b=min(39,int((h[j]-low)/step))
   for k in range(a,b+1):
    overlap=min(h[j],low+(k+1)*step)-max(l[j],low+k*step)
    if overlap>0:vv[k]+=v[j]*overlap/(h[j]-l[j])
  total=vv.sum()
  if total<=0:continue
  poc=np.argmax(vv);left=poc;right=poc;mass=vv[poc]
  while mass<.7*total and(left>0 or right<39):
   lv=vv[left-1] if left>0 else -1.;rv=vv[right+1] if right<39 else -1.
   if rv>=lv and right<39:right+=1;mass+=vv[right]
   elif left>0:left-=1;mass+=vv[left]
   else:break
  smooth=np.empty(40)
  for k in range(40):smooth[k]=np.mean(vv[max(0,k-1):min(40,k+2)])
  primary=np.argmax(smooth);secondary=-1
  for k in range(1,39):
   if abs(k-primary)>=6 and smooth[k]>=smooth[k-1] and smooth[k]>smooth[k+1] and smooth[k]>=.5*smooth[primary]:
    if secondary<0 or smooth[k]>smooth[secondary]:secondary=k
  hvn2=np.nan;lvn=np.nan;depth=np.nan;sh=0
  if secondary>=0:
   hvn2=low+(secondary+.5)*step;a=min(primary,secondary);b=max(primary,secondary);valley=a+np.argmin(smooth[a:b+1]);depth=smooth[valley]/min(smooth[primary],smooth[secondary])
   if depth<=.7:lvn=low+(valley+.5)*step
   if depth<=.7 and smooth[secondary]>=.7*smooth[primary]:sh=3
  lower=vv[:13].sum();upper=vv[27:].sum()
  if sh!=3:
   if poc+.5>=80/3 and upper>1.15*lower:sh=1
   elif poc+.5<=40/3 and lower>1.15*upper:sh=2
  out[i]=np.array([low+(poc+.5)*step,low+left*step,low+(right+1)*step,hvn2,lvn,float(sh),depth,low,high,step,low+(primary+.5)*step,total])
 return out

def main():
 d=pd.read_pickle(R/'results/LAB161_20261010/LAB161_dataset.pkl');pr=profile_nodes(*[d[k].to_numpy(float) for k in ['high','low','close','volume']]);cols=['POC_HVN','VAL','VAH','HVN2','LVN','shape_code','valley_ratio','profile_low','profile_high','bin_width','smoothed_primary','profile_volume']
 for j,k in enumerate(cols):d[k]=pr[:,j]
 d['shape']=d.shape_code.map({0:'D',1:'P',2:'b',3:'B'});d['legacy_shape']=np.argmax(d[[f'profile_shape_{j}' for j in range(4)]].to_numpy(),axis=1);d['legacy_shape']=d.legacy_shape.map({0:'D',1:'P',2:'b',3:'DOUBLE'})
 for orig,new in [('poc','POC_HVN'),('val','VAL'),('vah','VAH')]:
  expected=d.close-d[f'profile_dist_{orig}']*d.atr;mask=d[new].notna()&expected.notna();assert np.allclose(d.loc[mask,new],expected[mask],rtol=1e-9,atol=1e-6)
 with zipfile.ZipFile(DATA/'BTCUSDT_flow_2021-01-2026-08.csv.zip') as z:f=pd.read_csv(z.open('BTCUSDT_flow.csv'))
 f=f.drop_duplicates();f.index=pd.to_datetime(f.create_time,utc=True)+pd.Timedelta(minutes=5);d['oi_quantity']=f.sum_open_interest.where(f.sum_open_interest>0).reindex(d.index)
 # Prefix causality is checked numerically for every node, including revised B.
 pref=profile_nodes(*[d[k].iloc[:1900].to_numpy(float) for k in ['high','low','close','volume']]);assert np.allclose(pref,pr[:1900],equal_nan=True)
 d['trend_side']=np.select([d.ret_72>.5,d.ret_72<-.5],[1,-1],default=0);d=d.replace([np.inf,-np.inf],np.nan);d.to_pickle(O/'LAB162_tape.pkl')
 audit={'nonpositive_oi_rows_masked':int((f.sum_open_interest.reindex(d.index)<=0).sum()),'nonfinite_derived_features_masked':True,'rows':len(d),'start':str(d.index.min()),'end':str(d.index.max()),'profile_node_prefix_invariance':True,'poc_val_vah_lab161_parity':True,'B_definition':'separated smoothed peaks>=6bins,second>=0.7primary,valley<=0.7smallerpeak','structural_shape_counts':d['shape'].value_counts().to_dict(),'legacy_shape_counts':d.legacy_shape.value_counts().to_dict(),'hvn2_rows':int(d.HVN2.notna().sum()),'lvn_rows':int(d.LVN.notna().sum()),'source_lineage':json.loads((R/'results/LAB161_20261010/LAB161_data_audit.json').read_text())['sources']};(O/'LAB162_data_audit.json').write_text(json.dumps(audit,indent=2));print(json.dumps(audit),flush=True)
if __name__=='__main__':main()
