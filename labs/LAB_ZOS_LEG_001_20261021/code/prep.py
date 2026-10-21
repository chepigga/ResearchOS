import pandas as pd,numpy as np
m=pd.read_csv("M1_native.csv",sep=";",usecols=["time","open","high","low","close","ask_close","spread"])
m["t"]=pd.to_datetime(m.time,format="%Y.%m.%d %H:%M"); m=m.set_index("t").drop(columns="time")
a=pd.read_csv("XAUUSD_M1_2026.csv",sep=";"); a["t"]=pd.to_datetime(a.time,format="%Y.%m.%d %H:%M"); a=a.set_index("t")
a=a[a.index>m.index[-1]][["open","high","low","close","spread"]]; a["ask_close"]=a.close+a.spread*0.01
m=pd.concat([m,a]); m.to_pickle("m1.pkl")
agg={"open":"first","high":"max","low":"min","close":"last"}
for tf,nm in (("5min","m5"),("15min","m15"),("1h","h1"),("1D","d1")):
    b=m.resample(tf).agg({**agg,"spread":"mean"}).dropna(); b.to_pickle(nm+".pkl"); print(nm,len(b),b.index[0],b.index[-1])
