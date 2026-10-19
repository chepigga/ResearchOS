"""LAB286 (pre-registered): FAIL arrows of BinanceLSZ (v1.06 logic). After a TRIGGER, within 3 bars a bar closes back beyond the breakout
level AND beyond the trigger bar's open -> FAIL. Question: is FAIL a reversal ('buy' after failed SHORT)?
Measure signed move in the FAIL direction (opposite of the original trigger) at 1/4/12/24/48h in ATR_H1; share of FAILs where price moved
>= +1 ATR in FAIL direction before -1 ATR; trade in FAIL direction with indicator stop (min 0.5 ATR) 24h/48h exits, 7.5 bps.
Also: what the original trigger trade did after the FAIL bar (keep holding vs exit)."""
import numpy as np,pandas as pd
c=pd.read_pickle("/home/claude/lab251/cache_full.pkl")
BT=pd.DatetimeIndex(c["BT"]); BO,BH,BL,BC,BA=[c[k] for k in ("BO","BH","BL","BC","BA")]; N=len(BT); TE=pd.Timestamp("2025-01-01",tz="UTC")
r=pd.Series(np.load("/home/claude/lab251/ratio.npy"),index=BT)
z24=((r-r.rolling(288).mean())/r.rolling(288).std(ddof=0)).to_numpy()
rows=[]
for tf,nb in (("15min",3),("30min",6),("1h",12)):
    g=pd.Series(np.arange(N),index=BT).resample(tf).agg(["first","last","count"]).dropna(); g=g[g["count"]==nb]
    f=g["first"].to_numpy(int); l=g["last"].to_numpy(int); n=len(f)
    o=BO[f]; cl=BC[l]; h=np.array([BH[a:b+1].max() for a,b in zip(f,l)]); lo=np.array([BL[a:b+1].min() for a,b in zip(f,l)])
    z=z24[l]; Nn=12; M=12; K=3
    lastL=lastS=-10**6; trL=trS=-10**6; lvlL=lvlS=opL=opS=0.0; failL=failS=True; ntrg=0
    for i in range(Nn+2,n-1):
        # FAIL check first (as indicator)
        for sd in (1,-1):
            tr=trL if sd>0 else trS; lvl=lvlL if sd>0 else lvlS; op=opL if sd>0 else opS; done=failL if sd>0 else failS
            dI=i-tr
            if not done and 1<=dI<=K and ((sd>0 and cl[i]<lvl and cl[i]<op) or (sd<0 and cl[i]>lvl and cl[i]>op)):
                if sd>0: failL=True
                else: failS=True
                k=l[i]; ei=k+1
                if ei+600>=N: continue
                fd=-sd; e=BO[ei]; a=BA[k]
                stop=(max(h[i],h[tr]) if fd<0 else min(lo[i],lo[tr])); dist=max(abs(e-stop),0.5*a)
                fw={H:fd*(BC[ei+H*12-1]-e)/a for H in (1,4,12,24,48)}
                up=np.nonzero((BH[ei:ei+576]>=e+a) if fd>0 else (BL[ei:ei+576]<=e-a))[0]; dn=np.nonzero((BL[ei:ei+576]<=e-a) if fd>0 else (BH[ei:ei+576]>=e+a))[0]
                first=(up[0] if len(up) else 10**9)<(dn[0] if len(dn) else 10**9)
                res={}
                for hold in (24,48):
                    stp=e-fd*dist; end=ei+hold*12; hs=(BL[ei:end]<=stp) if fd>0 else (BH[ei:end]>=stp)
                    res[f"t{hold}"]=((-dist if hs.any() else fd*(BC[end-1]-e))-7.5e-4*e)/dist
                rows.append(dict(tf=tf,tr=BT[k]<TE,dir=fd,first1ATR=first,**{f"f{H}":v for H,v in fw.items()},**res))
        if np.isfinite(z[i]):
            if z[i]<=-1: lastL=i
            if z[i]>=1: lastS=i
        d=0
        if i-lastL<=M and lastL>=lastS: d=1
        elif i-lastS<=M and lastS>lastL: d=-1
        if d==0: continue
        hh=h[i-Nn:i].max(); ll=lo[i-Nn:i].min(); hhP=h[i-Nn-1:i-1].max(); llP=lo[i-Nn-1:i-1].min()
        if d>0 and cl[i]>hh and not(cl[i-1]>hhP) and i-trL>Nn: trL=i; lvlL=hh; opL=o[i]; failL=False; ntrg+=1
        if d<0 and cl[i]<ll and not(cl[i-1]<llP) and i-trS>Nn: trS=i; lvlS=ll; opS=o[i]; failS=False; ntrg+=1
    print(tf,"тригерів",ntrg,flush=True)
R=pd.DataFrame(rows); R["seg"]=np.where(R.tr,"2021-24","2025-26")
O=R.groupby(["tf","seg"],sort=False).agg(n=("f1","size"),**{f"рух {H}г":(f"f{H}","mean") for H in (1,4,12,24,48)},
   спершу_1ATR_у_бік_FAIL=("first1ATR","mean"),угода_24г=("t24","mean"),угода_48г=("t48","mean")).reset_index()
O["FAIL_на_міс"]=O.n/np.where(O.seg=="2021-24",48,19.3)
pd.set_option("display.width",250); print(O.drop(columns="n").round(3).to_string(index=False))
R.to_pickle("fail.pkl")
