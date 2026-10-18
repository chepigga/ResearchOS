"""LAB284 (pre-registered): BinanceLSZ TRIGGER arrows (v1.06+ logic, without ARMED) vs the REVERSED arrows.
Chart TF M30 (user's) and M15/H1 for robustness. z24 at bar close (v1.07 mapping). SETUP = z beyond ±1 within last 12 bars (memory),
side against crowd. TRIGGER = first close beyond max/min of previous 12 bars in setup direction, >12 bars since last trigger of that side.
Outcome: signed forward move in ATR_H1 for arrow direction at 1h/4h/12h/24h/48h (reversed = minus); MAE/MFE first 4h.
Trade view (both directions): stop = indicator's structural stop distance (min 0.5 ATR_H1), exit 24h, cost 7.5 bps."""
import numpy as np,pandas as pd
c=pd.read_pickle("/home/claude/lab251/cache_full.pkl")
BT=pd.DatetimeIndex(c["BT"]); BO,BH,BL,BC,BA=[c[k] for k in ("BO","BH","BL","BC","BA")]; N=len(BT); TE=pd.Timestamp("2025-01-01",tz="UTC")
r=pd.Series(np.load("/home/claude/lab251/ratio.npy"),index=BT)
z24=((r-r.rolling(288).mean())/r.rolling(288).std(ddof=0)).to_numpy()
idx=np.arange(N)
rows=[]
for tf,nb in (("15min",3),("30min",6),("1h",12)):
    g=pd.Series(idx,index=BT).resample(tf).agg(["first","last","count"]).dropna(); g=g[g["count"]==nb]
    f=g["first"].to_numpy(int); l=g["last"].to_numpy(int)
    o=BO[f]; c_=BC[l]; h=np.maximum.reduceat(BH,f) if False else np.array([BH[a:b+1].max() for a,b in zip(f,l)]); lo=np.array([BL[a:b+1].min() for a,b in zip(f,l)])
    z=z24[l]; n=len(f); Nn=12; M=12
    lastL=lastS=-10**6; trL=trS=-10**6
    for i in range(Nn+1,n-1):
        if np.isfinite(z[i]):
            if z[i]<=-1: lastL=i
            if z[i]>=1: lastS=i
        d=0
        if i-lastL<=M and lastL>=lastS: d=1
        elif i-lastS<=M and lastS>lastL: d=-1
        if d==0: continue
        hh=h[i-Nn:i].max(); ll=lo[i-Nn:i].min(); hhP=h[i-Nn-1:i-1].max(); llP=lo[i-Nn-1:i-1].min()
        sig=0
        if d>0 and c_[i]>hh and not(c_[i-1]>hhP) and i-trL>Nn: trL=i; sig=1; stop=min(ll,lo[i])
        if d<0 and c_[i]<ll and not(c_[i-1]<llP) and i-trS>Nn: trS=i; sig=-1; stop=max(hh,h[i])
        if sig==0: continue
        k=l[i]; ei=k+1
        if ei+600>=N: continue
        e=BO[ei]; a=BA[k]
        fw={H:sig*(BC[min(ei+H*12-1,N-1)]-e)/a for H in (1,4,12,24,48)}
        mfe=sig*((BH[ei:ei+48].max()-e) if sig>0 else (BL[ei:ei+48].min()-e))/a
        mae=sig*((BL[ei:ei+48].min()-e) if sig>0 else (BH[ei:ei+48].max()-e))/a
        dist=max(abs(e-stop),0.5*a)
        def trade(sd):
            stp=e-sd*dist; end=ei+288
            hs=(BL[ei:end]<=stp) if sd>0 else (BH[ei:end]>=stp)
            pnl=-dist if hs.any() else sd*(BC[end-1]-e)
            return (pnl-7.5e-4*e)/dist
        rows.append(dict(tf=tf,tr=BT[k]<TE,sig=sig,**{f"f{H}h":v for H,v in fw.items()},mfe4=mfe,mae4=mae,stopATR=dist/a,arrow=trade(sig),rev=trade(-sig)))
R=pd.DataFrame(rows); R["seg"]=np.where(R.tr,"2021-24","2025-26")
pd.set_option("display.width",250)
def t(x): return x.mean()/(x.std()/np.sqrt(len(x)))
out=[]
for (tf,seg),x in R.groupby(["tf","seg"],sort=False):
    mo=48 if seg=="2021-24" else 19.3
    out.append(dict(ТФ=tf,період=seg,стрілок_міс=len(x)/mo,**{f"рух {H}г":x[f"f{H}h"].mean() for H in (1,4,12,24,48)},
                    t_24г=t(x.f24h),стоп_ATR=x.stopATR.median(),угода_як_стрілка_R=x.arrow.mean(),угода_навпаки_R=x.rev.mean()))
print("Рух ціни в бік СТРІЛКИ (ATR H1; від'ємне = навпаки було б краще):")
print(pd.DataFrame(out).round(3).to_string(index=False))
R.to_pickle("arrows.pkl")
