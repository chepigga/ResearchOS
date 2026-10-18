"""LAB279 (pre-registered): 'profile as a magnet' once price is moving. Profile W=336h (step1 settings), hourly sample (decision at H1 close).
M1 speed: density at current price q = s[bin]/max(s). Outcome next 4h: range/ATR and time to move 1 ATR from price. Quintiles of q,
   stratified by the past-4h range (volatility clustering control).
M2 HVN braking: price arrives at an HVN level (H1 close within 0.25 ATR, was >=1 ATR away 12h ago). Next 12h: PASS (>=1 ATR beyond),
   REJECT (>=1 ATR back), STALL (neither). Control: same arrivals at random non-HVN levels (density <50% of max, >=1 ATR from any HVN),
   matched by approach speed.
M3 POC / HVN magnet: at each hour, level L (POC or nearest HVN) at distance d in [0.5,4] ATR. P(touch L within 24h) vs P(touch mirror level
   at the same distance on the other side). Random walk -> equal. Same for 'nearest HVN in direction of the last 4h move' (momentum + magnet)."""
import numpy as np,pandas as pd
exec(open("step1.py").read().split("COST=7.5")[0])
W=336; run=np.zeros(NB); rec=[]
hc=np.searchsorted(BT.values,(hours+pd.Timedelta("1h")).values)-1   # last M5 bar of hour h
for h in range(len(hours)):
    run+=M[h]
    if h>=W: run-=M[h-W]
    if h<W: continue
    i=hc[h]
    if i<300 or i>N-300 or BT[i].floor("1h")!=hours[h]: continue
    s=gaussian_filter1d(run,1.5); mx=s.max(); pk,_=find_peaks(s,prominence=0.05*mx)
    p=BC[i]; k=b(np.array([p]))[0]; a=BA[i]
    hv=bprice(pk) if len(pk) else np.array([])
    rec.append((i,s[k]/mx,bprice(int(np.argmax(s))),hv,a,s))
print("hours",len(rec),flush=True)
FH=lambda i,n:(BH[i+1:i+1+n].max(),BL[i+1:i+1+n].min())
# ---------- M1
r1=[]
for i,q,poc,hv,a,s in rec:
    hi,lo=FH(i,48); pr=(BH[i-47:i+1].max()-BL[i-47:i+1].min())/a
    up=np.nonzero(BH[i+1:i+577]>=BC[i]+a)[0]; dn=np.nonzero(BL[i+1:i+577]<=BC[i]-a)[0]
    t1=min(up[0] if len(up) else 999,dn[0] if len(dn) else 999)/12
    r1.append(dict(i=i,q=q,rng=(hi-lo)/a,past=pr,t1=t1))
R1=pd.DataFrame(r1); R1["tr"]=BT[R1.i.to_numpy()]<TE
R1["qb"]=pd.qcut(R1.q,5,labels=["LVN 0-20%","20-40","40-60","60-80","HVN 80-100%"]); R1["pb"]=pd.qcut(R1.past,3,labels=["спокій","сер.","волат."])
print("\n== M1: діапазон наступних 4 год (ATR) і час до руху на 1 ATR (год), за щільністю профілю на поточній ціні")
print(R1.groupby(["qb"],observed=True).agg(n=("rng","size"),rng4h=("rng","median"),t1ATR=("t1","median")).round(2).to_string())
print("\nстратифікація за минулою волатильністю (медіана діапазону 4 год):")
print(R1.pivot_table(index="qb",columns="pb",values="rng",aggfunc="median",observed=True).round(2).to_string())
print("\nпо періодах (медіана діапазону 4 год):"); print(R1.pivot_table(index="qb",columns="tr",values="rng",aggfunc="median",observed=True).round(2).to_string())
# ---------- M2
rng_=np.random.default_rng(279); r2=[]
lastev={}
for n_,(i,q,poc,hv,a,s) in enumerate(rec):
    p=BC[i]; p12=BC[i-144]
    cands=[("HVN",L) for L in hv]
    # control levels: random within ±4 ATR, low density, >=1 ATR from any HVN
    for _ in range(6):
        L=p+rng_.uniform(-0.25,0.25)*a
        kk=b(np.array([L]))[0]
        if s[kk]<0.5*s.max() and (len(hv)==0 or np.min(np.abs(hv-L))>=a): cands.append(("CTRL",L))
    for typ,L in cands:
        if abs(p-L)>0.25*a or abs(p12-L)<1.0*a: continue
        d=np.sign(L-p12)                       # direction of approach
        key=(typ,round(L/(0.5*a)))
        if i-lastev.get(key,-10**9)<288: continue
        lastev[key]=i
        hi,lo=FH(i,144)
        pas=(hi>=L+a) if d>0 else (lo<=L-a); rej=(lo<=L-a) if d>0 else (hi>=L+a)
        if pas and rej:   # which first
            up=np.argmax(BH[i+1:i+145]>=L+a) if d>0 else np.argmax(BL[i+1:i+145]<=L-a)
            bk=np.argmax(BL[i+1:i+145]<=L-a) if d>0 else np.argmax(BH[i+1:i+145]>=L+a)
            res="PASS" if up<bk else "REJECT"
        else: res="PASS" if pas else ("REJECT" if rej else "STALL")
        speed=abs(p-p12)/a
        r2.append(dict(i=i,typ=typ,res=res,speed=speed,tr=BT[i]<TE))
R2=pd.DataFrame(r2); R2["sb"]=pd.cut(R2.speed,[1,1.5,2.5,99],labels=["підхід 1-1.5ATR","1.5-2.5","2.5+"])
print("\n== M2: ціна прийшла до рівня (за 12 год пройшла ≥1 ATR). Що далі за 12 год")
T2=R2.groupby(["typ","sb"],observed=True).res.value_counts(normalize=True).unstack().round(3); T2["n"]=R2.groupby(["typ","sb"],observed=True).size(); print(T2.to_string())
T2b=R2.groupby(["tr","typ"]).res.value_counts(normalize=True).unstack().round(3); print(T2b.to_string())
# ---------- M3
r3=[]
for i,q,poc,hv,a,s in rec:
    p=BC[i]; mom=np.sign(BC[i]-BC[i-48])
    levels=[("POC",poc)]
    if len(hv):
        ab=hv[hv>p+0.5*a]; be=hv[hv<p-0.5*a]
        nx=ab.min() if mom>0 and len(ab) else (be.max() if mom<0 and len(be) else None)
        if nx is not None: levels.append(("HVN у бік руху 4h",nx))
        nb=hv[np.abs(hv-p)>=0.5*a]
        if len(nb): levels.append(("найближчий HVN",nb[np.argmin(np.abs(nb-p))]))
    hi,lo=FH(i,288)
    for typ,L in levels:
        d=abs(L-p)/a
        if d<0.5 or d>4: continue
        M_=2*p-L
        hitL=(hi>=L) if L>p else (lo<=L); hitM=(hi>=M_) if M_>p else (lo<=M_)
        r3.append(dict(typ=typ,d=d,hitL=hitL,hitM=hitM,tr=BT[i]<TE))
R3=pd.DataFrame(r3); R3["db"]=pd.cut(R3.d,[0.5,1,2,4],labels=["0.5-1 ATR","1-2","2-4"])
print("\n== M3: P(дотик рівня за 24 год) проти дзеркального рівня на тій самій відстані")
T3=R3.groupby(["typ","db","tr"],observed=True).agg(n=("hitL","size"),рівень=("hitL","mean"),дзеркало=("hitM","mean")); T3["різниця"]=T3.рівень-T3.дзеркало
print(T3.round(3).to_string())
for t,x in (("R1",R1),("R2",R2),("R3",R3)): x.to_pickle(f"mag_{t}.pkl")
