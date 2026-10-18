"""LAB276 (pre-registered): better PRICE instead of earlier TIME. After the signal, a limit order k ATR back (against the trade side)
from the would-be entry (next M5 open), valid W hours; not filled -> no trade.
D2: k 0.25/0.5/0.75/1.0 x W 2/6/12h. Stops: LEVEL = same stop price as original (3ATR from original entry -> R=(3-k)ATR),
    FILL3 = 3ATR from fill. Exits as v006 (trail peak-3R after +2R, 48h from SIGNAL, crowd exit >=+1R, max 2).
S: same k x W (W capped by next flip), stop LEVEL / FILL (2.2ATR14 from fill), exits as v006 S.
Fill bar: stop checked on the fill bar too (conservative). Risk 0.10%/R. Select on 2021-24."""
import numpy as np,pandas as pd
exec(open("ct268.py").read().split("\nrows=[]; EQ={}")[0])
EN0=entries("NOW",0,"ATR3")
def fill(ei,sd,e,k,a,W,cap):
    lim=e-sd*k*a
    for j in range(ei,min(ei+W*12,cap,N-1)):
        if (BL[j]<=lim) if sd>0 else (BH[j]>=lim):
            px=min(BO[j],lim) if sd>0 else max(BO[j],lim); return j,px
    return None,None
def runD2(lst):
    out=[]; open_=[]
    for ei,sd,e,R,end in lst:
        open_=[(x,s) for x,s in open_ if x>ei]
        if len(open_)>=2 or (len(open_)==1 and open_[0][1]!=sd): continue
        r,x=path(ei,sd,e,R,end,True,CMP,"PROFIT"); out.append(dict(i=ei,x=x,r=r-COST/1e4*e/R,tr=BT[ei]<TE,sd=sd,e=e,R=R)); open_.append((x,sd))
    return pd.DataFrame(out)
rows=[]
def rec(eng,k,W,stop,t,nsig):
    E=mtm_eq(t); o=st_(t,E)
    rows.append(dict(eng=eng,k=k,W=W,stop=stop,fill=len(t)/nsig,n21=o["n21"],ev21=o["ev21"],usd21=o["Rmo21"]*100,rdd21=o["rdd21"],
                     n25=o["n25"],ev25=o["ev25"],usd25=o["Rmo25"]*100,rdd25=o["rdd25"]))
base=[(ei,sd,e,3*a,ei+575) for ei,sd,e,d,a in EN0]
rec("D2",0,0,"-",runD2(base),len(EN0))
for k in (0.25,0.5,0.75,1.0):
    for W in (2,6,12):
        for stop in ("LEVEL","FILL3"):
            lst=[]
            for ei,sd,e,d,a in EN0:
                j,px=fill(ei,sd,e,k,a,W,N)
                if j is None: continue
                R=(3-k)*a if stop=="LEVEL" else 3*a
                lst.append((j,sd,px,R,ei+575))
            rec("D2",k,W,stop,runD2(lst),len(EN0))
    print("D2",k,flush=True)
# S
def runS2(lst):
    out=[]
    for ei,sd,e,R,nxt in lst:
        r,x=path(ei,sd,e,R,nxt,False,EMAX,"ALWAYS",flip_exit=nxt); out.append(dict(i=ei,x=x,r=r-COST/1e4*e/R,tr=BT[ei]<TE,sd=sd,e=e,R=R))
    return pd.DataFrame(out)
SS=[]
for n_,(si,ei,sd,dist) in enumerate(S2):
    nxt=S2[n_+1][1] if n_+1<len(S2) else N-1
    if HTF[si]!=sd or CMP[si]==-sd: continue
    SS.append((ei,sd,BO[ei],dist,nxt,BA[si]))
rec("S",0,0,"-",runS2([(ei,sd,e,R,nx) for ei,sd,e,R,nx,a in SS]),len(SS))
for k in (0.25,0.5,0.75,1.0):
    for W in (2,6,12):
        for stop in ("LEVEL","FILL"):
            lst=[]
            for ei,sd,e,R,nx,a in SS:
                j,px=fill(ei,sd,e,k,a,W,nx)
                if j is None: continue
                R2=R-sd*(e-px) if stop=="LEVEL" else R
                if R2<=0.2*a: continue
                lst.append((j,sd,px,R2,nx))
            rec("S",k,W,stop,runS2(lst),len(SS))
    print("S",k,flush=True)
X=pd.DataFrame(rows); X.to_csv("out_oos/LAB276_LIMIT.csv",index=False); pd.set_option("display.width",250)
print(X.round(2).to_string(index=False))
