from pathlib import Path
import pandas as pd,numpy as np
R=Path(__file__).resolve().parents[2];O=R/'results/LAB162_20261010';LEVELS=['POC_HVN','VAL','VAH','HVN2','LVN']
def main():
 d=pd.read_pickle(O/'LAB162_tape.pkl');waves=pd.read_csv(R/'results/LAB161_20261010/LAB161_waves.csv',parse_dates=['start','peak','end']);rows=[];summ=[];micro=[]
 for w in waves.itertuples():
  i=d.index.get_indexer([w.start])[0];j=d.index.get_indexer([w.peak])[0]
  if i<1 or pd.isna(d.POC_HVN.iloc[i-1]):continue
  st=d.iloc[i];pk=d.iloc[j];fixed=d.iloc[i-1];side=w.side;prior=int(st.trend_side);kind='CONT' if prior==side else ('REV' if prior==-side else 'FLAT');v=d.iloc[i:j+1];path=side*(v.close.to_numpy()-st.close)/st.atr;dd=np.maximum.accumulate(path)-path
  rec=dict(move_id=w.move_id,definition=w.definition,year=w.start.year,start=w.start,peak=w.peak,end=w.end,side=side,kind=kind,amplitude_atr=w.amplitude_atr,duration_h=w.duration_h,shape_start=st['shape'],shape_peak=pk['shape'],shape_frozen=fixed['shape'],oi_change_pct=100*(pk.oi_quantity/st.oi_quantity-1),ratio_change_pct=100*(pk.ratio/st.ratio-1),z_change=pk.crowd_z-st.crowd_z,poc_migration_atr=side*(pk.POC_HVN-fixed.POC_HVN)/st.atr,efficiency=abs(path[-1])/max(np.abs(np.diff(path)).sum(),1e-9),max_pullback_atr=dd.max())
  for level in LEVELS:
   rec[f'peak_dist_fixed_{level}']=abs(pk.close-fixed[level])/pk.atr;rec[f'peak_dist_prior_{level}']=abs(pk.close-d.iloc[j-1][level])/pk.atr
  summ.append(rec)
  points=[]
  for anchor,idx in [('START',i),('PEAK',j)]:
   for hours in [-12,-6,-3,-1,0,.5,1,3,6,12]:points.append((anchor,str(hours),idx+int(hours*12)))
  for frac in [.25,.5,.75]:points.append(('FRACTION',str(frac),i+int(round((j-i)*frac))))
  for anchor,pos,k in points:
   if k<0 or k>=len(d):continue
   r=d.iloc[k];rr=dict(move_id=w.move_id,definition=w.definition,year=w.start.year,side=side,kind=kind,anchor=anchor,position=pos,time=d.index[k],price_from_start_atr=side*(r.close-st.close)/st.atr,price_from_peak_atr=side*(r.close-pk.close)/pk.atr,oi_from_start_pct=100*(r.oi_quantity/st.oi_quantity-1),ratio_from_start_pct=100*(r.ratio/st.ratio-1),z_aligned=side*r.crowd_z,speed30m_atr=side*r.ret_6,oi4h_pct=100*r.oi_change_48,shape=r['shape'],poc_move_from_frozen_atr=side*(r.POC_HVN-fixed.POC_HVN)/st.atr)
   for level in LEVELS:rr[f'dist_dynamic_{level}']=side*(r.close-r[level])/r.atr;rr[f'dist_fixed_{level}']=side*(r.close-fixed[level])/r.atr
   rows.append(rr)
  # Internal directional-change sublegs, fixed 0.5 starting-waveATR; final segment is retrospective.
  c=v.close.to_numpy();start=0;ext=0;direction=0;segments=[]
  for k in range(1,len(c)):
   if direction==0:
    if abs(c[k]-c[start])>=.5*st.atr:direction=1 if c[k]>c[start] else -1;ext=k
   elif direction*(c[k]-c[ext])>0:ext=k
   elif direction*(c[ext]-c[k])>=.5*st.atr:segments.append((start,ext,direction));start=ext;direction=-direction;ext=k
  if direction and ext>start:segments.append((start,ext,direction))
  for a,b,dr in segments:
   aa=v.iloc[a];bb=v.iloc[b];micro.append(dict(move_id=w.move_id,definition=w.definition,kind=kind,wave_side=side,start=v.index[a],end=v.index[b],role='IMPULSE' if dr==side else 'PULLBACK',side=dr,amplitude_start_atr=abs(bb.close-aa.close)/st.atr,duration_minutes=(b-a)*5,oi_change_pct=100*(bb.oi_quantity/aa.oi_quantity-1),ratio_change_pct=100*(bb.ratio/aa.ratio-1),shape_start=aa['shape'],shape_end=bb['shape']))
 a=pd.DataFrame(rows);q=pd.DataFrame(summ);m=pd.DataFrame(micro);a.to_csv(O/'LAB162_wave_trajectories.csv',index=False);q.to_csv(O/'LAB162_wave_anatomy.csv',index=False);m.to_csv(O/'LAB162_internal_legs.csv',index=False)
 metrics=['price_from_start_atr','price_from_peak_atr','oi_from_start_pct','ratio_from_start_pct','z_aligned','speed30m_atr','oi4h_pct','poc_move_from_frozen_atr'];z=a.groupby(['definition','side','kind','anchor','position'])[metrics].agg(['count','median',lambda x:x.quantile(.25),lambda x:x.quantile(.75)]);z.columns=['_'.join(c).replace('<lambda_0>','q25').replace('<lambda_1>','q75') for c in z.columns];z.reset_index().to_csv(O/'LAB162_trajectory_summary.csv',index=False)
 t=q.groupby(['definition','side','kind','shape_start','shape_peak']).agg(n=('move_id','size'),duration_median=('duration_h','median'),oi_pct_median=('oi_change_pct','median'),poc_move_median=('poc_migration_atr','median')).reset_index();t.to_csv(O/'LAB162_shape_transitions.csv',index=False)
 print('WAVES',len(q),'ALIGNED',len(a),'INTERNAL',len(m),flush=True)
if __name__=='__main__':main()
