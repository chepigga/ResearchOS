import pandas as pd,numpy as np
src=open("/home/claude/bk/lrep.py").read().split("raw=b.sig.values")[0]
exec(src)
raw=b.sig.values
h4["e20"]=h4.close.ewm(span=20,adjust=False).mean(); ce=pd.Series(np.sign(h4.close-h4.e20).values,index=h4.index+pd.Timedelta(hours=4)).reindex(t,method="ffill").values
base_l=(raw>0)&(cc>ee50); base_s=(raw<0)&(cc<ee50)&(ee50<ee50p)&(ee20<ee50)&(cc<ee200)
V={"L без H4":(base_l,base_s),"L H4 структура":(base_l&(s4!=-1),base_s&(s4!=1)),"L H4 EMA20":(base_l&(ce>0),base_s&(ce<0)),"L лише лонги H4 EMA20":(base_l&(ce>0),np.zeros_like(base_s))}
out={}
for k,(l,s) in V.items():
    bl=b.copy(); bl["sig"]=np.where(l,1,0); TL=simulate(bl,tps=(1,2,3))
    bs=b.copy(); bs["sig"]=np.where(s,-1,0); TS=simulate(bs,tps=(1,1,1)) if s.any() else TL.iloc[0:0]
    out[k]=pd.concat([TL,TS])
pd.to_pickle(out,"/home/claude/bk/lvar.pkl")
