from pathlib import Path
import sys,json,hashlib,zipfile,importlib.util
import numpy as np,pandas as pd
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parents[2]; O=R/'results/LAB164_20261010';O.mkdir(exist_ok=True)

def profile(d,s,e):
 q=d.iloc[s:e+1];lo=q.low.min();hi=q.high.max();edges=np.linspace(lo,hi,41);v=np.zeros(40)
 for h,l,c,vol in q[['high','low','close','volume']].to_numpy():
  if h>l:v+=vol*np.maximum(0,np.minimum(edges[1:],h)-np.maximum(edges[:-1],l))/(h-l)
  else:v[min(39,max(0,np.searchsorted(edges,c)-1))]+=vol
 p=int(v.argmax());left=right=p;mass=v[p]
 while mass<.7*v.sum() and (left>0 or right<39):
  if (v[right+1] if right<39 else -1)>=(v[left-1] if left>0 else -1):right+=1;mass+=v[right]
  else:left-=1;mass+=v[left]
 smooth=np.array([v[max(0,k-1):min(40,k+2)].mean() for k in range(40)]);primary=int(smooth.argmax());peaks=[k for k in range(1,39) if abs(k-primary)>=6 and smooth[k]>=smooth[k-1] and smooth[k]>smooth[k+1] and smooth[k]>=.5*smooth[primary]]
 secondary=max(peaks,key=lambda k:smooth[k]) if peaks else None;shape='D';hvn2=lvn=np.nan
 if secondary is not None:
  hvn2=(edges[secondary]+edges[secondary+1])/2;a,b=sorted([primary,secondary]);valley=a+smooth[a:b+1].argmin();depth=smooth[valley]/min(smooth[primary],smooth[secondary])
  if depth<=.7:lvn=(edges[valley]+edges[valley+1])/2
  if depth<=.7 and smooth[secondary]>=.7*smooth[primary]:shape='B'
 if shape!='B':
  if p+.5>=80/3 and v[27:].sum()>1.15*v[:13].sum():shape='P'
  elif p+.5<=40/3 and v[:13].sum()>1.15*v[27:].sum():shape='b'
 assert np.isclose(v.sum(),q.volume.sum(),rtol=1e-9)
 return dict(poc=(edges[p]+edges[p+1])/2,val=edges[left],vah=edges[right+1],hvn2=hvn2,lvn=lvn,shape=shape,profile_volume=v.sum())

def detect(d):
 b=d.resample('1h',closed='right',label='right').agg({'high':'max','low':'min','close':'last'});counts=d.close.resample('1h',closed='right',label='right').count();b.loc[counts!=12]=np.nan
 seeds={}
 for k in range(5,len(b)):
  q=b.iloc[k-5:k+1];t=b.index[k];i=d.index.get_indexer([t])[0]
  if i<0 or q.isna().any().any():continue
  a=d.atr.iloc[i];lo=q.low.min();hi=q.high.max();w=hi-lo;c=q.close.to_numpy();path=np.abs(np.diff(c)).sum();eff=abs(c[-1]-c[0])/path if path else 0;mid=(hi+lo)/2;cross=np.sum((c[:-1]-mid)*(c[1:]-mid)<0)
  if np.isfinite(a) and 1<=w/a<=4 and eff<=.35 and cross>=3 and (c<=lo+w/3).sum()>=2 and (c>=hi-w/3).sum()>=2:
   seeds[i]=dict(start=i-71,det=i,lo=lo,hi=hi,atr=a,width_atr=w/a,efficiency=eff,crossings=int(cross))
 c=d.close.to_numpy();h=d.high.to_numpy();l=d.low.to_numpy();rows=[];signals=[];p=None;minstart=0
 for i in range(len(d)):
  if p is None:
   if i in seeds and seeds[i]['start']>=minstart:p=seeds[i].copy();p['id']=len(rows);p['break_i']=-1
   continue
  if p['break_i']<0:
   sd=1 if c[i]>p['hi']+.1*p['atr'] else (-1 if c[i]<p['lo']-.1*p['atr'] else 0)
   if i-p['det']>288:
    p.update(end=i,status='EXPIRED');rows.append(p);p=None;minstart=i+1;continue
   if sd:
    p.update(break_i=i,side=sd,boundary=p['hi'] if sd==1 else p['lo'],extreme=h[i] if sd==1 else l[i]);p.update(profile(d,p['start'],i-1));signals.append(dict(id=p['id'],stage='BREAKOUT',i=i,side=sd,stop=p['boundary']-sd*.1*p['atr'],target=p['boundary']+sd*(p['hi']-p['lo'])))
   continue
  sd=p['side'];dist=sd*(c[i]-p['boundary'])/p['atr'];prev=sd*(c[i-1]-p['boundary'])/p['atr'];p['extreme']=max(p['extreme'],h[i]) if sd==1 else min(p['extreme'],l[i])
  if i-p['break_i']>72:
   p.update(end=i,status='UNCONFIRMED');rows.append(p);p=None;minstart=i+1;continue
  touch=(l[i-1]<=p['boundary']+.1*p['atr'] and h[i-1]>=p['boundary']-.1*p['atr'])
  stage='FAILED_RETURN' if i>=p['break_i']+2 and dist<=-.1 and prev<=-.1 else ('RETEST_HOLD' if i>=p['break_i']+2 and touch and prev>=.1 and dist>=.1 else None)
  if stage:
   direction=-sd if stage=='FAILED_RETURN' else sd;stop=p['extreme']+sd*.1*p['atr'] if stage=='FAILED_RETURN' else p['boundary']-sd*.1*p['atr'];target=p['poc'] if stage=='FAILED_RETURN' else p['boundary']+sd*(p['hi']-p['lo']);signals.append(dict(id=p['id'],stage=stage,i=i,side=direction,stop=stop,target=target));p.update(end=i,status=stage);rows.append(p);p=None;minstart=i+1
 if p is not None:p.update(end=len(d)-1,status='CENSORED');rows.append(p)
 return pd.DataFrame(rows),pd.DataFrame(signals)

def prepare():
 d=pd.read_pickle(R/'results/LAB162_20261010/LAB162_tape.pkl');b,s=detect(d);b.to_csv(O/'balances.csv',index=False);s.to_csv(O/'signals_unlabelled.csv',index=False)
 cut=min(len(d),120000);bp,sp=detect(d.iloc[:cut]);full=b[b.end<cut-1].drop(columns=['profile_volume'],errors='ignore').reset_index(drop=True);pre=bp[bp.end<cut-1].drop(columns=['profile_volume'],errors='ignore').reset_index(drop=True);pd.testing.assert_frame_equal(full,pre,check_dtype=False)
 assert (b.start<b.det).all();broken=b[b.break_i>=0];assert (broken.det<broken.break_i).all();assert b.start.iloc[1:].to_numpy().min()>=0
 figs,axs=plt.subplots(3,2,figsize=(16,11));examples=[]
 for year,ax in zip(range(2021,2027),axs.flat):
  q=broken[d.index[broken.det.astype(int)].year==year];r=q.iloc[np.abs(q.width_atr-q.width_atr.median()).argmin()];a=int(r.start);z=min(len(d)-1,int(r.end)+36);t=d.index[a:z+1];ax.plot(t,d.close.iloc[a:z+1],lw=.85,color='#24394b');ax.axvspan(d.index[a],d.index[int(r.det)],alpha=.12,color='gray');ax.axvline(d.index[int(r.det)],color='gray',ls=':');ax.axvline(d.index[int(r.break_i)],color='purple',ls=':')
  for name,color in [('lo','orange'),('hi','orange'),('poc','blue'),('val','green'),('vah','green')]:ax.hlines(r[name],d.index[int(r.break_i)],t[-1],color=color,lw=.9,label=name)
  for _,v in s[s.id==r.id].iterrows():ax.scatter(d.index[int(v.i)],d.close.iloc[int(v.i)],s=35,label=v.stage)
  ax.set_title(f'{year} | balance {int(r.id)} | shape {r["shape"]}');ax.tick_params(axis='x',rotation=20);ax.legend(fontsize=6,ncol=3);examples.append(int(r.id))
 figs.suptitle('LAB164 causal balance annotations — examples selected without future outcomes');figs.tight_layout();figs.savefig(O/'annotation_audit.png',dpi=140);plt.close(figs)
 (O/'annotation_validation.json').write_text(json.dumps(dict(prefix_invariance=True,volume_conservation=True,examples=examples,balances=len(b),signals=len(s),statuses=b.status.value_counts().to_dict()),indent=2));print((O/'annotation_validation.json').read_text())
if __name__=='__main__':prepare()
