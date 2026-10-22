import pandas as pd,numpy as np,sys
f="r.xlsx"; x=pd.read_excel(f,header=None)
i=x.index[x[0].astype(str).str.strip()=="Deals"][0]
d=x.iloc[i+1:].copy(); d.columns=[str(c) for c in d.iloc[0]]; d=d.iloc[1:]; d=d[d.Direction.isin(["in","out"])].copy()
d["t"]=pd.to_datetime(d.Time,format="%Y.%m.%d %H:%M:%S")
for c in ("Volume","Price","Profit","Commission","Swap","Balance"): d[c]=pd.to_numeric(d[c],errors="coerce").fillna(0)
o=x.index[x[0].astype(str).str.strip()=="Orders"][0]
od=x.iloc[o+1:i].copy(); od.columns=[str(c) for c in od.iloc[0]]; od=od.iloc[1:]
od=od[od["State"].astype(str).str.contains("filled",case=False,na=False)]
slc=[c for c in od.columns if c.strip() in ("S / L","S/L","SL")][0]
od["sl"]=pd.to_numeric(od[slc],errors="coerce"); od["Order"]=pd.to_numeric(od["Order"],errors="coerce")
slmap=od.set_index("Order").sl.to_dict()
def leg(c):
    c=str(c)
    if c.startswith("ZOS-Z"): return "Z"
    if c.startswith("ZOS-L"): return "L"
    if c.startswith("ZOSM"): return c.split()[1]
    return "?"
opn=[]; rows=[]
for r in d.itertuples():
    if r.Direction=="in":
        sl=slmap.get(pd.to_numeric(r.Order,errors="coerce"),np.nan)
        opn.append(dict(leg=leg(r.Comment),side=r.Type,vol=r.Volume,v0=r.Volume,p=r.Price,t=r.t,bal=r.Balance,sl=sl,id=len(opn)+len(rows))); continue
    side="buy" if r.Type=="sell" else "sell"; sg=1 if side=="buy" else -1
    implied=r.Price-r.Profit/(r.Volume*100*sg) if r.Volume>0 else r.Price
    cand=[q for q in opn if q["side"]==side and q["vol"]>=r.Volume-1e-9] or [q for q in opn if q["side"]==side]
    if not cand: continue
    q=min(cand,key=lambda q:abs(q["p"]-implied)); q["vol"]-=r.Volume
    rows.append(dict(id=q["id"],leg=q["leg"],et=q["t"],xt=r.t,side=side,ep=q["p"],sl=q["sl"],v0=q["v0"],vol=r.Volume,xp=r.Price,profit=r.Profit,swap=r.Swap,bal=q["bal"],xc=str(r.Comment)))
    opn=[q for q in opn if q["vol"]>1e-9]
D=pd.DataFrame(rows)
T=D.groupby("id").agg(leg=("leg","first"),et=("et","first"),xt=("xt","max"),side=("side","first"),ep=("ep","first"),sl=("sl","first"),v0=("v0","first"),bal=("bal","first"),profit=("profit","sum"),swap=("swap","sum"),nparts=("xt","size"),lastc=("xc","last")).reset_index()
T["net"]=T.profit+T.swap
T["riskusd"]=(T.ep-T.sl).abs()*T.v0*100
T["R"]=T.net/T.riskusd; T["Rgross"]=T.profit/T.riskusd
T["hold_h"]=(T.xt-T.et).dt.total_seconds()/3600
T.to_pickle("trades.pkl"); print(T.groupby("leg").agg(n=("R","size"),R=("R","mean"),net=("net","sum"),swap=("swap","sum")).round(2))
