import runpy, io, contextlib, numpy as np, pandas as pd
buf=io.StringIO()
with contextlib.redirect_stdout(buf): g=runpy.run_path("months.py")
M=g["M"]; td=g["td"]; tv=g["tv"]
for sg,x in M.groupby("seg"):
    for c in ["v157","D","разом"]:
        s=x[c]; print(sg,c,"mean %/mo",round(s.mean(),2),"std",round(s.std(),2),"Sharpe(річний)",round(s.mean()/s.std()*np.sqrt(12),2))
    print(sg,"кореляція v157 vs D помісячно:",round(x["v157"].corr(x["D"]),2))
# concentration: share of profit from top 10% trades
for nm,t in [("v157",tv),("D",td)]:
    t=t.copy(); t["seg"]=np.where(pd.to_datetime(t.entry_time,utc=True)<pd.Timestamp("2025-01-01",tz="UTC"),"2021-24","2025-26")
    for sg,x in t.groupby("seg"):
        r=x.net_r.sort_values(ascending=False); k=max(1,int(len(r)*0.1))
        print(nm,sg,"угод",len(r),"WR",round((r>0).mean(),2),"частка прибутку від топ-10% угод",round(r.iloc[:k].sum()/r.sum(),2),"медіана R",round(r.median(),2))
