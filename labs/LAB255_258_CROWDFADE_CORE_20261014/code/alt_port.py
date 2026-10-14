import io,contextlib,pickle,numpy as np,pandas as pd
src=open("trendalt.py").read(); src=src[:src.index("df=pd.DataFrame({\"c\":BC")]
g={}
with contextlib.redirect_stdout(io.StringIO()): exec(compile(src,"ta","exec"),g)
BT,AB,al,simD,E=[g[k] for k in "BT AB al simD E".split()]
tD,eD=simD(E.SIG); DB=al(eD)*0.10
O=pickle.load(open("alt_out.pkl","rb"))
def eqs(a,v,f="close"): return al(O[(a,v,f)][1])*0.10
T0=pd.Timestamp("2022-01-01",tz="UTC"); TE=pd.Timestamp("2025-01-01",tz="UTC"); TEND=pd.Timestamp("2026-07-31",tz="UTC")
P={"BTC ядро (A+B3+D)":AB+DB,
   "+ ETH D + SOL D":AB+DB+eqs("ETH","D")+eqs("SOL","D"),
   "+ ETH D' + SOL D'":AB+DB+eqs("ETH","D'")+eqs("SOL","D'"),
   "+ ETH D + SOL D' ":AB+DB+eqs("ETH","D")+eqs("SOL","D'"),
   "+ ETH D + SOL D (stop-fill, оптимістично)":AB+DB+eqs("ETH","D","stop")+eqs("SOL","D","stop")}
rows=[]
for nm,s in P.items():
    s=s[(s.index>=T0)&(s.index<=TEND)]
    r=dict(v=nm)
    for seg,m in [("2022-24",s.index<TE),("2025-26",s.index>=TE)]:
        x=s[m]; x=x-x.iloc[0]; mo=(x.index[-1]-x.index[0]).days/30.44; dd=float((x.cummax()-x).max())
        mm=x.groupby(x.index.strftime("%Y-%m")).last().diff().dropna()
        r.update({f"pct_{seg}":x.iloc[-1]/mo,f"dd_{seg}":dd,f"rdd_{seg}":x.iloc[-1]/dd,f"sh_{seg}":mm.mean()/mm.std()*np.sqrt(12),f"neg_{seg}":(mm<0).mean()})
    rows.append(r)
R=pd.DataFrame(rows).set_index("v"); k=7/R[["dd_2022-24","dd_2025-26"]].max(axis=1)
R["$міс 2022-24"]=R["pct_2022-24"]*k*1000; R["$міс 2025-26"]=R["pct_2025-26"]*k*1000; R["ризик ×"]=k
pd.set_option("display.width",250); print(R.round(2).to_string())
# monthly correlations of streams
st={"BTC A+B3":AB,"BTC D":DB,"ETH D":eqs("ETH","D"),"SOL D":eqs("SOL","D"),"ETH D'":eqs("ETH","D'"),"SOL D'":eqs("SOL","D'")}
M=pd.DataFrame({k:v[(v.index>=T0)&(v.index<=TEND)].groupby(v[(v.index>=T0)&(v.index<=TEND)].index.strftime("%Y-%m")).last().diff() for k,v in st.items()}).dropna()
print("\nкореляція помісячно (2022-07.2026):"); print(M.corr().round(2).to_string())
print("\n== вага альтів (ризик на угоду ETH/SOL D, close-fill)")
for w in (0.0,0.02,0.04,0.06,0.10):
    s=AB+DB+(eqs("ETH","D")+eqs("SOL","D"))*w/0.10; s=s[(s.index>=T0)&(s.index<=TEND)]; out=[]
    for m in (s.index<TE,s.index>=TE):
        x=s[m]; x=x-x.iloc[0]; mo=(x.index[-1]-x.index[0]).days/30.44; dd=float((x.cummax()-x).max()); out+= [x.iloc[-1]/mo,dd,x.iloc[-1]/dd]
    k=7/max(out[1],out[4]); print(f"ризик альтів {w:.2f}%: 2022-24 {out[0]:.2f}%/міс DD {out[1]:.2f} R/DD {out[2]:.2f} | 2025-26 {out[3]:.2f}%/міс DD {out[4]:.2f} R/DD {out[5]:.2f} | $ {out[0]*k*1000:.0f} / {out[3]*k*1000:.0f}")
