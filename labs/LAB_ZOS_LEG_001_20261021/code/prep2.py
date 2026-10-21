import pandas as pd
m=pd.read_pickle("m1.pkl"); m=m[m.index<"2026-09-01"]
n=pd.read_csv("in/oct.csv",sep="\t"); n.columns=[c.strip("<>").lower() for c in n.columns]
n["t"]=pd.to_datetime(n.date+" "+n.time,format="%Y.%m.%d %H:%M:%S"); n=n.set_index("t")[["open","high","low","close","spread"]]
m=pd.concat([m[["open","high","low","close","spread"]],n]); m.to_pickle("m1b.pkl")
agg={"open":"first","high":"max","low":"min","close":"last","spread":"mean"}
for tf,nm in (("5min","m5"),("15min","m15"),("1h","h1"),("1D","d1")):
    b=m.resample(tf).agg(agg).dropna(); b.to_pickle(nm+".pkl"); print(nm,len(b),b.index[-1])
