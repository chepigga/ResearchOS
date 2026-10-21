import pandas as pd,numpy as np,itertools
m5=pd.read_pickle("m5.pkl"); d1=pd.read_pickle("d1.pkl")
c=d1.close; er=((c-c.shift(20)).abs()/c.diff().abs().rolling(20).sum()).shift(1)
tr=pd.concat([d1.high-d1.low,(d1.high-c.shift()).abs(),(d1.low-c.shift()).abs()],axis=1).max(axis=1); atr=tr.rolling(14).mean().shift(1)
G={d:x for d,x in m5.groupby(m5.index.normalize())}
boxes={"Азія 01-09 → 09-20":(1,9,20),"перед Лондоном 07-10 → 10-20":(7,10,20),"перед NY 13-16 → 16-21":(13,16,21),"перша година 01-02 → 02-20":(1,2,20)}
rows=[]
for d,x in G.items():
    if d not in atr.index or np.isnan(atr[d]): continue
    A=atr[d]; hr=x.index.hour
    for bn,(a,b,e) in boxes.items():
        bx=x[(hr>=a)&(hr<b)]; ac=x[(hr>=b)&(hr<e)]; tail=x[hr>=b]
        if len(bx)<6 or len(ac)<6: continue
        H,L=bx.high.max(),bx.low.min(); W=H-L
        if W<=0.05*A: continue
        for buf in (0.0,0.1):
            up=H+buf*A; dn=L-buf*A
            # first trigger
            hit=None
            for t,(hh,ll) in zip(ac.index,ac[["high","low"]].values):
                u=hh>=up; v=ll<=dn
                if u and v: hit=None; break
                if u: hit=(1,t); break
                if v: hit=(-1,t); break
            if hit is None: continue
            s,t0=hit; e0=up if s>0 else dn
            after=tail[tail.index>t0]; cost=x.spread.mean()/100+0.10
            for slm in ("протилежна межа","середина"):
                st=(dn if s>0 else up) if slm=="протилежна межа" else (H+L)/2
                R=abs(e0-st)
                for tp in (1.0,2.0,3.0,None):
                    tg=e0+s*tp*R if tp else None; res=None
                    # fill bar: stop check only
                    fb=ac.loc[t0]
                    if (s>0 and fb.low<=st) or (s<0 and fb.high>=st): res=-R
                    else:
                        for hh,ll,cl,tt in zip(after.high,after.low,after.close,after.index):
                            if tt.hour>=21 and tt.minute>=45 or tt.hour>=22: res=s*(cl-e0); break
                            if (s>0 and ll<=st) or (s<0 and hh>=st): res=-R; break
                            if tg and ((s>0 and hh>=tg) or (s<0 and ll<=tg)): res=tp*R; break
                        if res is None: res=s*(after.close.iloc[-1]-e0) if len(after) else 0
                    rows.append((d,bn,buf,slm,tp if tp else "кінець дня",(res-cost)/R,W/A))
T=pd.DataFrame(rows,columns=["d","box","buf","sl","tp","R","W/A"])
T["reg"]=er.reindex(T.d).values<0.2; T["h"]=np.where(T.d<"2024-07-01","A","B"); T["m"]=T.d.dt.to_period("M")
T.to_pickle("ocoT.pkl")
