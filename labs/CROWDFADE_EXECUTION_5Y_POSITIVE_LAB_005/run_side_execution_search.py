import json,itertools
from pathlib import Path
import numpy as np
from numba import njit
import run_search_v2 as b
OUT=Path(__file__).resolve().parent/'output'

@njit(cache=True)
def run_side(ts,O,H,L,C,Z,A,Y,D,confirm,ttl_h,mode,stop_atr,hold_h,pause,side_filter):
    sums=np.zeros(5);counts=np.zeros(5,np.int64);n=0;wins=0;pos_sum=0.;neg_sum=0.;eq=0.;peak_eq=0.;maxdd=0.;i=0;next_ts=0;last_entry=0.;last_atr=0.;has_last=False;cur_day=-1;day_count=0;N=len(ts)
    while i<N-3:
        if ts[i]<next_ts:i+=1;continue
        if D[i]!=cur_day:cur_day=D[i];day_count=0
        if day_count>=b.MAXDAY:i+=1;continue
        z=Z[i];side=-1 if z>=b.ZTH else (1 if z<=-b.ZTH else 0)
        if side==0 or side!=side_filter:i+=1;continue
        if pause==2 and has_last and abs(O[i]-last_entry)<last_atr:i+=1;continue
        atr=A[i];level=O[i]+side*confirm*atr;end=min(N-3,i+int(ttl_h*12));ci=-1
        for j in range(i+1,end+1):
            if (side>0 and H[j]>=level) or (side<0 and L[j]<=level):ci=j;break
        if ci<0:i+=1;continue
        ei=ci;entry=level
        if mode==1:entry=C[ci]
        elif mode==2:ei=ci+1;entry=O[ei]
        elif mode==3 or mode==4:
            retr=.25 if mode==3 else .50;target=level-side*retr*atr;ei=-1
            for j in range(ci,min(N-3,ci+12)+1):
                if (side>0 and L[j]<=target) or (side<0 and H[j]>=target):ei=j;entry=target;break
            if ei<0:i=ci+1;continue
        if D[ei]!=cur_day:cur_day=D[ei];day_count=0
        if day_count>=b.MAXDAY:i=ei+1;continue
        sl=entry-side*stop_atr*atr;xe=min(N-1,ei+int(hold_h*12));xp=C[xe];exit_i=xe
        for j in range(ei+1,xe+1):
            if (side>0 and L[j]<=sl) or (side<0 and H[j]>=sl):xp=sl;exit_i=j;break
            if (side<0 and Z[j]<=-b.EXIT_Z) or (side>0 and Z[j]>=b.EXIT_Z):xp=C[j];exit_i=j;break
        R=side*(xp-entry)/(stop_atr*atr)-(b.COST_BPS/10000.)*entry/(stop_atr*atr);yi=Y[ei]-2021
        if 0<=yi<5:sums[yi]+=R;counts[yi]+=1
        n+=1
        if R>0:wins+=1;pos_sum+=R
        elif R<0:neg_sum-=R
        eq+=R
        if eq>peak_eq:peak_eq=eq
        dd=peak_eq-eq
        if dd>maxdd:maxdd=dd
        day_count+=1;last_entry=entry;last_atr=atr;has_last=True;next_ts=ts[exit_i]+(10800 if pause==1 else 300);i=exit_i+1
    return sums,counts,n,eq,(eq/n if n else -999.),(pos_sum/neg_sum if neg_sum else 99.),maxdd,(wins/n if n else 0.)

def make_rec(params,res,side):
    c,t,m,sl,h,p=params;sums,counts,n,total,ev,pf,dd,wr=res
    ann={str(2021+i):{'SumR':float(sums[i]),'N':int(counts[i]),'EV':float(sums[i]/counts[i]) if counts[i] else 0.} for i in range(5)}
    return {'side':'LONG' if side==1 else 'SHORT','confirm':c,'ttl_h':t,'mode':b.MODE_NAMES[m],'stop':sl,'hold_h':h,'pause':b.PAUSE_NAMES[p],'positive_years':int(np.sum(sums>0)),'annual':ann,'agg':{'N':int(n),'SumR':float(total),'EV':float(ev),'PF':float(pf),'MaxDD':float(dd),'WR':float(wr)},'score':[float(np.min(sums)),float(np.median(sums)),float(total/max(dd,1e-9)),float(ev)]}

def main():
    p=b.prepare();ts=p.ts.to_numpy(np.int64);O=p.o.to_numpy(float);H=p.h.to_numpy(float);L=p.l.to_numpy(float);C=p.c.to_numpy(float);Z=p.z.to_numpy(float);A=p.atr.to_numpy(float);Y=p.year.to_numpy(np.int64);D=p.day.to_numpy(np.int64)
    out={}
    for side in [1,-1]:
        rows=[]
        for params in itertools.product(b.CONFIRMS,b.TTLS,b.MODES,b.STOPS,b.HOLDS,b.PAUSES):
            rows.append(make_rec(params,run_side(ts,O,H,L,C,Z,A,Y,D,*params,side),side))
        rows.sort(key=lambda x:(x['positive_years'],x['score']),reverse=True)
        perfect=[r for r in rows if r['positive_years']==5 and r['agg']['N']>=75]
        out['LONG' if side==1 else 'SHORT']={'tested':len(rows),'perfect_count':len(perfect),'best':rows[0],'perfect_top20':perfect[:20],'near_top20':[r for r in rows if r['positive_years']<5][:20]}
        print('SIDE',side,'perfect',len(perfect),'best',rows[0])
    (OUT/'side_execution_search.json').write_text(json.dumps(out,indent=2))
if __name__=='__main__':main()
