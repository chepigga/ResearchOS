import io,contextlib,pickle,numpy as np,pandas as pd
src=open("trendalt.py").read(); src=src[:src.index("df=pd.DataFrame({\"c\":BC")]
g={}
with contextlib.redirect_stdout(io.StringIO()): exec(compile(src,"ta","exec"),g)
L,BT,TE,TLD,RAW,simD,E,al=[g[k] for k in "L BT TE TLD RAW simD E al".split()]
IDX={t:i for i,t in enumerate(BT)}
tD,eD=simD(E.SIG); DB=al(eD)*0.10
C=pickle.load(open("a_oi_cands.pkl","rb"))
B3=RAW[RAW.source=="B3_HIGH"][["source","entry_time","entry_i","side","atr","pri"]]
rows=[]
for k,c in C.items():
    c=c[c.entry_time.isin(IDX.keys())].copy(); c["entry_i"]=c.entry_time.map(IDX); c["source"]="A"; c["pri"]=0
    raw=pd.concat([c[["source","entry_time","entry_i","side","atr","pri"]],B3]).sort_values(["entry_i","pri"]).reset_index(drop=True)
    t,e,_,_=L.replay(7.5,{},TLD,raw=raw)
    AB=al(pd.Series(e.equity_r.to_numpy(),index=pd.DatetimeIndex(e.time)))*0.25; P=AB+DB
    r=dict(v=k)
    for seg,m,mo in [("21-24",BT<TE,48),("25-26",BT>=TE,19.3)]:
        ta=t[(t.source=="A")&((t.entry_time<TE)==(seg=="21-24"))]
        x=P[m]; x=x-x.iloc[0]; dd=float((x.cummax()-x).max())
        r.update({f"A/міс {seg}":len(ta)/mo,f"A EV {seg}":ta.net_r.mean(),f"A R/міс {seg}":ta.net_r.sum()/mo,f"порт %/міс {seg}":x.iloc[-1]/mo,f"порт DD {seg}":dd,f"порт R/DD {seg}":x.iloc[-1]/dd})
    rows.append(r)
R=pd.DataFrame(rows).set_index("v"); k=7/R[["порт DD 21-24","порт DD 25-26"]].max(axis=1)
R["$ 21-24"]=R["порт %/міс 21-24"]*k*1000; R["$ 25-26"]=R["порт %/міс 25-26"]*k*1000
pd.set_option("display.width",300); print(R.round(2).T.to_string())
