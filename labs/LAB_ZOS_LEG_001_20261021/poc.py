import pandas as pd,numpy as np,itertools,sys
m1=pd.read_pickle("m1b.pkl"); m5=pd.read_pickle("m5.pkl"); d1=pd.read_pickle("d1.pkl")
c=d1.close
er20=((c-c.shift(20)).abs()/c.diff().abs().rolling(20).sum()).shift(1)   # known before day
tr=pd.concat([d1.high-d1.low,(d1.high-c.shift()).abs(),(d1.low-c.shift()).abs()],axis=1).max(axis=1)
atr=tr.rolling(14).mean().shift(1)
days=d1.index[25:]
m1d=m1.index.normalize(); m5d=m5.index.normalize()
g1={d:x for d,x in m1.groupby(m1d)}; g5={d:x for d,x in m5.groupby(m5d)}
def profile(dd,step=0.5):
    x=pd.concat([g1[d] for d in dd if d in g1])
    lo=np.floor(x.low.min()/step)*step; nb=int((x.high.max()-lo)/step)+2
    h=np.zeros(nb)
    a=((x.low.values-lo)/step).astype(int); b=((x.high.values-lo)/step).astype(int)
    for i,j in zip(a,b): h[i:j+1]+=1.0/(j-i+1)
    p=int(h.argmax()); tot=h.sum(); L=R=p; acc=h[p]
    while acc<0.7*tot:
        l=h[L-1] if L>0 else -1; r=h[R+1] if R<nb-1 else -1
        if r>=l: R+=1; acc+=h[R]
        else: L-=1; acc+=h[L]
    return lo+p*step, lo+R*step, lo+L*step   # POC VAH VAL
prof={}
for N in (1,5):
    for i,d in enumerate(days):
        prev=list(d1.index[d1.index.get_loc(d)-N:d1.index.get_loc(d)])
        prof[(N,d)]=profile(prev)
pd.to_pickle(prof,"prof.pkl")
