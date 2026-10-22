import pandas as pd,numpy as np,sys
f=sys.argv[1]; x=pd.read_excel(f,header=None); i=x.index[x[0].astype(str).str.strip()=="Deals"][0]
d=x.iloc[i+1:].copy(); d.columns=[str(c) for c in d.iloc[0]]; d=d.iloc[1:]; d=d[d.Direction.isin(["in","out"])].copy()
d["t"]=pd.to_datetime(d.Time,format="%Y.%m.%d %H:%M:%S")
for c in ("Volume","Price","Profit","Commission","Swap","Balance"): d[c]=pd.to_numeric(d[c],errors="coerce").fillna(0)
d=d.sort_values(["t","Deal"]) if "Deal" in d else d.sort_values("t")
def leg(c):
    c=str(c)
    if c.startswith("ZOS-Z"): return "Z"
    if c.startswith("ZOS-L"): return "L"
    if c.startswith("ZOSM"): return c.split()[1]
    return "?"
opn=[]; rows=[]
for r in d.itertuples():
    if r.Direction=="in":
        opn.append(dict(leg=leg(r.Comment),side=r.Type,vol=r.Volume,p=r.Price,t=r.t,com=r.Commission,bal=r.Balance)); continue
    side="buy" if r.Type=="sell" else "sell"; sgn=1 if side=="buy" else -1
    implied=r.Price - r.Profit/(r.Volume*100*sgn) if r.Volume>0 else r.Price
    cand=[q for q in opn if q["side"]==side and q["vol"]>=r.Volume-1e-9]
    if not cand: cand=[q for q in opn if q["side"]==side]
    if not cand: continue
    q=min(cand,key=lambda q:abs(q["p"]-implied))
    q["vol"]-=r.Volume
    rows.append(dict(leg=q["leg"],et=q["t"],xt=r.t,side=side,net=r.Profit+r.Swap+r.Commission+q["com"]*r.Volume/max(r.Volume,1e-9)*0,bal=q["bal"],xc=str(r.Comment)))
    opn=[q for q in opn if q["vol"]>1e-9]
L=pd.DataFrame(rows); L["m"]=L.xt.dt.to_period("M"); L.to_pickle(f+".legs.pkl")
print("сума угод",round(L.net.sum()),"| по ногах:",L.groupby("leg").net.sum().round(0).to_dict(), "| входів:",d[d.Direction=="in"].Comment.map(leg).value_counts().to_dict())
