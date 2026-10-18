"""LAB285 (pre-registered): earlier H1 arrows. Base = LAB284 H1 TRIGGER (z24 setup, memory 12, breakout of 12-bar H1 structure, H1 close).
 ORACLE-1h : same arrows, entry 1h earlier (look-ahead, ceiling only)
 M15-INTRA : same H1 structure & setup, but trigger on the first M15 close beyond the level inside the H1 bar (causal, up to 45 min earlier)
 STRUCT-6  : structure of 6 H1 bars instead of 12
 Z6-SETUP  : setup from z6 (6h window) instead of z24
Outcome as LAB284: signed move in ATR_H1 (1/4/12/24/48h), trade with structural stop (min 0.5 ATR), 24h and 48h exits, 7.5 bps."""
import numpy as np,pandas as pd
c=pd.read_pickle("/home/claude/lab251/cache_full.pkl")
BT=pd.DatetimeIndex(c["BT"]); BO,BH,BL,BC,BA=[c[k] for k in ("BO","BH","BL","BC","BA")]; N=len(BT); TE=pd.Timestamp("2025-01-01",tz="UTC")
r=pd.Series(np.load("/home/claude/lab251/ratio.npy"),index=BT)
zr=lambda w:((r-r.rolling(w).mean())/r.rolling(w).std(ddof=0)).to_numpy()
Z={"z24":zr(288),"z6":zr(72)}
g=pd.Series(np.arange(N),index=BT).resample("1h").agg(["first","last","count"]).dropna(); g=g[g["count"]==12]
f=g["first"].to_numpy(int); l=g["last"].to_numpy(int); n=len(f)
o=BO[f]; cl=BC[l]; h=np.array([BH[a:b+1].max() for a,b in zip(f,l)]); lo=np.array([BL[a:b+1].min() for a,b in zip(f,l)])
m15end=np.asarray((BT+pd.Timedelta("5min")).minute%15==0)
def signals(zname,Nn,intra):
    z=Z[zname]; out=[]; lastL=lastS=-10**6; trL=trS=-10**6; M=12
    for i in range(Nn+2,n-1):
        zi=z[l[i-1]] if intra else z[l[i]]          # intrabar: setup must be known at start of bar i
        zc=z[l[i]]
        if not intra and np.isfinite(zc):
            if zc<=-1: lastL=i
            if zc>=1: lastS=i
        if intra and np.isfinite(zi):
            if zi<=-1: lastL=i-1
            if zi>=1: lastS=i-1
        d=0
        if i-lastL<=M+ (1 if intra else 0) and lastL>=lastS: d=1
        elif i-lastS<=M+(1 if intra else 0) and lastS>lastL: d=-1
        if d==0: continue
        hh=h[i-Nn:i].max(); ll=lo[i-Nn:i].min(); hhP=h[i-Nn-1:i-1].max(); llP=lo[i-Nn-1:i-1].min()
        fresh=(not(cl[i-1]>hhP)) if d>0 else (not(cl[i-1]<llP))
        if not fresh: continue
        if (d>0 and i-trL<=Nn) or (d<0 and i-trS<=Nn): continue
        k=None
        if intra:
            for j in range(f[i],l[i]+1):
                if m15end[j] and ((d>0 and BC[j]>hh) or (d<0 and BC[j]<ll)): k=j; break
        else:
            if (d>0 and cl[i]>hh) or (d<0 and cl[i]<ll): k=l[i]
        if k is None: continue
        if d>0: trL=i
        else: trS=i
        stop=min(ll,BL[f[i]:k+1].min()) if d>0 else max(hh,BH[f[i]:k+1].max())
        out.append((k,d,stop))
    return out
def evaluate(name,S,shift=0):
    rows=[]
    for k,d,stop in S:
        ei=k+1-shift
        if ei+600>=N or ei<1: continue
        e=BO[ei]; a=BA[k]; dist=max(abs(e-stop),0.5*a)
        res={f"f{H}":d*(BC[ei+H*12-1]-e)/a for H in (1,4,12,24,48)}
        for hold in (24,48):
            stp=e-d*dist; end=ei+hold*12; hs=(BL[ei:end]<=stp) if d>0 else (BH[ei:end]>=stp)
            res[f"t{hold}"]=((-dist if hs.any() else d*(BC[end-1]-e))-7.5e-4*e)/dist
        rows.append(dict(v=name,tr=BT[k]<TE,**res))
    return rows
base=signals("z24",12,False)
allr=evaluate("H1 як зараз",base)+evaluate("ПІДГЛЯД: та сама стрілка на 1 год раніше",base,12)
intra=signals("z24",12,True); allr+=evaluate("M15 всередині H1 (до 45 хв раніше)",intra)
allr+=evaluate("структура 6 барів",signals("z24",6,False))+evaluate("SETUP з z6",signals("z6",12,False))
R=pd.DataFrame(allr); R["seg"]=np.where(R.tr,"2021-24","2025-26")
O=R.groupby(["v","seg"],sort=False).agg(n=("f1","size"),**{f"рух {H}г":(f"f{H}","mean") for H in (1,4,24,48)},угода_24г=("t24","mean"),угода_48г=("t48","mean")).reset_index()
O["на_міс"]=O.n/np.where(O.seg=="2021-24",48,19.3)
pd.set_option("display.width",250); print(O.drop(columns="n").round(3).to_string(index=False))
# how much earlier is M15 intrabar on average vs H1 close
b=pd.DataFrame(base,columns=["k","d","s"]); it=pd.DataFrame(intra,columns=["k","d","s"])
print("медіана: M15-стрілка раніше за H1-стрілку на",np.median([ (b.k[(b.k>=x)&(b.k<=x+12)&(b.d==dd)].min()-x)*5 for x,dd in zip(it.k,it.d) if ((b.k>=x)&(b.k<=x+12)&(b.d==dd)).any()]),"хв; частка M15-стрілок без H1-підтвердження:",
      round(np.mean([not((b.k>=x)&(b.k<=x+12)&(b.d==dd)).any() for x,dd in zip(it.k,it.d)]),3))
