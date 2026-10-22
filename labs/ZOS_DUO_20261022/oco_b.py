import pandas as pd,numpy as np
m15=pd.read_pickle("m15.pkl"); d1=pd.read_pickle("d1.pkl"); dW=d1[d1.index.dayofweek<5]
c=dW.close; tr=pd.concat([dW.high-dW.low,(dW.high-c.shift()).abs(),(dW.low-c.shift()).abs()],axis=1).max(axis=1); atr=tr.rolling(14).mean().shift(1)
G={d:x for d,x in m15.groupby(m15.index.normalize())}
rows=[]
for d,x in G.items():
    if d not in atr.index or np.isnan(atr[d]) or d.dayofweek>4: continue
    A=atr[d]; hr=x.index.hour; bx=x[(hr>=1)&(hr<9)]; ac=x[(hr>=9)&(hr<21)]
    if len(bx)<20 or len(ac)<20: continue
    H,L=bx.high.max(),bx.low.min(); up,dn=H+0.1*A,L-0.1*A; hit=None
    for t,hh,ll in zip(ac.index,ac.high,ac.low):
        u=hh>=up; v=ll<=dn
        if u and v: break
        if u: hit=(1,t); break
        if v: hit=(-1,t); break
    if hit is None: continue
    s,t0=hit; e=up if s>0 else dn; st=dn if s>0 else up; R=abs(e-st); cost=x.spread.mean()/100+0.1
    for tp in (2.0,3.0,"EOD"):
        tg=e+s*tp*R if tp!="EOD" else None; res=None
        after=x[x.index>=t0]
        for i,(t,hh,ll,cl) in enumerate(zip(after.index,after.high,after.low,after.close)):
            if (s>0 and ll<=st) or (s<0 and hh>=st): res=-R; break
            if i>0 and tg is not None and ((s>0 and hh>=tg) or (s<0 and ll<=tg)): res=tp*R; break
            if t.hour>=22: res=s*(cl-e); break
        if res is None: res=s*(after.close.iloc[-1]-e)
        rows.append((d,s,str(tp),(res-cost)/R,R))
O=pd.DataFrame(rows,columns=["d","s","tp","R","risk"]); O.to_pickle("oco_b.pkl")
