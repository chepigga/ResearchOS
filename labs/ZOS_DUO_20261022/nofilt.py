import pandas as pd,numpy as np,sys
sys.path.insert(0,"/home/claude/zr"); from z102 import *
V={"оригінал":{},
 "без макс. ризику":dict(maxr=1e9),
 "без мін. ризику":dict(minr=0.0),
 "без структури":dict(struct=False),
 "без тіла пробою":dict(body=0.0),
 "без ліміту ordinal":dict(maxord=99),
 "без 1 позиції":dict(onepos=False),
 "без усіх фільтрів":dict(maxr=1e9,minr=0.0,struct=False,body=0.0,maxord=99,onepos=False,spr_atr=9e9),
}
out={}
for k,p in V.items():
    ev,piv=run(**p); out[k]=pd.DataFrame([(x[0],x[6],x[2]) for x in ev if x[1]=="ENTRY"],columns=["t","R","d"])
pd.to_pickle(out,"/home/claude/zr/nofilt.pkl")
