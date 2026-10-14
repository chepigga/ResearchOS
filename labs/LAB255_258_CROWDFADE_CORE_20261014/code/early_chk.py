import io,contextlib,numpy as np,pandas as pd
src=open("trendalt.py").read(); src=src[:src.index("df=pd.DataFrame({\"c\":BC")]
g={}
with contextlib.redirect_stdout(io.StringIO()): exec(compile(src,"ta","exec"),g)
L,BT,TE,TLD,RAW,simD,E,al=[g[k] for k in "L BT TE TLD RAW simD E al".split()]
tD,eD=simD(E.SIG); DB=al(eD)*0.10
r=RAW; a=r[r.source=="A"]; e=r[r.source=="EARLY_EPISODE"]
e=e.assign(yr=e.entry_time.dt.year); print("сирі сигнали EARLY по роках:",e.groupby("yr").size().to_dict())
print("сирі A по роках:",a.groupby(a.entry_time.dt.year).size().to_dict())
# overlap: EARLY within ±12h of A same side
ai=a.entry_i.to_numpy(); asd=a.side.to_numpy()
near=[bool(((np.abs(ai-x.entry_i)<=144)&(asd==x.side)).any()) for x in e.itertuples()]
e["near_A"]=near; print("EARLY в межах 12 год від A того ж боку:",round(np.mean(near),2), e.groupby("yr").near_A.mean().round(2).to_dict())
cols=["source","entry_time","entry_i","side","atr","pri"]
def run(srcs,name):
    raw=r[r.source.isin(srcs)][cols].reset_index(drop=True)
    t,eq,_,_=L.replay(7.5,{},TLD,raw=raw)
    P=al(pd.Series(eq.equity_r.to_numpy(),index=pd.DatetimeIndex(eq.time)))*0.25+DB
    out=dict(v=name)
    for seg,m,mo in [("21-24",BT<TE,48),("25-26",BT>=TE,19.3)]:
        tt=t[(t.entry_time<TE)==(seg=="21-24")]; te=tt[tt.source=="EARLY_EPISODE"]
        x=P[m]; x=x-x.iloc[0]; dd=float((x.cummax()-x).max())
        out.update({f"EARLY угод/міс {seg}":len(te)/mo,f"EARLY EV {seg}":te.net_r.mean() if len(te) else np.nan,
                    f"%/міс {seg}":x.iloc[-1]/mo,f"DD {seg}":dd,f"R/DD {seg}":x.iloc[-1]/dd})
    return out,t
rows=[]
for srcs,nm in [(["A","B3_HIGH"],"A+B3+D (ядро)"),(["A","B3_HIGH","EARLY_EPISODE"],"A+B3+EARLY+D"),(["EARLY_EPISODE","B3_HIGH"],"EARLY замість A"),(["EARLY_EPISODE"],"EARLY окремо (+D)")]:
    o,t=run(srcs,nm); rows.append(o)
    if nm=="A+B3+EARLY+D":
        te=t[t.source=="EARLY_EPISODE"]; print("EARLY у портфелі по роках (n, сума R):",te.groupby(te.entry_time.dt.year).net_r.agg(["count","sum"]).round(1).to_dict("index"))
R=pd.DataFrame(rows).set_index("v"); k=7/R[["DD 21-24","DD 25-26"]].max(axis=1)
R["$ 21-24"]=R["%/міс 21-24"]*k*1000; R["$ 25-26"]=R["%/міс 25-26"]*k*1000
pd.set_option("display.width",300); print(R.round(2).T.to_string())
