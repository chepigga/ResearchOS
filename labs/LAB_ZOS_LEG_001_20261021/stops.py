import pandas as pd,numpy as np
exec(open("octs.py").read().split("exits=")[0])
d=d1.close; er=((d-d.shift(20)).abs()/d.diff().abs().rolling(20).sum()).shift(1)
S={(tf,nm):sig for tf,nm,sig in strats}
b=B["M15"]
def run2(b,sig,s_atr,tgt,hold):
    o,h,l,c,a,cost,ma=[b[x].values for x in ("open","high","low","close","atr","cost","ma20")]
    idx=b.index; res=[]; i=0; n=len(b)
    while i<n-1:
        s=sig[i]
        if s==0 or np.isnan(a[i]): i+=1; continue
        e=o[i+1]; R=s_atr*a[i]; st=e-s*R; tp=(ma[i] if tgt=="ma" else e+s*tgt*R)
        if tgt=="ma" and s*(tp-e)<=0.2*R: i+=1; continue
        j=i+1; out=None; typ="час"
        while j<n and j<=i+hold:
            if (s>0 and l[j]<=st) or (s<0 and h[j]>=st): out=-R; typ="стоп"; break
            if (s>0 and h[j]>=tp) or (s<0 and l[j]<=tp): out=s*(tp-e); typ="ціль"; break
            j+=1
        if out is None: j=min(j,n-1); out=s*(c[j]-e)
        res.append((idx[i+1],(out-cost[i])/R,typ,R)); i=j+1
    return res
rows=[]
for nm,tgt,hold in (("PDH/PDL фейд",2.0,8),("RSI2 10/90 фейд","ma",24)):
    for sa in (1.0,2.0,3.0,4.0):
        r=pd.DataFrame(run2(b,S[("M15",nm)],sa,tgt,hold),columns=["t","R","typ","Rusd"])
        r["m"]=r.t.dt.to_period("M"); r["reg"]=er.reindex(r.t.dt.normalize()).values<0.2
        r["grp"]=np.where(r.t>="2026-10-01","жовтень",np.where(r.reg,"інші коридори","не коридор"))
        for g,x in r.groupby("grp"):
            mm=x.groupby("m").R.sum()
            rows.append((nm,sa,g,len(x),(x.typ=="стоп").mean(),(x.typ=="ціль").mean(),(x.typ=="час").mean(),x[x.typ=="час"].R.mean(),x.R.mean(),x.R.sum(),(mm>0).mean(),x.Rusd.median()))
O=pd.DataFrame(rows,columns=["стратегія","стоп ATR","група","n","стоп%","ціль%","час%","R час-виходів","R/угоду","ΣR","міс+%","стоп $ мед"])
pd.set_option("display.width",250); print(O.round(3).to_string(index=False))
