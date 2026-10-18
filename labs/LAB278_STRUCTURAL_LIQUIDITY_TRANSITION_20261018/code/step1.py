"""LAB278 Step 1 (pre-registered before looking at outcomes).
Profile: Binance BTCUSDT 5m volume spread uniformly over [low,high] in 0.2% log bins (validated vs aggTrades in step0: corr 0.999, HVN/LVN match 97-100%).
Window W = 168h / 336h / 720h ending at the last closed H1; Gaussian smoothing 1.5 bins; HVN = peaks with prominence >= 5% of max;
LVN = min between two adjacent HVNs with s[LVN] <= lr*min(HVN_A,HVN_B), lr = 0.5 | 0.7. Profile of hour h is used for M5 bars of hour h+1 (causal).
Event (exit from HVN_A into LVN toward HVN_B): M5 close crosses the LVN price in direction A->B, price touched HVN_A level (±1 bin) within last 12h,
  dA = |entry - A| >= 0.3 ATR_H1 and dB = |B - entry| >= 0.3 ATR_H1. Dedup: same direction & LVN within ±2 bins once per 24h.
Entry = next M5 open. Outcome within 48h, M5 high/low first passage: B first (continuation / 'breakthrough'), A first (return), timeout.
  Same bar touching both -> A (conservative). Acceleration = B reached within 6h.
Null (driftless random walk): P(B first) = dA/(dA+dB). Edge = observed - null.
Trade view: continuation, stop at A (R = dA), target B, 48h time exit, cost 7.5 bps round trip; fade = mirror (gross = -continuation).
Features for step 2 stored: OI change 6h/24h, z6, z24 (crowd sign vs direction), taker buy share (12 bars), 1h momentum, dA,dB in ATR, LVN depth."""
import numpy as np,pandas as pd,zipfile,sys
from vp import *
c=pd.read_pickle("/home/claude/lab251/cache_full.pkl")
BT=pd.DatetimeIndex(c["BT"]); BO,BH,BL,BC,BA=[c[k] for k in ("BO","BH","BL","BC","BA")]; N=len(BT)
TE=pd.Timestamp("2025-01-01",tz="UTC")
v=pd.read_pickle("/home/claude/lab251/v5m.pkl"); v=v[v.index>="2020-11-25"]
hours=pd.date_range(v.index[0].floor("1h"),v.index[-1].floor("1h"),freq="1h")
M=hourly_from_bars(v.index,v.low.to_numpy(),v.high.to_numpy(),v.volume.to_numpy(),hours)
# features
r=pd.Series(np.load("/home/claude/lab251/ratio.npy"),index=BT)
def zr(w): m=r.rolling(w,min_periods=w).mean(); s=r.rolling(w,min_periods=w).std(ddof=0); return ((r-m)/s).to_numpy()
z6,z24=zr(72),zr(288)
with zipfile.ZipFile("/home/claude/data/BTCUSDT_flow_2021-01-2026-08.csv.zip") as zf:
    nm=[x for x in zf.namelist() if x.endswith(".csv")][0]; f=pd.read_csv(zf.open(nm))
f["time"]=pd.to_datetime(f.create_time,utc=True); f=f.sort_values("time").drop_duplicates("time").set_index("time")
OI=f.sum_open_interest.astype(float).where(lambda x:x>0).resample("5min").last().reindex(BT,method="ffill").ffill().to_numpy()
TK=v.taker_ratio.reindex(BT).to_numpy(); TK12=pd.Series(TK).rolling(12).mean().to_numpy()
def ch(a,k): return np.r_[np.full(k,np.nan),a[k:]/a[:-k]-1]
OI6,OI24=ch(OI,72),ch(OI,288)
mom1=np.r_[np.full(12,np.nan),BC[12:]-BC[:-12]]/BA
LOW12=pd.Series(BL).rolling(144,min_periods=1).min().shift(1).to_numpy(); HIGH12=pd.Series(BH).rolling(144,min_periods=1).max().shift(1).to_numpy()
hb=np.searchsorted(hours.values,BT.floor("1h").values)   # hour index of each M5 bar
first_bar_of_hour={}
starts=np.r_[0,np.nonzero(np.diff(hb))[0]+1]
COST=7.5
rows=[]
for W in (168,336,720):
    run=np.zeros(NB); 
    for h in range(len(hours)):
        run+=M[h]
        if h>=W: run-=M[h-W]
        if h<W: continue
        # bars of hour h+1 in BT
        k=np.searchsorted(starts,0)  # dummy
        hh=h+1
        j0=np.searchsorted(hb,hh); j1=np.searchsorted(hb,hh+1)
        if j0>=j1 or j0<300 or j1>N-600: continue
        s=gaussian_filter1d(run,1.5); pk,_=find_peaks(s,prominence=0.05*s.max())
        if len(pk)<2: continue
        for lr in (0.5,0.7):
            for a_,c_ in zip(pk[:-1],pk[1:]):
                m=a_+int(np.argmin(s[a_:c_+1]))
                if s[m]>lr*min(s[a_],s[c_]): continue
                pl,pm,ph=bprice(a_),bprice(m),bprice(c_); depth=s[m]/min(s[a_],s[c_])
                for i in range(max(j0,1),j1):
                    for d in (1,-1):
                        A,B=(pl,ph) if d>0 else (ph,pl)
                        crossed=(BC[i-1]<pm<=BC[i]) if d>0 else (BC[i-1]>pm>=BC[i])
                        if not crossed: continue
                        came=(LOW12[i]<=A*(1+STEP)) if d>0 else (HIGH12[i]>=A*(1-STEP))
                        if not came: continue
                        ei=i+1; e=BO[ei]; dA=d*(e-A); dB=d*(B-e); a=BA[i]
                        if dA<0.3*a or dB<0.3*a: continue
                        rows.append(dict(W=W,lr=lr,i=i,ei=ei,d=d,lvn_bin=m,A=A,B=B,e=e,dA=dA,dB=dB,atr=a,depth=depth))
    print("W",W,len(rows),flush=True)
E=pd.DataFrame(rows)
# dedup: same W,lr,d, lvn within ±2 bins within 24h (288 bars)
E=E.sort_values(["W","lr","d","i"]); keep=[]; last={}
for r_ in E.itertuples():
    key=(r_.W,r_.lr,r_.d); L=last.setdefault(key,[])
    L[:]=[(ii,bb) for ii,bb in L if r_.i-ii<288]
    if any(abs(bb-r_.lvn_bin)<=2 for ii,bb in L): keep.append(False); continue
    L.append((r_.i,r_.lvn_bin)); keep.append(True)
E=E[np.array(keep)].reset_index(drop=True)
# outcomes
out=[]
for r_ in E.itertuples():
    ei,d,A,B=r_.ei,r_.d,r_.A,r_.B; end=min(ei+576,N-1)
    hiB=(BH[ei:end]>=B) if d>0 else (BL[ei:end]<=B)
    hiA=(BL[ei:end]<=A) if d>0 else (BH[ei:end]>=A)
    kb=np.argmax(hiB) if hiB.any() else 10**9; ka=np.argmax(hiA) if hiA.any() else 10**9
    if ka==10**9 and kb==10**9: res="TIMEOUT"; pnl=d*(BC[end-1]-r_.e); k=end-1-ei
    elif ka<=kb: res="A"; pnl=-r_.dA; k=ka
    else: res="B"; pnl=r_.dB; k=kb
    out.append(dict(res=res,pnl=pnl,hrs=k/12))
E=pd.concat([E,pd.DataFrame(out)],axis=1)
E["p0"]=E.dA/(E.dA+E.dB); E["hitB"]=(E.res=="B").astype(float)
E["accel"]=((E.res=="B")&(E.hrs<=6)).astype(float)
E["grossR"]=E.pnl/E.dA; E["costR"]=COST/1e4*E.e/E.dA; E["netR_cont"]=E.grossR-E.costR; E["netR_fade"]=-E.grossR*E.dA/E.dB-COST/1e4*E.e/E.dB
E["evnull_price"]=0.0
ii=E.i.to_numpy()
E["tr"]=BT[ii]<TE; E["t"]=BT[ii]
E["oi6"]=OI6[ii]; E["oi24"]=OI24[ii]; E["crowd6"]=-np.sign(z6[ii])*E.d*np.minimum(np.abs(z6[ii]),9); E["z6"]=z6[ii]; E["z24"]=z24[ii]
E["crowd24"]=-np.sign(z24[ii])*E.d*np.minimum(np.abs(z24[ii]),9)  # >0: crowd positioned AGAINST our direction (compass agrees)
E["taker"]=(TK12[ii]-0.5)*E.d; E["mom1"]=mom1[ii]*E.d; E["dA_atr"]=E.dA/E.atr; E["dB_atr"]=E.dB/E.atr
E.to_pickle("events.pkl"); print(len(E))
