"""LAB275 (pre-registered): causal EARLY triggers — how much of the LAB274 hindsight ceiling can they recover?
D2 family (exits = v006 D2: SL 3 H1ATR, trail peak-3R after +2R, 48h, max 2, crowd-compass exit at >=+1R; risk 0.10%):
  D2 (control) | Z6_1.0 (z6 cross 1.0 instead of 1.5) | Z1H/Z2H/Z3H x 1.5/2.0 (z on 12/24/36-bar window) | Z2H_1.5+Z6>=0.5 (short z cross, 6h z already leaning)
  all keep |z24|>=0.5 same sign, H4 EMA50 with side, one entry per episode (re-arm when the trigger z < 1).
S family (exits = v006 S: SL 2.2 ATR14 H2, opposite flip / EMA9/20 H1 cross against; HTF 150/250; skip crowd-against; risk 0.10%):
  S (control, flip at H2 close) | S_f1.0 / S_f0.8 (smaller factor, earlier flips) | S_H1 (H1, 1.3)
  S_PRE15: inside the H2 bar, first M15 close beyond the PREVIOUS H2 band (fd[k-1]/fu[k-1]) -> enter next M5 open; band known at bar start = causal.
         If the H2 bar closes WITHOUT a flip (false break) -> exit at next open. Otherwise identical to S.
Metric: trades/mo, EV, $/mo, MTM R/DD; price move in trade side during 6h before entry (lag); share of LAB274 ceiling recovered.
Select on 2021-24, 2025-26 shown."""
import numpy as np,pandas as pd
exec(open("ct268.py").read().split("\nrows=[]; EQ={}")[0])
r=pd.Series(np.load("ratio.npy"),index=BT)
def zroll(w):
    m=r.rolling(w,min_periods=w).mean(); s=r.rolling(w,min_periods=w).std(ddof=0); return ((r-m)/s).to_numpy()
z6=g["z6"]; ZW={"Z1H":zroll(12),"Z2H":zroll(24),"Z3H":zroll(36),"Z6":z6}
def dsig(zt,x,need6=None):
    out=[]; armed=True
    for i in range(300,N-1000):
        v=zt[i]
        if not np.isfinite(v): continue
        if abs(v)<1: armed=True; continue
        if armed and abs(v)>=x and abs(zt[i-1])<x:
            sd=-int(np.sign(v)); armed=False
            if not(np.isfinite(z24[i]) and -np.sign(z24[i])==sd and abs(z24[i])>=0.5): continue
            if TR4[i]!=sd: continue
            if need6 is not None and not(np.isfinite(z6[i]) and -np.sign(z6[i])==sd and abs(z6[i])>=need6): continue
            out.append((i+1,sd,BO[i+1],3*BA[i],BA[i]))
    return out
# sanity: control must equal entries("NOW",0,"ATR3") logic (one per z6 episode)
DV={"D2 (контроль)":entries("NOW",0,"ATR3"),"Z6 поріг 1.0":dsig(z6,1.0)}
for w in ("Z1H","Z2H","Z3H"):
    for x in (1.5,2.0): DV[f"{w} поріг {x}"]=dsig(ZW[w],x)
DV["Z2H 1.5 + z6≥0.5"]=dsig(ZW["Z2H"],1.5,0.5)
DV["Z1H 2.0 + z6≥0.5"]=dsig(ZW["Z1H"],2.0,0.5)
def lag6(lst): return np.array([sd*(BO[ei]-BO[ei-72])/BA[ei-1] for ei,sd,*_ in lst]),np.array([BT[ei]<TE for ei,*_ in lst])
rows=[]
def rec(eng,name,t,lst,ceil):
    E=mtm_eq(t); o=st_(t,E); L6,m=lag6(lst)
    rows.append(dict(eng=eng,var=name,n21=o["n21"],ev21=o["ev21"],usd21=o["Rmo21"]*100,rdd21=o["rdd21"],lag21=L6[m].mean(),
                     n25=o["n25"],ev25=o["ev25"],usd25=o["Rmo25"]*100,rdd25=o["rdd25"],lag25=L6[~m].mean()))
for nm,lst in DV.items():
    EN=lst; t=run_D(CMP,"PROFIT"); rec("D2",nm,t,lst,None); print(nm,flush=True)
# ---- S family
S_ctrl=list(S2)
def sig_tf(tf,sens): return signals(tf,sens)
SV={"S (контроль)":S_ctrl,"S фактор 1.0":sig_tf("2h",1.0),"S фактор 0.8":sig_tf("2h",0.8),"S H1 1.3":sig_tf("1h",1.3)}
for nm,lst in SV.items():
    S2=lst; t=run_S(EMAX,"ALWAYS"); rec("S",nm,t,[(ei,sd) for si,ei,sd,d in lst],None); print(nm,flush=True)
S2=S_ctrl
# S_PRE15
b=df.resample("2h").agg({"o":"first","h":"max","l":"min","c":"last"}).dropna()
o,h,l,c=[b[k].to_numpy() for k in "ohlc"]; src=(o+h+l+c)/4; pc=np.r_[c[0],c[:-1]]
tr=np.maximum(h-l,np.maximum(abs(h-pc),abs(l-pc))); a10=rma(tr,10); a14=rma(tr,14)
up=src-1.3*a10; dn=src+1.3*a10; fu=up.copy(); fd=dn.copy(); d=np.ones(len(c),int)
for k in range(1,len(c)):
    fu[k]=max(up[k],fu[k-1]) if c[k-1]>fu[k-1] else up[k]
    fd[k]=min(dn[k],fd[k-1]) if c[k-1]<fd[k-1] else dn[k]
    d[k]=1 if (d[k-1]==-1 and c[k]>fd[k-1]) else (-1 if (d[k-1]==1 and c[k]<fu[k-1]) else d[k-1])
bstart=np.searchsorted(T.values,b.index.values); bend=np.searchsorted(T.values,(b.index+pd.Timedelta("2h")).values)
m15end=np.asarray((T+pd.Timedelta("5min")).minute%15==0)
pre=[]; nfalse=0
for k in range(31,len(c)-1):
    lvl_l=fd[k-1]; lvl_s=fu[k-1]; dir0=d[k-1]; sd=-dir0; lvl=lvl_l if sd>0 else lvl_s
    for i in range(bstart[k],min(bend[k],N-2)):
        if not m15end[i] or i==bend[k]-1: continue        # last M15 of bar == normal S at close
        if (BC[i]>lvl) if sd>0 else (BC[i]<lvl):
            if HTF[i]!=sd or CMP[i]==-sd: break
            ei=i+1; flipped=(d[k]==sd)
            # exit: false break -> next open after H2 close; else as S (next opposite flip / EMA cross)
            if not flipped: xi=min(bend[k],N-1); nfalse+=1
            else:
                nx=[e2 for s2,e2,s_,dd in S_ctrl if e2>bend[k]-1]; xi=nx[0] if nx else N-1
            pre.append((ei,sd,2.2*a14[k-1],xi)); break
out=[]
for ei,sd,R,xi in pre:
    e=BO[ei]; rr,x=path(ei,sd,e,R,xi,False,EMAX,"ALWAYS",flip_exit=xi)
    out.append(dict(i=ei,x=x,r=rr-COST/1e4*e/R,tr=BT[ei]<TE,sd=sd,e=e,R=R))
t=pd.DataFrame(out); rec("S","S PRE: M15 пробій лінії H2",t,[(ei,sd) for ei,sd,R,xi in pre],None)
print("PRE false-break share",nfalse/len(pre))
Rr=pd.DataFrame(rows)
CEIL={("D2","21"):705.6,("D2","25"):854.4,("S","21"):640.3,("S","25"):587.8}
for eng in ("D2","S"):
    base=Rr[(Rr.eng==eng)].iloc[0]
    for sg in ("21","25"):
        Rr.loc[Rr.eng==eng,f"ceil{sg}"]=(Rr.loc[Rr.eng==eng,f"usd{sg}"]-base[f"usd{sg}"])/(CEIL[(eng,sg)]-base[f"usd{sg}"])
Rr.to_csv("out_oos/LAB275_EARLY.csv",index=False); pd.set_option("display.width",260)
print(Rr.round(2).to_string(index=False))
