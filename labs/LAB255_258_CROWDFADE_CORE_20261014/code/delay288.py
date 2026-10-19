"""LAB288: colour+H4 arrows entered 0/1/2/4h LATER (causal). Variant DLY1-CONF: enter after 1h only if the first hour went in trade direction."""
import numpy as np,pandas as pd
exec(open("color287.py").read().split("A=pd.read_pickle")[0])
S=color_sig(True)
rows=[]
for d in (0,12,24,48):
    rows+=ev(f"через {d//12} год",[(i+d,sd) for i,sd in S if i+d<N-700])
conf=[(i+12,sd) for i,sd in S if i+12<N-700 and sd*(BC[i+12]-BO[i+1])>0]
anti=[(i+12,sd) for i,sd in S if i+12<N-700 and sd*(BC[i+12]-BO[i+1])<=0]
rows+=ev("через 1 год, лише якщо 1-а година в наш бік",conf)+ev("через 1 год, лише якщо 1-а година проти",anti)
R=pd.DataFrame(rows); R["seg"]=np.where(R.tr,"2021-24","2025-26")
O=R.groupby(["v","seg"],sort=False).agg(n=("f1","size"),**{f"рух {H}г":(f"f{H}","mean") for H in (1,4,24,48)},виграшних=("win","mean"),EV_R=("R","mean")).reset_index()
O["на_міс"]=O.n/np.where(O.seg=="2021-24",48,19.3)
pd.set_option("display.width",250); print(O.drop(columns="n").round(3).to_string(index=False))
