import os
os.environ["LAB_CACHE"]="/home/claude/lab251/cache_full.pkl"
import numpy as np, pandas as pd
import topD as T
BT,BO,BH,BL,BC,BA,N,COST=T.BT,T.BO,T.BH,T.BL,T.BC,T.BA,T.N,T.COST
rows=[]
for (i,sd),tk in zip(T.E.SIG,T.D["taker за 1 год (log сума)"]):
    e=i+1; e0=BO[e]; A=BA[e]; R=3*A; end=min(e+576-1,N-1)
    adv=((e0-BL[e:end+1]) if sd>0 else (BH[e:end+1]-e0))/A
    hit=np.argmax(adv>=3) if (adv>=3).any() else None
    m24=sd*(BC[min(e+287,N-1)]-e0)/A; m48=sd*(BC[end]-e0)/A
    if hit is not None: r=-1.0; how="стоп"
    else: r=m48/3; how="48 год"
    rows.append(dict(seg="2021-24" if BT[i]<T.TE else "2025-26",grp="на нашому боці" if tk>0 else "проти нас",
       m24=m24,m48=m48,how=how,R=r-COST/1e4*e0/R,stop_h=(hit/12 if hit is not None else np.nan),
       m24_stopped=m24 if hit is not None else np.nan))
D=pd.DataFrame(rows).dropna(subset=["grp"])
pd.set_option("display.width",250)
g=D.groupby(["grp","seg"])
print(pd.DataFrame({
 "рух за 24 год, середнє ATR":g.m24.mean(),"рух за 24 год, МЕДІАНА":g.m24.median(),
 "рух за 48 год, середнє":g.m48.mean(),"частка стопів":g.how.apply(lambda x:(x=="стоп").mean()),
 "R угоди, середнє":g.R.mean(),"R угоди, медіана":g.R.median(),
 "частка 5% найкращих у сумі руху24":g.m24.apply(lambda x: x[x>=x.quantile(.95)].sum()/x.sum())}).round(2).T.to_string())
# for stopped trades: what did price do at 24h anyway?
s=D[D.how=="стоп"]
print("\nугоди, закриті стопом: рух через 24 год від входу (ATR), середнє:",s.groupby(["grp","seg"]).m24_stopped.mean().round(2).to_dict())
print("скільки годин до стопу, медіана:",s.groupby(["grp","seg"]).stop_h.median().round(1).to_dict())
