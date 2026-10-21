import pandas as pd,numpy as np,itertools
m15=pd.read_pickle("m15.pkl"); h1=pd.read_pickle("h1.pkl"); d1=pd.read_pickle("d1.pkl")
def prep(b):
    b=b.copy(); c=b.close
    tr=pd.concat([b.high-b.low,(b.high-c.shift()).abs(),(b.low-c.shift()).abs()],axis=1).max(axis=1)
    b["atr"]=tr.rolling(14).mean(); b["cost"]=b.spread/100+0.10
    d=c.diff(); 
    for n in (2,14):
        up=d.clip(lower=0).ewm(alpha=1/n).mean(); dn=(-d.clip(upper=0)).ewm(alpha=1/n).mean(); b[f"rsi{n}"]=100-100/(1+up/dn)
    for n in (20,50):
        b[f"ma{n}"]=c.rolling(n).mean(); b[f"sd{n}"]=c.rolling(n).std()
        b[f"hh{n}"]=b.high.rolling(n).max().shift(1); b[f"ll{n}"]=b.low.rolling(n).min().shift(1)
    dd=d1.reindex(b.index.normalize()); 
    pdh=d1.high.shift(1).reindex(b.index.normalize()); pdl=d1.low.shift(1).reindex(b.index.normalize())
    b["pdh"]=pdh.values; b["pdl"]=pdl.values
    return b
B={"M15":prep(m15),"H1":prep(h1)}
def run(b,sig,s_atr,tgt,hold,mode):
    """sig: +1/-1 at bar close (array); entry next open. tgt: 'ma'->ma20, number->R multiple"""
    o,h,l,c,a,cost,ma=[b[x].values for x in ("open","high","low","close","atr","cost","ma20")]
    idx=b.index; res=[]; i=0; n=len(b)
    while i<n-1:
        s=sig[i]
        if s==0 or np.isnan(a[i]): i+=1; continue
        e=o[i+1]; R=s_atr*a[i]; st=e-s*R
        tp=(ma[i] if tgt=="ma" else e+s*tgt*R)
        if tgt=="ma" and s*(tp-e)<=0.2*R: i+=1; continue
        j=i+1; out=None
        while j<n and j<=i+hold:
            if (s>0 and l[j]<=st) or (s<0 and h[j]>=st): out=-R; break
            if (s>0 and h[j]>=tp) or (s<0 and l[j]<=tp): out=s*(tp-e); break
            j+=1
        if out is None: j=min(j,n-1); out=s*(c[j]-e)
        res.append((idx[i+1],(out-cost[i])/R)); i=j+1
    return res
strats=[]
for tf in ("M15","H1"):
    b=B[tf]; c=b.close.values
    for n,k in itertools.product((20,50),(1.5,2.0,2.5)):
        z=(b.close-b[f"ma{n}"])/b[f"sd{n}"]
        strats.append((tf,f"BB{n},{k} фейд",np.where(z>k,-1,np.where(z<-k,1,0))))
        strats.append((tf,f"BB{n},{k} пробій",np.where(z>k,1,np.where(z<-k,-1,0))))
    for n,(lo,hi) in itertools.product((2,14),((10,90),(20,80),(30,70))):
        if n==14 and lo==10: continue
        r=b[f"rsi{n}"].values; strats.append((tf,f"RSI{n} {lo}/{hi} фейд",np.where(r>hi,-1,np.where(r<lo,1,0))))
    for n in (20,50):
        strats.append((tf,f"Donchian{n} фейд",np.where(b.high.values>b[f"hh{n}"].values,-1,np.where(b.low.values<b[f"ll{n}"].values,1,0))))
        strats.append((tf,f"Donchian{n} пробій",np.where(b.close.values>b[f"hh{n}"].values,1,np.where(b.close.values<b[f"ll{n}"].values,-1,0))))
    strats.append((tf,"PDH/PDL фейд",np.where(b.high.values>b.pdh.values,-1,np.where(b.low.values<b.pdl.values,1,0))))
    strats.append((tf,"PDH/PDL пробій",np.where(b.close.values>b.pdh.values,1,np.where(b.close.values<b.pdl.values,-1,0))))
exits=[(s,t,hd) for s in (1.0,2.0) for t in ("ma",1.0,2.0) for hd in (8,24)]
rows=[]
for tf,nm,sig in strats:
    b=B[tf]; m=(b.index>="2026-10-01"); st=np.argmax(m)-200
    bb=b.iloc[st:]; sg=sig[st:].copy(); sg[:200]=0
    for s,t,hd in exits:
        r=run(bb,sg,s,t,hd,0)
        if len(r)>=6: rows.append((tf,nm,s,t,hd,len(r),sum(x for _,x in r),np.mean([x>0 for _,x in r])))
O=pd.DataFrame(rows,columns=["tf","strat","stopATR","tgt","hold","n","sumR","win"]).sort_values("sumR",ascending=False)
O.to_pickle("oct_grid.pkl"); pd.set_option("display.width",200)
print(len(O),"варіантів; прибуткових:",(O.sumR>0).sum()); print(O.head(25).round(2).to_string(index=False))
