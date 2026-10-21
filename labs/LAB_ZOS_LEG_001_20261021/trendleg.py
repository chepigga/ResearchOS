import pandas as pd,numpy as np
h1=pd.read_pickle("h1.pkl"); d1=pd.read_pickle("d1.pkl")
agg={"open":"first","high":"max","low":"min","close":"last","spread":"mean"}
h4=h1.resample("4h").agg(agg).dropna()
def atr(b,n=14):
    c=b.close; tr=pd.concat([b.high-b.low,(b.high-c.shift()).abs(),(b.low-c.shift()).abs()],axis=1).max(axis=1); return tr.rolling(n).mean()
SWAP_PER_DAY_PCT=0.012  # приблизна ціна свопу, % ціни за добу (оцінка з ноги G: -2.4k на +5.3k)
def donchian(b,n,trail,maxdays,name):
    a=atr(b).values; o,h,l,c=b.open.values,b.high.values,b.low.values,b.close.values
    hh=b.high.rolling(n).max().shift(1).values; ll=b.low.rolling(n).min().shift(1).values; idx=b.index; out=[]; i=n+15
    while i<len(b)-1:
        s=1 if c[i]>hh[i] else (-1 if c[i]<ll[i] else 0)
        if s==0 or np.isnan(a[i]): i+=1; continue
        e=o[i+1]; R=trail*a[i]; st=e-s*R; j=i+1; best=e; res=None
        while j<len(b):
            if (s>0 and l[j]<=st) or (s<0 and h[j]>=st): res=s*(min(o[j],st) if s>0 else max(o[j],st))-s*e; break
            best=max(best,h[j]) if s>0 else min(best,l[j]); ns=best-s*trail*a[j]
            st=max(st,ns) if s>0 else min(st,ns)
            if (idx[j]-idx[i+1]).total_seconds()>maxdays*86400: res=s*(c[j]-e); break
            j+=1
        if res is None: break
        days=(idx[min(j,len(b)-1)]-idx[i+1]).total_seconds()/86400
        cost=b.spread.values[i]/100+0.10+e*SWAP_PER_DAY_PCT/100*days
        out.append((idx[i+1],s,(res-cost)/R,days)); i=j+1
    return pd.DataFrame(out,columns=["t","s","R","days"]).assign(name=name)
def ema_d1(fast,slow,name):
    b=d1; ef=b.close.ewm(span=fast).mean(); es=b.close.ewm(span=slow).mean(); sig=np.sign(ef-es).shift(1)
    a=atr(b).shift(1); out=[]; pos=0
    for k in range(slow,len(b)):
        s=sig.iloc[k]
        if s!=pos and s!=0:
            pos=s; e=b.open.iloc[k]; et=b.index[k]; R=2*a.iloc[k]
            # hold until signal flips
            kk=k+1
            while kk<len(b) and sig.iloc[kk]==s: kk+=1
            x=b.open.iloc[min(kk,len(b)-1)]; days=(b.index[min(kk,len(b)-1)]-et).days
            out.append((et,s,(s*(x-e)-0.5-e*SWAP_PER_DAY_PCT/100*days)/R,days))
    return pd.DataFrame(out,columns=["t","s","R","days"]).assign(name=name)
T=pd.concat([donchian(h4,20,3.0,10,"H4 Donchian20 трейл 3ATR"),donchian(h4,55,3.0,20,"H4 Donchian55 трейл 3ATR"),
             donchian(h1,48,3.0,5,"H1 Donchian48 трейл 3ATR"),ema_d1(20,50,"D1 EMA20/50")])
A=pd.read_pickle("algoT.pkl")[["t","s","R"]].assign(name="AlgoSignals-копія M15",days=0.5)
T=pd.concat([T,A]); T.to_pickle("trendT.pkl")
