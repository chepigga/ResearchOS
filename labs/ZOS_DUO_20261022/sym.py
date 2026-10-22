import pandas as pd,numpy as np
m15=pd.read_pickle("m15.pkl"); d1=pd.read_pickle("d1.pkl"); h1=pd.read_pickle("h1.pkl"); c=d1.close
mv=c.groupby(d1.index.to_period("M")).agg(lambda s:(s.iloc[-1]/s.iloc[0]-1)*100)
o,h,l,cl=[m15[x].values for x in ("open","high","low","close")]; sp=m15.spread.values/100+0.1
tr=pd.concat([m15.high-m15.low,(m15.high-m15.close.shift()).abs(),(m15.low-m15.close.shift()).abs()],axis=1).max(axis=1)
A=tr.rolling(14).mean().values; mon=m15.index.to_period("M"); mvm=mv.reindex(mon).values
idx=np.arange(200,len(m15)-200,4)
res=[]
for i in idx:
    a=A[i]
    if np.isnan(a) or np.isnan(mvm[i]): continue
    R=2.2*a; e=o[i+1]
    for s in (1,-1):
        for tp in (1,2):
            st=e-s*R; tg=e+s*tp*R; out=None
            for j in range(i+1,min(i+97,len(m15))):
                if (s>0 and l[j]<=st) or (s<0 and h[j]>=st): out=-1; break
                if (s>0 and h[j]>=tg) or (s<0 and l[j]<=tg): out=tp; break
            if out is None: out=s*(cl[min(i+96,len(m15)-1)]-e)/R
            res.append((mon[i],mvm[i],s,tp,out-sp[i]/R))
X=pd.DataFrame(res,columns=["m","mv","s","tp","R"]); X.to_pickle("sym.pkl")
