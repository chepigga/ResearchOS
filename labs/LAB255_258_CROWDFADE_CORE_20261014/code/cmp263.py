"""LAB263 (pre-registered) compass x entry interaction.
Compass: D2 signal (z6 cross 1.5, |z24|>=0.5 same sign, EMA50-H4 with side) -> side for next 48h (newer signal overrides).
Also robustness compass C24: side=-sign(z24) when |z24|>=1 (continuous, no H4).
Entries (generated independently of compass, both sides):
 US_OR   : opening range 13:30-14:30 UTC; first M5 close beyond OR high/low between 14:30-20:00 -> one trade/day
 LDN_OR  : opening range 07:00-08:00 UTC; first break 08:00-13:00 -> one trade/day
 BRK1H   : M5 close beyond high/low of previous 12 bars; cooldown 2h per side
 PB_EMA  : H1 EMA20 slope(6h) defines side; limit at last closed H1 EMA20 when price on trend side; fill on touch; cooldown 4h
 ST_H1   : Supertrend(10,3) H1 flip, entry next M5 open after H1 close
Exits (uniform): XA = SL 1 H1ATR, trail stop=peak-2R after +2R, max 12h | XB = SL 2 ATR, trail peak-2R after +2R, max 24h.
Each trade simulated standalone (no portfolio interaction). Cost 7.5bps. Stats by compass state at signal: WITH / AGAINST / NONE."""
import numpy as np,pandas as pd
exec(open("sw260.py").read().split("\nrows=[]")[0])
z24=g["z24"]; COST=7.5
T=pd.DatetimeIndex(BT); hr=T.hour+T.minute/60.0; day=T.floor("D")
# compass
comp=np.zeros(N,int); last=-10**9; cs=0
sigd={i:sd for i,sd in SIG}
for i in range(N):
    if i in sigd: cs=sigd[i]; last=i
    comp[i]=cs if i-last<=576 else 0
c24=np.where(np.isfinite(z24)&(np.abs(z24)>=1),-np.sign(z24),0).astype(int)
# H1 frame
df=pd.DataFrame({"o":BO,"h":BH,"l":BL,"c":BC},index=T)
h1=df.resample("1h").agg({"o":"first","h":"max","l":"min","c":"last"}).dropna()
e20=h1.c.ewm(span=20,adjust=False).mean(); slope=np.sign(e20-e20.shift(6))
def asof(s):  # last closed H1 value at each M5 bar
    x=s.copy(); x.index=x.index+pd.Timedelta("1h"); return x.reindex(T,method="ffill").to_numpy()
E20=asof(e20); SLP=asof(slope)
# supertrend H1
tr=np.maximum(h1.h-h1.l,np.maximum((h1.h-h1.c.shift()).abs(),(h1.l-h1.c.shift()).abs())); atr=tr.ewm(alpha=1/10,adjust=False).mean()
hl2=(h1.h+h1.l)/2; up=(hl2-3*atr).to_numpy(); dn=(hl2+3*atr).to_numpy(); C1=h1.c.to_numpy()
st=np.zeros(len(h1)); dirn=np.ones(len(h1),int); fu=up.copy(); fd=dn.copy()
for k in range(1,len(h1)):
    fu[k]=max(up[k],fu[k-1]) if C1[k-1]>fu[k-1] else up[k]
    fd[k]=min(dn[k],fd[k-1]) if C1[k-1]<fd[k-1] else dn[k]
    dirn[k]=1 if C1[k]>fd[k-1] else (-1 if C1[k]<fu[k-1] else dirn[k-1])
flip=pd.Series(np.where(np.r_[0,np.diff(dirn)]!=0,dirn,0),index=h1.index+pd.Timedelta("1h"))
ev=[]  # (signal_bar, entry_bar, side, entry_price)
# session OR
def session(o0,o1,t1,name):
    out=[]
    for d,idx in pd.Series(np.arange(N),index=T).groupby(day):
        ix=idx.to_numpy(); h=hr[ix]
        orr=ix[(h>=o0)&(h<o1)]
        if len(orr)<10: continue
        hi=BH[orr].max(); lo=BL[orr].min()
        for i in ix[(h>=o1)&(h<t1)]:
            if BC[i]>hi: out.append((i,i+1,1,BO[min(i+1,N-1)],name)); break
            if BC[i]<lo: out.append((i,i+1,-1,BO[min(i+1,N-1)],name)); break
    return out
ev+=session(13.5,14.5,20,"US_OR"); ev+=session(7,8,13,"LDN_OR")
hh=pd.Series(BH).rolling(12).max().shift(1).to_numpy(); ll=pd.Series(BL).rolling(12).min().shift(1).to_numpy()
lastb={1:-10**9,-1:-10**9}
for i in range(300,N-300):
    if BC[i]>hh[i] and i-lastb[1]>=24: ev.append((i,i+1,1,BO[i+1],"BRK1H")); lastb[1]=i
    if BC[i]<ll[i] and i-lastb[-1]>=24: ev.append((i,i+1,-1,BO[i+1],"BRK1H")); lastb[-1]=i
lp=-10**9
for i in range(300,N-300):
    s=SLP[i]; lv=E20[i]
    if not np.isfinite(lv) or s==0 or i-lp<48: continue
    if s>0 and BC[i-1]>lv and BL[i]<=lv: ev.append((i,i,1,min(lv,BO[i]),"PB_EMA")); lp=i
    elif s<0 and BC[i-1]<lv and BH[i]>=lv: ev.append((i,i,-1,max(lv,BO[i]),"PB_EMA")); lp=i
fl=flip[flip!=0]; pos=np.searchsorted(T.values,fl.index.values)
for p_,d_ in zip(pos,fl.to_numpy()):
    if 300<p_<N-300: ev.append((p_-1,p_,int(d_),BO[p_],"ST_H1"))
print({k:sum(1 for e in ev if e[4]==k) for k in ["US_OR","LDN_OR","BRK1H","PB_EMA","ST_H1"]},flush=True)
def run(si,ei,sd,e,k,Hh):
    a=BA[si]; R=k*a; stp=e-sd*R; pk=0.0; c=COST/1e4*e
    start=ei+1 if si==ei else ei   # limit fill bar: manage from next bar
    for i in range(start,min(ei+Hh*12,N-1)):
        if (BL[i]<=stp) if sd>0 else (BH[i]>=stp): return (sd*(stp-e)-c)/R
        pk=max(pk,((BH[i]-e) if sd>0 else (e-BL[i]))/R)
        if pk>=2:
            ns=e+sd*(pk-2)*R; stp=max(stp,ns) if sd>0 else min(stp,ns)
    i=min(ei+Hh*12-1,N-1); return (sd*(BC[i]-e)-c)/R
rows=[]
for si,ei,sd,e,nm in ev:
    if not np.isfinite(BA[si]) or BA[si]<=0: continue
    st_=comp[si]; s24=c24[si]
    rows.append(dict(e=nm,tr=BT[si]<TE,side=sd,
        comp="ЗА" if st_==sd else ("ПРОТИ" if st_==-sd else "ПОЗА"),
        c24="ЗА" if s24==sd else ("ПРОТИ" if s24==-sd else "ПОЗА"),
        XA=run(si,ei,sd,e,1.0,12),XB=run(si,ei,sd,e,2.0,24)))
D=pd.DataFrame(rows); D.to_pickle("cmp263.pkl")
mo={True:48,False:19.3}
for cm in ("comp","c24"):
    for X in ("XA","XB"):
        print(f"\n===== компас {'D2 48 год' if cm=='comp' else 'z24 (|z24|>=1)'}, вихід {X} =====")
        G=D.groupby(["e","tr",cm])[X].agg(n="count",ev="mean",wr=lambda x:(x>0).mean()).reset_index()
        G["/міс"]=G.apply(lambda r:r.n/mo[r.tr],axis=1); G["seg"]=np.where(G.tr,"21-24","25-26")
        P=G.pivot_table(index=["e",cm],columns="seg",values=["/міс","ev"],sort=False).round(2)
        print(P.to_string())
