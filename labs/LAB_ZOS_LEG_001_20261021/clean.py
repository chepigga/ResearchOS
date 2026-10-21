import pandas as pd,numpy as np
exec(open("octs.py").read().split("exits=")[0])
c=d1.close; H=d1.high; L=d1.low
tr=pd.concat([H-L,(H-c.shift()).abs(),(L-c.shift()).abs()],axis=1).max(axis=1); atr=tr.rolling(14).mean()
F=pd.DataFrame(index=d1.index)
for n in (5,10,20): F[f"ER{n}"]=(c-c.shift(n)).abs()/c.diff().abs().rolling(n).sum()
F["box20/ATR"]=(H.rolling(20).max()-L.rolling(20).min())/atr
F["box10/ATR"]=(H.rolling(10).max()-L.rolling(10).min())/atr
F["ATR5/ATR20"]=tr.rolling(5).mean()/tr.rolling(20).mean()
hh=H.rolling(20).max(); ll=L.rolling(20).min()
F["дотики меж20 за 10дн"]=(((hh-H)<0.3*atr)|((L-ll)<0.3*atr)).rolling(10).sum()
F["позиція в коробці"]=((c-ll)/(hh-ll)-0.5).abs()
# H1-based mean reversion measures over last k days
hc=h1.close; r1=np.log(hc).diff()
day=hc.index.normalize()
def daily_roll(f,k):
    vals={}
    ds=d1.index
    for i,d in enumerate(ds):
        if i<k: continue
        m=(day>=ds[i-k+1])&(day<=d); vals[d]=f(m)
    return pd.Series(vals)
r4=np.log(hc).diff(4)
F["VR4 10дн"]=daily_roll(lambda m: r4[m].var()/(4*r1[m].var()),10)
F["VR4 5дн"]=daily_roll(lambda m: r4[m].var()/(4*r1[m].var()),5)
F["AC1 H1 10дн"]=daily_roll(lambda m: r1[m].autocorr(1),10)
m15c=np.log(m15.close).diff(); m15d=m15.index.normalize()
F["AC1 M15 5дн"]=pd.Series({d:m15c[(m15d<=d)&(m15d>d-pd.Timedelta(days=7))].autocorr(1) for d in d1.index[10:]})
F=F.shift(1)   # тільки відоме до дня
F.to_pickle("cleanF.pkl")
