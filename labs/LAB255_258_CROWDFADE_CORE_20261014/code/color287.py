"""LAB287 (pre-registered): arrow at colour change = z24 crosses ±1 (first point of red/green), side against crowd, entry next M5 open.
Variants: COLOR (raw), COLOR+H4 (H4 EMA50 trend with side), plus re-arm rule: new arrow only after |z24| returned below 0.5.
Compare: indicator TRIGGER (H1, LAB284) and D2. Outcome: signed move ATR_H1 1/4/24/48h; trade SL 3 ATR_H1, trail peak-3R after +2R, 48h, 7.5bps."""
import numpy as np,pandas as pd
c=pd.read_pickle("/home/claude/lab251/cache_full.pkl")
BT=pd.DatetimeIndex(c["BT"]); BO,BH,BL,BC,BA=[c[k] for k in ("BO","BH","BL","BC","BA")]; N=len(BT); TE=pd.Timestamp("2025-01-01",tz="UTC")
r=pd.Series(np.load("/home/claude/lab251/ratio.npy"),index=BT)
zr=lambda w:((r-r.rolling(w).mean())/r.rolling(w).std(ddof=0)).to_numpy()
z24,z6=zr(288),zr(72)
s=pd.Series(BC,index=BT); h4=s.resample("4h").last().dropna(); e50=h4.ewm(span=50,adjust=False).mean()
tr4=pd.Series(np.where((h4>e50)&(e50>e50.shift(6)),1,np.where((h4<e50)&(e50<e50.shift(6)),-1,0)),index=h4.index); tr4.index+=pd.Timedelta("4h")
TR4=tr4.reindex(BT,method="ffill").fillna(0).to_numpy()
def color_sig(h4f):
    out=[]; armed={1:True,-1:True}
    for i in range(300,N-700):
        v,p=z24[i],z24[i-1]
        if not(np.isfinite(v) and np.isfinite(p)): continue
        for s_ in (1,-1):
            if s_*v<0.5: armed[s_]=True
        if v>=1 and p<1 and armed[1]: sd=-1; armed[1]=False
        elif v<=-1 and p>-1 and armed[-1]: sd=1; armed[-1]=False
        else: continue
        if h4f and TR4[i]!=sd: continue
        out.append((i,sd))
    return out
def d2():
    out=[]; arm=True
    for i in range(300,N-700):
        v=z6[i]
        if not np.isfinite(v): continue
        if abs(v)<1: arm=True; continue
        if arm and abs(v)>=1.5 and abs(z6[i-1])<1.5:
            sd=-int(np.sign(v)); arm=False
            if np.isfinite(z24[i]) and -np.sign(z24[i])==sd and abs(z24[i])>=0.5 and TR4[i]==sd: out.append((i,sd))
    return out
def ev(name,S):
    rows=[]
    for i,sd in S:
        ei=i+1; e=BO[ei]; a=BA[i]; R=3*a; stp=e-sd*R; pk=0; x=None
        for k in range(ei,ei+576):
            if (BL[k]<=stp) if sd>0 else (BH[k]>=stp): pnl=sd*(stp-e); x=k; break
            pk=max(pk,sd*((BH[k] if sd>0 else BL[k])-e)/R)
            if pk>=2: ns=e+sd*(pk-3)*R; stp=max(stp,ns) if sd>0 else min(stp,ns)
        if x is None: pnl=sd*(BC[ei+575]-e)
        rows.append(dict(v=name,tr=BT[i]<TE,**{f"f{H}":sd*(BC[ei+H*12-1]-e)/a for H in (1,4,24,48)},R=(pnl-7.5e-4*e)/R,win=pnl>0))
    return rows
A=pd.read_pickle("arrows.pkl"); A=A[A.tf=="1h"]
rows=ev("колір змінився (z24 перетнув ±1)",color_sig(False))+ev("колір + тренд H4",color_sig(True))+ev("D2 (як у боті)",d2())
R=pd.DataFrame(rows); R["seg"]=np.where(R.tr,"2021-24","2025-26")
O=R.groupby(["v","seg"],sort=False).agg(n=("f1","size"),**{f"рух {H}г":(f"f{H}","mean") for H in (1,4,24,48)},виграшних=("win","mean"),EV_R=("R","mean")).reset_index()
O["на_міс"]=O.n/np.where(O.seg=="2021-24",48,19.3)
Ta=A.groupby("seg").agg(**{f"рух {H}г":(f"f{H}h","mean") for H in (1,4,24,48)}).reset_index(); Ta.insert(0,"v","стрілки TRIGGER H1 (зараз)")
pd.set_option("display.width",250); print(O.drop(columns="n").round(3).to_string(index=False)); print(Ta.round(3).to_string(index=False))
