import pandas as pd,numpy as np,sys
sys.path.insert(0,"/home/claude/zr"); import z102
m15=pd.read_pickle("/home/claude/bk/m15.pkl"); z102.m15=m15
h1=pd.read_pickle("/home/claude/bk/h1.pkl"); h4=pd.read_pickle("/home/claude/bk/h4.pkl"); d1=pd.read_pickle("/home/claude/bk/d1.pkl")
ev,piv=z102.run()
Z=pd.DataFrame([x for x in ev if x[1]=="ENTRY"],columns=["sig","ev","d","e","risk","atr","R","ord","wt","lvl","xj"])
Z["t"]=Z.sig+pd.Timedelta(minutes=15); Z["xt"]=m15.index[Z.xj.clip(upper=len(m15)-1)]
def side(b,n,hrs,t):
    e=b.close.ewm(span=n,adjust=False).mean(); s=pd.Series(np.sign(b.close-e).values,index=b.index+pd.Timedelta(hours=hrs)); return s.reindex(t,method="ffill").values
Z["H1e30"]=side(h1,30,1,Z.t)*Z.d; Z["H4e20"]=side(h4,20,4,Z.t)*Z.d
c=d1.close; e50=c.ewm(span=50,adjust=False).mean(); e200=c.ewm(span=200,adjust=False).mean()
DD=pd.DataFrame({"D1e50":np.sign(c-e50),"D1e200":np.sign(c-e200),"mom20":np.sign(c-c.shift(20)),
                 "ER20":(c-c.shift(20)).abs()/c.diff().abs().rolling(20).sum(),
                 "atrD%":(pd.concat([d1.high-d1.low,(d1.high-c.shift()).abs(),(d1.low-c.shift()).abs()],axis=1).max(axis=1).rolling(14).mean()/c*100)}).shift(1)
X=DD.reindex(Z.t.dt.normalize(),method="ffill").reset_index(drop=True)
for k in ("D1e50","D1e200","mom20"): Z[k]=X[k].values*Z.d
Z["ER20"]=X.ER20.values; Z["atrD%"]=X["atrD%"].values
Z["risk/atr"]=Z.risk/Z.atr; Z["hour"]=Z.t.dt.hour; Z["dow"]=Z.t.dt.dayofweek
Z["m"]=Z.t.dt.to_period("M"); Z.to_pickle("/home/claude/bk/zfeat.pkl")
print(len(Z),"R/уг",round(Z.R.mean(),3))
