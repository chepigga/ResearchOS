import pandas as pd,numpy as np
exec(open("algo2.py").read())
d1=pd.read_pickle("d1.pkl"); c=d1.close
e20=c.ewm(span=20,adjust=False).mean(); e50=c.ewm(span=50,adjust=False).mean(); e200=c.ewm(span=200,adjust=False).mean()
F=pd.DataFrame({"b50":c<e50,"sl50":e50<e50.shift(5),"x2050":e20<e50,"b200":c<e200,"m60":c<c.shift(60),"a50":c>e50}).shift(1).fillna(False)
b=build(1.5)
day=b.index.normalize()
Fb=F.reindex(day).fillna(False).astype(bool).values
cols=list(F.columns); fi=lambda k:Fb[:,cols.index(k)]
conds={"S1 нижче EMA50":fi("b50"),
       "S2 + нахил EMA50 вниз":fi("b50")&fi("sl50"),
       "S3 + EMA20<EMA50":fi("b50")&fi("sl50")&fi("x2050"),
       "S4 + нижче EMA200":fi("b50")&fi("sl50")&fi("x2050")&fi("b200"),
       "S5 S3 + імпульс 60д вниз":fi("b50")&fi("sl50")&fi("x2050")&fi("m60")}
res={}
raw=b.sig.values.copy()
for nm,cnd in conds.items():
    for ex,tps in (("1R/2R/3R",(1,2,3)),("повністю 1R",(1,1,1)),("повністю 1.5R",(1.5,1.5,1.5))):
        bb=b.copy(); bb["sig"]=np.where((raw<0)&cnd,-1,0)
        T=simulate(bb,tps=tps); res[(nm,ex)]=T
pd.to_pickle(res,"shorts.pkl")
