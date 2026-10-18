"""Why the chart 'shows' acceleration in thin zones: profile built WITH the move vs profile built only from the PAST."""
import numpy as np,pandas as pd
exec(open("step1.py").read().split("COST=7.5")[0])
C=np.vstack([np.zeros(NB),np.cumsum(M.astype(np.float64),0)])
hc=np.searchsorted(BT.values,(hours+pd.Timedelta("1h")).values)-1
rows=[]
for h in range(400,len(hours)-400,3):
    i=hc[h]
    if i<300 or i>N-300 or BT[i].floor("1h")!=hours[h]: continue
    a=BA[i]; k=b(np.array([BC[i]]))[0]
    rng=(BH[i+1:i+49].max()-BL[i+1:i+49].min())/a
    for nm,(h0,h1) in (("лише минуле (як торгує бот)",(h-335,h+1)),("включно з наступними 4 год (як на графіку)",(h-331,h+5)),("±7 днів навколо (fixed range на графіку)",(h-167,h+169))):
        P=gaussian_filter1d(C[h1]-C[h0],1.5); rows.append(dict(v=nm,q=P[k]/P.max(),rng=rng))
R=pd.DataFrame(rows)
for nm,x in R.groupby("v",sort=False):
    x=x.copy(); x["qb"]=pd.qcut(x.q,5,labels=["LVN 0-20%","20-40","40-60","60-80","HVN 80-100%"])
    print(nm); print("   ",x.groupby("qb",observed=True).rng.median().round(2).to_dict())
