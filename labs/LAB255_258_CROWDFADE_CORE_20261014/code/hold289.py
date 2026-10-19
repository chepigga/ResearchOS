"""LAB289: holding time for colour+H4 arrows. Fixed hold 2/6/12/24/48/72h, two exit sets:
 TIME   = SL 3 ATR_H1 + time exit only;  TRAIL = SL 3 ATR_H1, trail peak-3R after +2R, time exit. 7.5 bps. Also D2 signals for comparison."""
import numpy as np,pandas as pd
exec(open("color287.py").read().split("def ev(")[0])
def run(S,H,trail):
    out=[]
    for i,sd in S:
        ei=i+1; e=BO[ei]; a=BA[i]; R=3*a; stp=e-sd*R; pk=0; x=None; end=ei+H*12
        if end>=N: continue
        for k in range(ei,end):
            if (BL[k]<=stp) if sd>0 else (BH[k]>=stp): pnl=sd*(stp-e); x=k; break
            if trail:
                pk=max(pk,sd*((BH[k] if sd>0 else BL[k])-e)/R)
                if pk>=2: ns=e+sd*(pk-3)*R; stp=max(stp,ns) if sd>0 else min(stp,ns)
        if x is None: pnl=sd*(BC[end-1]-e)
        out.append((BT[i]<TE,(pnl-7.5e-4*e)/R))
    return out
rows=[]
for nm,S in (("колір+H4",color_sig(True)),("D2",d2())):
    for trail in (False,True):
        for H in (2,6,12,24,48,72):
            x=pd.DataFrame(run(S,H,trail),columns=["tr","R"])
            r={"сигнали":nm,"вихід":"трейл" if trail else "лише час","год":H}
            for sg,m,mo in (("21-24",x.tr,48),("25-26",~x.tr,19.3)):
                y=x.R[m]; cum=y.cumsum(); dd=(cum.cummax()-cum).max()
                r[f"EV {sg}"]=y.mean(); r[f"R/міс {sg}"]=y.sum()/mo; r[f"R/DD {sg}"]=y.sum()/dd if dd>0 else np.nan
            rows.append(r)
pd.set_option("display.width",250); print(pd.DataFrame(rows).round(3).to_string(index=False))
