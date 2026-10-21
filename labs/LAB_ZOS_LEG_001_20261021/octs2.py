import pandas as pd,numpy as np
exec(open("octs.py").read().split("exits=")[0])
c=d1.close; er=((c-c.shift(20)).abs()/c.diff().abs().rolling(20).sum()).shift(1)
S={(tf,nm):sig for tf,nm,sig in strats}
top=[("M15","PDH/PDL фейд",1.0,2.0,8),("M15","RSI2 10/90 фейд",2.0,"ma",24),("M15","PDH/PDL фейд",1.0,"ma",24),
     ("M15","BB20,1.5 фейд",1.0,"ma",24),("M15","Donchian20 фейд",2.0,2.0,24),("M15","PDH/PDL фейд",2.0,1.0,24),
     ("H1","RSI2 20/80 фейд",1.0,2.0,8),("H1","Donchian50 фейд",1.0,2.0,8)]
out=[];mon={}
for tf,nm,s,t,hd in top:
    b=B[tf]; sg=S[(tf,nm)].copy(); sg[:60]=0
    r=pd.DataFrame(run(b,sg,s,t,hd,0),columns=["t","R"]); r["reg"]=(er.reindex(r.t.dt.normalize()).values<0.2)
    r["h"]=np.where(r.t<"2024-07-01","H1","H2"); r["m"]=r.t.dt.to_period("M")
    k=f"{tf} {nm} st{s} tp{t} h{hd}"
    rg=r[r.reg]; tr=r[~r.reg]; oc=r[r.t>="2026-10-01"]
    mm=rg.groupby("m").R.sum(); mon[k]=mm
    out.append((k,len(oc),oc.R.sum(),len(rg),rg.R.mean(),rg[rg.h=="H1"].R.sum(),rg[rg.h=="H2"].R.sum(),(mm>0).mean(),len(tr),tr.R.mean()))
O=pd.DataFrame(out,columns=["стратегія","жовт n","жовт R","коридор n","коридор R/угоду","кор 22-24 ΣR","кор 24-26 ΣR","кор міс+ %","тренд n","тренд R/угоду"])
pd.set_option("display.width",250); print(O.round(3).to_string(index=False))
pd.to_pickle(mon,"oct_mon.pkl")
