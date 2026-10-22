import pandas as pd,numpy as np
exec(open("twoside.py").read().split("conds=")[0])
F2=pd.DataFrame({"a50":c>e50,"su50":e50>e50.shift(5),"x":e20>e50,"a200":c>e200}).shift(1).fillna(False)
G=F2.reindex(day).fillna(False).astype(bool).values
Lsimple=G[:,0]; Lfull=G.all(axis=1)
Sfull=fi("b50")&fi("sl50")&fi("x2050")&fi("b200")
raw=b.sig.values.copy(); out={}
for nm,lc,sc,ltp,stp in [("лонг EMA50 (як раніше)",Lsimple,None,(1,2,3),None),
                          ("лонг повний тренд D1",Lfull,None,(1,2,3),None),
                          ("шорт повний тренд D1, вихід 1R",None,Sfull,None,(1,1,1))]:
    bb=b.copy(); bb["sig"]=np.where((raw>0)&lc,1,0) if lc is not None else np.where((raw<0)&sc,-1,0)
    out[nm]=simulate(bb,tps=ltp or stp)
pd.to_pickle(out,"twoside.pkl")
