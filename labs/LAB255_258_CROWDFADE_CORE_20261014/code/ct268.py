"""LAB268 (pre-registered)
A) Early exit on countertrend start, for D2 (SL3ATR, trail 3R>2R, 48h) and S (ST H2 1.3, HTF150/250, crowd skip, SL2.2ATR, exit on flip):
   triggers (known at M5 close, exit next open): ST_H1 = Supertrend H1(1.8) flips against; EMA = EMA9 vs EMA20 H1 turns against;
   CROWD = compass sign(-z24,|z24|>=1) turns against. Modes: ALWAYS | PROFIT (only if open MTM >= +1R).
B) Countertrend engine C: trend = ST H2(1.3) dir AND HTF150/250 agree; signal = EMA9 crosses EMA20 on H1 against trend (last closed H1);
   side = against trend. Crowd conditions: ANY | CROWD_WITH_C (compass agrees with C side) | CROWD_NOT_AGAINST.
   Exit: EMA9 crosses back, SL 1.5 H1ATR, max 24h. One position at a time.
Select on 2021-24; 2025-26 shown."""
import numpy as np,pandas as pd
exec(open("st265.py").read().split("\nF={")[0])
idx=T
def tfser(tf,arr_index,vals):
    s=pd.Series(vals,index=arr_index+pd.Timedelta(tf)); return s.reindex(T,method="ffill").fillna(0).to_numpy()
def st_dir(tf,sens):
    b=df.resample(tf).agg({"o":"first","h":"max","l":"min","c":"last"}).dropna()
    o,h,l,c=[b[k].to_numpy() for k in "ohlc"]; src=(o+h+l+c)/4; pc=np.r_[c[0],c[:-1]]
    tr=np.maximum(h-l,np.maximum(abs(h-pc),abs(l-pc))); a10=rma(tr,10)
    up=src-sens*a10; dn=src+sens*a10; fu=up.copy(); fd=dn.copy(); d=np.ones(len(c),int)
    for k in range(1,len(c)):
        fu[k]=max(up[k],fu[k-1]) if c[k-1]>fu[k-1] else up[k]
        fd[k]=min(dn[k],fd[k-1]) if c[k-1]<fd[k-1] else dn[k]
        d[k]=1 if (d[k-1]==-1 and c[k]>fd[k-1]) else (-1 if (d[k-1]==1 and c[k]<fu[k-1]) else d[k-1])
    return tfser(tf,b.index,d)
STH1=st_dir("1h",1.8).astype(int); STH2=st_dir("2h",1.3).astype(int)
h1c=df.resample("1h").agg({"c":"last"}).dropna().c
EMAX=tfser("1h",h1c.index,np.sign(h1c.ewm(span=9,adjust=False).mean()-h1c.ewm(span=20,adjust=False).mean()).to_numpy()).astype(int)
CMP=np.where(np.isfinite(z24)&(np.abs(z24)>=1),-np.sign(z24),0).astype(int)
TRIG={"NONE":None,"ST_H1":STH1,"EMA9/20_H1":EMAX,"CROWD":CMP}
def path(ei,sd,e,R,end,trail,trig,mode,flip_exit=None):
    """walk M5 from ei; returns net R (before cost) and exit index"""
    stp=e-sd*R; pk=0.0
    for i in range(ei,min(end,N-1)+1):
        if flip_exit is not None and i==flip_exit: return sd*(BO[i]-e)/R,i
        if (BL[i]<=stp) if sd>0 else (BH[i]>=stp): return sd*(stp-e)/R,i
        pk=max(pk,((BH[i]-e) if sd>0 else (e-BL[i]))/R)
        if trail and pk>=2:
            ns=e+sd*(pk-3)*R; stp=max(stp,ns) if sd>0 else min(stp,ns)
        if trig is not None and i>ei and trig[i]==-sd and trig[i-1]!=-sd:
            m=sd*(BC[i]-e)/R
            if mode=="ALWAYS" or m>=1.0:
                j=min(i+1,N-1); return sd*(BO[j]-e)/R,j
    i=min(end,N-1); return sd*(BC[i]-e)/R,i
def run_D(trig,mode):
    out=[]; busy=[]   # max 2, 2nd same side & MTM>=0 approximated by: allow if <2 open same side
    open_=[]
    for ei,sd,e,d,a in EN:
        open_=[(x,s) for x,s in open_ if x>ei]
        if len(open_)>=2 or (len(open_)==1 and open_[0][1]!=sd): continue
        R=3*a; r,x=path(ei,sd,e,R,ei+575,True,trig,mode); c=COST/1e4*e/R
        out.append(dict(i=ei,x=x,r=r-c,tr=BT[ei]<TE,sd=sd,e=e,R=R)); open_.append((x,sd))
    return pd.DataFrame(out)
EN=entries("NOW",0,"ATR3")
S2=signals("2h",1.3)
def run_S(trig,mode):
    out=[]
    for n_,(si,ei,sd,dist) in enumerate(S2):
        nxt=S2[n_+1][1] if n_+1<len(S2) else N-1
        if HTF[si]!=sd: continue
        if CMP[si]==-sd: continue
        e=BO[ei]; R=dist; r,x=path(ei,sd,e,R,nxt,False,trig,mode,flip_exit=nxt); c=COST/1e4*e/R
        out.append(dict(i=ei,x=x,r=r-c,tr=BT[ei]<TE,sd=sd,e=e,R=R))
    return pd.DataFrame(out)
def mtm_eq(t):
    eq=np.zeros(N); add=np.zeros(N+1)
    for r in t.itertuples():
        seg=slice(int(r.i),int(r.x)); eq[seg]+=r.sd*(BC[seg]-r.e)/r.R; add[int(r.x)]+=r.r
    return pd.Series(np.cumsum(add[:N])+eq,index=T)
def st_(t,E):
    o={}
    for seg,m,mo in [("21",T<TE,48),("25",T>=TE,19.3)]:
        x=t[t.tr==(seg=="21")]; y=E[m]-E[m].iloc[0]; dd=float((y.cummax()-y).max())
        o.update({f"n{seg}":len(x)/mo,f"ev{seg}":x.r.mean(),f"Rmo{seg}":y.iloc[-1]/mo,f"rdd{seg}":y.iloc[-1]/dd,f"hold{seg}":((x.x-x.i)/12).mean()})
    return o
rows=[]; EQ={}
for eng,fn in [("D2",run_D),("S",run_S)]:
    for tn,tr in TRIG.items():
        for mode in (["-"] if tr is None else ["ALWAYS","PROFIT"]):
            t=fn(tr,mode); E=mtm_eq(t); EQ[(eng,tn,mode)]=E
            rows.append(dict(eng=eng,trig=tn,mode=mode,**st_(t,E))); print(eng,tn,mode,flush=True)
R=pd.DataFrame(rows); pd.set_option("display.width",250)
print("\n== A) ранній вихід на початку контртренду"); print(R.round(2).to_string(index=False))
# B) countertrend engine
def run_C(cond):
    out=[]; busy=-1
    for i in range(400,N-300):
        if i<=busy: continue
        tr=STH2[i]
        if tr==0 or HTF[i]!=tr: continue
        if not(EMAX[i]==-tr and EMAX[i-1]!=-tr): continue
        sd=-tr
        if cond=="CROWD_WITH_C" and CMP[i]!=sd: continue
        if cond=="CROWD_NOT_AGAINST" and CMP[i]==-sd: continue
        ei=i+1; e=BO[ei]; R=1.5*BA[i]; stp=e-sd*R; x=None
        for j in range(ei,min(ei+288,N-1)):
            if (BL[j]<=stp) if sd>0 else (BH[j]>=stp): r=sd*(stp-e)/R; x=j; break
            if j>ei and EMAX[j]==-sd and EMAX[j-1]!=-sd: x=min(j+1,N-1); r=sd*(BO[x]-e)/R; break
        if x is None: x=min(ei+287,N-1); r=sd*(BC[x]-e)/R
        out.append(dict(i=ei,x=x,r=r-COST/1e4*e/R,tr=BT[ei]<TE,sd=sd,e=e,R=R)); busy=x
    return pd.DataFrame(out)
rows=[]
for cond in ("ANY","CROWD_WITH_C","CROWD_NOT_AGAINST"):
    t=run_C(cond); E=mtm_eq(t); EQ[("C",cond,"-")]=E; rows.append(dict(eng="C",cond=cond,**st_(t,E)))
print("\n== B) контртрендовий двигун C"); print(pd.DataFrame(rows).round(2).to_string(index=False))
pd.to_pickle(EQ,"ct268_eq.pkl"); R.to_csv("out_oos/LAB268_CT_EXIT.csv",index=False); pd.DataFrame(rows).to_csv("out_oos/LAB268_CT_ENGINE.csv",index=False)
