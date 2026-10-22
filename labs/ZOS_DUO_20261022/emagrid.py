import pandas as pd,numpy as np
src=open("/home/claude/bk/lrep.py").read().split("raw=b.sig.values")[0]
exec(src)
raw=b.sig.values
m1=None
base_l=(raw>0)&(cc>ee50); base_s=(raw<0)&(cc<ee50)&(ee50<ee50p)&(ee20<ee50)&(cc<ee200)
agg={"open":"first","high":"max","low":"min","close":"last"}
h1b=pd.read_pickle("/home/claude/bk/h1.pkl"); m15b=pd.read_pickle("/home/claude/bk/m15.pkl")
TF={"H1":(h1b,1),"H2":(m15b.resample("2h").agg(agg).dropna(),2),"H4":(h4,4)}
out={}
for tf,(bb,hrs) in TF.items():
    for n in (10,20,30,50,100):
        e=bb.close.ewm(span=n,adjust=False).mean()
        side=pd.Series(np.sign(bb.close-e).values,index=bb.index+pd.Timedelta(hours=hrs)).reindex(t,method="ffill").values
        l=base_l&(side>0); s=base_s&(side<0)
        bl=b.copy(); bl["sig"]=np.where(l,1,0); TL=simulate(bl,tps=(1,2,3))
        bs=b.copy(); bs["sig"]=np.where(s,-1,0); TS=simulate(bs,tps=(1,1,1))
        out[(tf,n)]=pd.concat([TL,TS])
pd.to_pickle(out,"/home/claude/bk/emagrid.pkl")
