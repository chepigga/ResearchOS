import io,contextlib,itertools,numpy as np,pandas as pd
src=open("trendalt.py").read(); src=src[:src.index("df=pd.DataFrame({\"c\":BC")]
g={}
with contextlib.redirect_stdout(io.StringIO()): exec(compile(src,"ta","exec"),g)
BT,BO,BC,BA,N,TE,AB,al,simD=[g[k] for k in "BT BO BC BA N TE AB al simD".split()]
z6,z24=g["z6"],g["z24"]; TR4=g["E"].TR4
C24=np.r_[np.full(288,np.nan),BC[:-288]]
def cands(x):
    """all crossings |z6|>=x with episode start index; one per episode handled later"""
    out=[]; armed=True; ep=None
    for i in range(300,N-1000):
        v=z6[i]
        if not np.isfinite(v): continue
        if abs(v)<1: armed=True; ep=None; continue
        if ep is None or np.sign(v)!=np.sign(z6[ep]): ep=i
        if armed and abs(v)>=x and abs(z6[i-1])<x:
            out.append((i,-int(np.sign(v)),ep)); 
    return out
CAND={x:cands(x) for x in (1.5,2.0,2.5)}
def build(x,zmin,trend,lep,l24):
    SIG=[]; used=set()
    for i,sd,ep in CAND[x]:
        if ep in used: continue
        if not(np.isfinite(z24[i]) and -np.sign(z24[i])==sd and abs(z24[i])>=zmin): continue
        if trend and TR4[i]!=sd: continue
        a=BA[i+1]
        if lep is not None and sd*(BO[i+1]-BC[ep])/a>lep: used.add(ep); continue
        if l24 is not None and np.isfinite(C24[i]) and sd*(BO[i+1]-C24[i])/a>l24: used.add(ep); continue
        SIG.append((i,sd)); used.add(ep)
    return SIG
rows=[]
grid=list(itertools.product([1.5,2.0,2.5],[0.5,1.0,1.5],[True,False],[None,1,2,3,4],[None]))+\
     list(itertools.product([2.0],[1.0],[True,False],[None],[2,3,4,6]))
for x,zmin,trend,lep,l24 in grid:
    SIG=build(x,zmin,trend,lep,l24); t,e=simD(SIG); D=al(e)*0.10; tot=AB+D
    r=dict(x=x,zmin=zmin,trend="H4" if trend else "-",lep=lep if lep else "-",l24=l24 if l24 else "-")
    for seg,mask,mo in [("TR",BT<TE,48),("OOS",BT>=TE,19.3)]:
        P=tot[mask]; P=P-P.iloc[0]; dd=float((P.cummax()-P).max())
        tt=t[(BT[t.entry_i.to_numpy(int)]<TE)==(seg=="TR")]
        r.update({f"n_{seg}":len(tt)/mo,f"ev_{seg}":tt.net_r.mean(),f"Rmo_{seg}":tt.net_r.sum()/mo,f"pct_{seg}":P.iloc[-1]/mo,f"dd_{seg}":dd,f"rdd_{seg}":P.iloc[-1]/dd})
    rows.append(r)
R=pd.DataFrame(rows); R["usd_TR"]=R.pct_TR*7/R[["dd_TR","dd_OOS"]].max(axis=1)*1000; R["usd_OOS"]=R.pct_OOS*7/R[["dd_TR","dd_OOS"]].max(axis=1)*1000
R.to_csv("out_oos/D_TUNE.csv",index=False)
pd.set_option("display.width",300)
c=["x","zmin","trend","lep","l24","n_TR","ev_TR","Rmo_TR","rdd_TR","n_OOS","ev_OOS","Rmo_OOS","rdd_OOS","usd_TR","usd_OOS"]
print(R.sort_values("rdd_TR",ascending=False)[c].round(2).head(25).to_string(index=False))
print("\nbase:");print(R[(R.x==2.0)&(R.zmin==1.0)&(R.lep=="-")&(R.l24=="-")][c].round(2).to_string(index=False))
