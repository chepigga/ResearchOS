import os
os.environ["LAB_CACHE"]="/home/claude/lab251/cache_full.pkl"
import numpy as np, pandas as pd, statsmodels.api as sm
import lab251 as L
BT,BC,BA,N=L.BT,L.BC,L.BA,L.N; BZ=np.asarray(L.C["BZ"],float)
c=pd.Series(BC); a=pd.Series(BA); z=pd.Series(BZ)
TE=pd.Timestamp("2025-01-01",tz="UTC")
D=pd.DataFrame(dict(
  fut24=(c.shift(-288)-c)/a, fut6=(c.shift(-72)-c)/a,
  past1=(c-c.shift(12))/a, past6=(c-c.shift(72))/a, past24=(c-c.shift(288))/a,
  z=z, dz1=z-z.shift(12), dz6=z-z.shift(72),
  ema=(c-c.ewm(span=20*12,adjust=False).mean())/a))   # EMA20 H1 on M5 = span 240 bars
D["seg"]=np.where(BT<TE,"2021-24","2025-26")
D=D.iloc[300:-300:12].dropna()   # hourly samples
def ols(y,X,d):
    m=sm.OLS(d[y],sm.add_constant(d[X])).fit(cov_type="HAC",cov_kwds={"maxlags":24})
    return pd.DataFrame({"coef":m.params,"t":m.tvalues}).drop("const").round(3), round(m.rsquared*100,3)
for seg,d in D.groupby("seg"):
    print("=====",seg,"n",len(d))
    for X in (["past6","past24"],["z"],["past6","past24","ema","z","dz1","dz6"]):
        t,r2=ols("fut24",X,d); print("fut24 ~",X,"R2%",r2); print(t.T.to_string())
# lead-lag: which reacts faster to a price move? corr of past1 shock with later z / ema changes
print("\nreaction speed: corr( price move over hour t , change in indicator over next k hours )")
x=D  # hourly
for name,ser in [("z",z),("EMA-dist",(c-c.ewm(span=240,adjust=False).mean())/a)]:
    out=[]
    for k in [0,1,2,3,6,12]:
        ch=(ser.shift(-12*k)-ser.shift(12)).iloc[300:-300:12]   # from t-1h to t+k
        p=((c-c.shift(12))/a).iloc[300:-300:12]
        m=ch.notna()&p.notna(); out.append(round(np.corrcoef(p[m],ch[m])[0,1],3))
    print(name,out)
# extreme vs trajectory: fresh crossing events vs level, fade fut24
fresh=(np.abs(BZ)>=1)&(np.abs(np.r_[0,BZ[:-1]])<1)
lvl=(np.abs(BZ)>=1)
side=-np.sign(BZ); f24=((c.shift(-288)-c)/a).to_numpy(); seg=np.where(BT<TE,"2021-24","2025-26")
dz6=(z-z.shift(72)).to_numpy()
rows=[]
for nm,msk in [("|z|>=1 будь-коли",lvl),("свіжий перетин |z|=1",fresh),
               ("|z|>=1 і |z| росте за 6г",lvl&(np.sign(BZ)*dz6>0.5)),("|z|>=1 і |z| падає за 6г",lvl&(np.sign(BZ)*dz6<-0.5)),
               ("|z|>=2",np.abs(BZ)>=2)]:
    for s in ["2021-24","2025-26"]:
        m=msk&(seg==s)&np.isfinite(f24); v=(side*f24)[m][::6]
        rows.append(dict(what=nm,seg=s,n=len(v),fade_fut24=v.mean(),t=v.mean()/v.std()*np.sqrt(len(v)/24)))
print(pd.DataFrame(rows).pivot(index="what",columns="seg",values=["fade_fut24","n"]).round(3))
