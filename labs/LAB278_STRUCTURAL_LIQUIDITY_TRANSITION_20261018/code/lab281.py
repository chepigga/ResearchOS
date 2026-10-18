"""LAB281 (pre-registered): 'level-to-level' Volume Profile method from the video, formalized literally, BTCUSDT M5 2021-2026.
Profile ('visible range'): last W M5 bars incl. current (W=288 = 24h main; 576 = 48h variant), 0.05% log bins, 5m volume spread over [low,high],
  Gaussian smoothing 2 bins. HVN = peaks with prominence >= 10% of max; LVN = minimum between adjacent HVNs <= 0.6 x smaller HVN.
Trigger (short; long mirrored): M5 close crosses an LVN downward, the upper HVN (A) was touched (±0.1%) in the last 36 bars (price leaves HVN),
  lower HVN (B) = target. Entry next M5 open. Stop = A + 0.1 ATR_H1 ('just above the upper HVN'). Target = B. Time exit 24h.
  Require stop distance >= 0.3 ATR_H1 and target distance >= 0.3 ATR_H1. Dedup: same direction & LVN within 0.15% once per 6h.
Filters (video): STRUCT = last two confirmed M5 pivot highs AND lows descending (p=3) | TREND = EMA20<EMA50 on last closed M30 AND H1 |
  MOM = crossing bar bearish with body >= 60% of range AND close fell >= 0.3 ATR_H1 over last 6 bars.
Variants: P (profile only), P+S, P+T, P+M, FULL = P+S+T+M (the video), FULL_48h.
Controls: random-walk null p0 = dStop/(dStop+dTarget); CTRL = bars where S+T+M are true but NOT an LVN crossing, with stop/target distances
  copied from a random FULL event (does the profile timing add anything over the trend filters?).
Cost 7.5 bps round trip. Select nothing; report 2021-24 and 2025-26."""
import numpy as np,pandas as pd
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks
c=pd.read_pickle("/home/claude/lab251/cache_full.pkl")
BT=pd.DatetimeIndex(c["BT"]); BO,BH,BL,BC,BA=[c[k] for k in ("BO","BH","BL","BC","BA")]; N=len(BT); TE=pd.Timestamp("2025-01-01",tz="UTC"); COST=7.5
VOL=pd.read_pickle("/home/claude/lab251/v5m.pkl").volume.reindex(BT).fillna(0).to_numpy()
S=0.0005; P0=np.log(8000); NBN=int(np.log(250000/8000)/S)+5
bl=np.floor((np.log(BL)-P0)/S).astype(int); bh=np.floor((np.log(BH)-P0)/S).astype(int)
px=lambda k:np.exp(P0+(k+0.5)*S)
# filters
s=pd.Series(BC,index=BT)
def emaside(tf):
    x=s.resample(tf).last().dropna(); d=np.sign(x.ewm(span=20,adjust=False).mean()-x.ewm(span=50,adjust=False).mean())
    d.index=d.index+pd.Timedelta(tf); return d.reindex(BT,method="ffill").fillna(0).to_numpy()
TREND=np.where((emaside("30min")==emaside("1h")),emaside("1h"),0)
p=3; ph=[];pl=[]; ST=np.zeros(N,int); lh=[np.nan,np.nan]; ll=[np.nan,np.nan]
for i in range(2*p+1,N):
    j=i-p
    if BH[j]==BH[j-p:j+p+1].max(): lh=[lh[1],BH[j]]
    if BL[j]==BL[j-p:j+p+1].min(): ll=[ll[1],BL[j]]
    if lh[1]<lh[0] and ll[1]<ll[0]: ST[i]=-1
    elif lh[1]>lh[0] and ll[1]>ll[0]: ST[i]=1
rng_=BH-BL; body=BC-BO
c6=np.r_[np.full(6,np.nan),BC[6:]-BC[:-6]]/BA
MOMd=np.where((body<0)&(np.abs(body)>=0.6*rng_)&(c6<=-0.3),-1,np.where((body>0)&(np.abs(body)>=0.6*rng_)&(c6>=0.3),1,0))
HI36=pd.Series(BH).rolling(36,min_periods=1).max().shift(1).to_numpy(); LO36=pd.Series(BL).rolling(36,min_periods=1).min().shift(1).to_numpy()
ev=[]
for W in (288,576):
    prof=np.zeros(NBN)
    def add(i,sg):
        a,b=bl[i],bh[i]; prof[a:b+1]+=sg*VOL[i]/(b-a+1)
    for i in range(W): add(i,1)
    last={}
    for i in range(W,N-300):
        add(i,1); add(i-W,-1)
        k=int((np.log(BC[i])-P0)/S); lo=max(k-200,0); sl=prof[lo:k+201]
        if i%1==0:
            sm=gaussian_filter1d(sl,2.0); mx=sm.max()
            if mx<=0: continue
            pk,_=find_peaks(sm,prominence=0.1*mx)
            if len(pk)<2: continue
            for a_,c_ in zip(pk[:-1],pk[1:]):
                m=a_+int(np.argmin(sm[a_:c_+1]))
                if sm[m]>0.6*min(sm[a_],sm[c_]): continue
                L=px(lo+m); lowH=px(lo+a_); upH=px(lo+c_)
                for d in (-1,1):
                    if d<0:
                        if not (BC[i-1]>L>=BC[i]): continue
                        A,B=upH,lowH
                        if HI36[i]<A*(1-0.001): continue
                    else:
                        if not (BC[i-1]<L<=BC[i]): continue
                        A,B=lowH,upH
                        if LO36[i]>A*(1+0.001): continue
                    key=(W,d); Ls=last.setdefault(key,[]); Ls[:]=[(ii,ll_) for ii,ll_ in Ls if i-ii<72]
                    if any(abs(ll_/L-1)<0.0015 for ii,ll_ in Ls): continue
                    Ls.append((i,L))
                    a=BA[i]; e=BO[i+1]; stp=A-d*0.1*a; dS=d*(e-stp); dT=d*(B-e)
                    if dS<0.3*a or dT<0.3*a: continue
                    ev.append(dict(W=W,i=i,d=d,e=e,dS=dS,dT=dT,fS=ST[i]==d,fT=TREND[i]==d,fM=MOMd[i]==d))
    print("W",W,len(ev),flush=True)
E=pd.DataFrame(ev)
def walk(i,d,e,dS,dT):
    ei=i+1; end=min(ei+288,N-1); stp=e-d*dS; tg=e+d*dT
    ht=(BH[ei:end]>=tg) if d>0 else (BL[ei:end]<=tg); hs=(BL[ei:end]<=stp) if d>0 else (BH[ei:end]>=stp)
    kt=np.argmax(ht) if ht.any() else 10**9; ks=np.argmax(hs) if hs.any() else 10**9
    if kt==ks==10**9: return d*(BC[end-1]-e),0
    if ks<=kt: return -dS,0
    return dT,1
R=[walk(r.i,r.d,r.e,r.dS,r.dT) for r in E.itertuples()]
E["pnl"]=[x[0] for x in R]; E["hit"]=[x[1] for x in R]; E["p0"]=E.dS/(E.dS+E.dT); E["netR"]=(E.pnl-COST/1e4*E.e)/E.dS; E["tr"]=BT[E.i.to_numpy()]<TE
E["costR"]=COST/1e4*E.e/E.dS
E.to_pickle("lab281_ev.pkl")
# control: S+T+M bars without LVN crossing
rng=np.random.default_rng(281)
full=E[(E.W==288)&E.fS&E.fT&E.fM]
cand=np.nonzero((ST==TREND)&(TREND==MOMd)&(TREND!=0))[0]; cand=cand[(cand>600)&(cand<N-300)]
evset=set(E[E.W==288].i)
cand=np.array([x for x in cand if x not in evset])
ctl=[]
for i in rng.choice(cand,size=min(20000,len(cand)),replace=False):
    rr=full.iloc[rng.integers(len(full))]; d=TREND[i]; a=BA[i]; s_=a/BA[int(rr.i)]
    e=BO[i+1]; pnl,hit=walk(i,d,e,rr.dS*s_,rr.dT*s_)
    ctl.append(dict(tr=BT[i]<TE,hit=hit,p0=rr.dS/(rr.dS+rr.dT),netR=(pnl-COST/1e4*e)/(rr.dS*s_)))
C=pd.DataFrame(ctl)
V={"P (лише профіль)":(E.W==288),"P+структура":(E.W==288)&E.fS,"P+тренд M30/H1":(E.W==288)&E.fT,"P+моментум":(E.W==288)&E.fM,
   "ПОВНИЙ (як у відео)":(E.W==288)&E.fS&E.fT&E.fM,"ПОВНИЙ, профіль 48 год":(E.W==576)&E.fS&E.fT&E.fM}
rows=[]
for nm,m in V.items():
    for sg,mm,mo in (("2021-24",E.tr,48),("2025-26",~E.tr,19.3)):
        x=E[m&mm]; dl=x.hit-x.p0
        rows.append(dict(варіант=nm,період=sg,угод_міс=len(x)/mo,ціль=x.hit.mean(),нуль=x.p0.mean(),відхил=dl.mean(),z=dl.mean()/(dl.std()/np.sqrt(len(x))),
                         стоп_ATR=(x.dS/BA[x.i.to_numpy()]).median(),витрати_R=x.costR.mean(),netR=x.netR.mean()))
for sg,mm,mo in (("2021-24",C.tr,None),("2025-26",~C.tr,None)):
    x=C[mm]; dl=x.hit-x.p0
    rows.append(dict(варіант="КОНТРОЛЬ: ті самі фільтри без профілю",період=sg,угод_міс=np.nan,ціль=x.hit.mean(),нуль=x.p0.mean(),відхил=dl.mean(),z=dl.mean()/(dl.std()/np.sqrt(len(x))),netR=x.netR.mean()))
O=pd.DataFrame(rows); O.to_csv("lab281.csv",index=False); pd.set_option("display.width",250); print(O.round(3).to_string(index=False))
