"""LAB280 (pre-registered).
Part 1 — Dalton 80% rule on the UTC-day profile (0.05% bins, 5m volume spread over bar range; VA = 70% by expansion from POC).
  Event (day D): price outside previous-day VA [VAL,VAH] (OPEN: day opens outside | ANY: any time outside during day), then K=2 (also 1)
  consecutive M30 closes inside VA -> entry next M5 open toward the opposite VA edge. Stop: extreme of the excursion outside VA ±0.1 ATR,
  clamped [0.3,3] ATR. Target: opposite edge. Exit: end of UTC day D (also 24h variant). First event per day.
  Report: classic 'reached opposite edge' rate; first passage target vs stop vs random-walk null dS/(dS+dT); net R after 7.5 bps.
  Extra (one pre-registered check): crowd z6 against the trade direction (>=0.5).
Part 2 — naked POC: POC of a past day (<=30 days old) never traded at since that day ended. At each H1 close nearest nPOC at 0.5–4 ATR:
  P(touch in 24h) vs mirror level at same distance. Also all prior-day POC (not naked) as reference.
Part 3 — anchored (fixed-range) profile from the latest confirmed H4 swing (pivot p=2, >=24h old) to now, recomputed each H1:
  (a) POC mirror test, (b) LVN transitions HVN->LVN->HVN exactly as LAB278 step1 (prominence 5%, lr 0.7, smoothing 1.5) vs null."""
import numpy as np,pandas as pd
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks
import vp
c=pd.read_pickle("/home/claude/lab251/cache_full.pkl")
BT=pd.DatetimeIndex(c["BT"]); BO,BH,BL,BC,BA=[c[k] for k in ("BO","BH","BL","BC","BA")]; N=len(BT); TE=pd.Timestamp("2025-01-01",tz="UTC"); COST=7.5
v=pd.read_pickle("/home/claude/lab251/v5m.pkl").reindex(BT)
VOL=v.volume.fillna(0).to_numpy()
r=pd.Series(np.load("/home/claude/lab251/ratio.npy"),index=BT); z6=((r-r.rolling(72).mean())/r.rolling(72).std(ddof=0)).to_numpy()
day=BT.floor("1D"); days=day.unique(); dstart=np.searchsorted(BT.values,days.values); dend=np.r_[dstart[1:],N]
S5=0.0005; P5=np.log(8000)
def dprof(i0,i1):
    lo=np.floor((np.log(BL[i0:i1])-P5)/S5).astype(int); hi=np.floor((np.log(BH[i0:i1])-P5)/S5).astype(int)
    k0=lo.min(); n=hi.max()-k0+2; D=np.zeros(n+1); w=VOL[i0:i1]/(hi-lo+1)
    np.add.at(D,lo-k0,w); np.add.at(D,hi-k0+1,-w); P=np.cumsum(D)[:n]; return k0,P
def va(k0,P):
    poc=int(np.argmax(P)); tot=P.sum(); lo=hi=poc; acc=P[poc]
    while acc<0.7*tot:
        up=P[hi+1] if hi+1<len(P) else -1; dn=P[lo-1] if lo-1>=0 else -1
        if up>=dn: hi+=1; acc+=up
        else: lo-=1; acc+=dn
    px=lambda k:np.exp(P5+(k0+k+0.5)*S5)
    return px(lo)-0.5*np.exp(P5+(k0+lo)*S5)*S5*0, px(hi), px(poc)   # VAL,VAH,POC (bin centers)
DAYS=[]
for d_,(i0,i1) in enumerate(zip(dstart,dend)):
    if i1-i0<200: DAYS.append(None); continue
    k0,P=dprof(i0,i1); DAYS.append(va(k0,P))
print("days",len(DAYS),flush=True)
# ---------- Part 1
m30end=np.asarray((BT+pd.Timedelta("5min")).minute%30==0)
rows=[]
for mode in ("OPEN","ANY"):
    for K in (1,2):
        for horizon in ("DAY","24H"):
            for d_ in range(1,len(days)):
                if DAYS[d_-1] is None: continue
                VAL,VAH,POC=DAYS[d_-1]; i0,i1=dstart[d_],dend[d_]
                if i1-i0<200 or i0<300 or i1>N-300: continue
                op=BO[i0]; side0=1 if op>VAH else (-1 if op<VAL else 0)
                if mode=="OPEN" and side0==0: continue
                out=0; ext=None; cnt=0; ev=None
                for i in range(i0,i1-1):
                    s=1 if BC[i]>VAH else (-1 if BC[i]<VAL else 0)
                    if s!=0:
                        if mode=="OPEN" and s!=side0: break     # went to the other side first: not the classic setup
                        out=s; ext=max(ext,BH[i]) if (ext is not None and s>0) else (BH[i] if s>0 else (min(ext,BL[i]) if ext is not None else BL[i]))
                        cnt=0; continue
                    if out==0: continue
                    if m30end[i]:
                        cnt+=1
                        if cnt>=K: ev=i; break
                if ev is None: continue
                sd=-out; ei=ev+1; e=BO[ei]; a=BA[ev]; T_=VAL if sd<0 else VAH
                stp=ext+0.1*a if sd<0 else ext-0.1*a
                dS=sd*(e-stp); dS=min(max(dS,0.3*a),3*a); stp=e-sd*dS; dT=sd*(T_-e)
                if dT<=0.1*a: continue
                end=i1 if horizon=="DAY" else min(ei+288,N-1)
                hT=(BL[ei:end]<=T_) if sd<0 else (BH[ei:end]>=T_); hS=(BH[ei:end]>=stp) if sd<0 else (BL[ei:end]<=stp)
                kt=np.argmax(hT) if hT.any() else 10**9; ks=np.argmax(hS) if hS.any() else 10**9
                if kt==ks==10**9: res="TO"; pnl=sd*(BC[end-1]-e)
                elif ks<=kt: res="S"; pnl=-dS
                else: res="T"; pnl=dT
                rows.append(dict(mode=mode,K=K,hor=horizon,i=ev,tr=BT[ev]<TE,sd=sd,reach=bool(hT.any()),res=res,p0=dS/(dS+dT),
                                 netR=(pnl-COST/1e4*e)/dS,dS=dS/a,dT=dT/a,crowd=-np.sign(z6[ev])*sd*min(abs(z6[ev]),9)))
P1=pd.DataFrame(rows); P1.to_pickle("p1.pkl")
def summ1(x,mo): return dict(n_mo=len(x)/mo,reach=x.reach.mean(),T=(x.res=="T").mean(),null=x.p0.mean(),edge=(x.res=="T").mean()-x.p0.mean(),
                             se=((x.res=="T")-x.p0).std()/np.sqrt(len(x)),netR=x.netR.mean(),dS=x.dS.median(),dT=x.dT.median())
o=[]
for (mode,K,hor),x in P1.groupby(["mode","K","hor"]):
    for sg,m,mo in (("2021-24",x.tr,48),("2025-26",~x.tr,19.3)):
        o.append(dict(mode=mode,K=K,hor=hor,seg=sg,**summ1(x[m],mo)))
        y=x[m&(x.crowd>=0.5)]; o.append(dict(mode=mode,K=K,hor=hor,seg=sg+" натовп проти",**summ1(y,mo)))
pd.set_option("display.width",260)
print("\n== Part 1: правило 80% (денна VA)"); print(pd.DataFrame(o).round(3).to_string(index=False))
# ---------- Part 2 & 3 hourly
hours=pd.date_range(BT[0].ceil("1h"),BT[-1].floor("1h"),freq="1h")
hc=np.searchsorted(BT.values,hours.values)-1     # last M5 bar before hour start = bar closing at hour boundary
dayidx=np.searchsorted(days.values,BT.floor("1D").values)
# naked POC tracking: for each day d, POC; first index after day end where price trades through POC
pocs=np.array([x[2] if x is not None else np.nan for x in DAYS]); touched=np.full(len(days),N)
for d_ in range(len(days)):
    if not np.isfinite(pocs[d_]): continue
    i0=dend[d_]; L=pocs[d_]
    hit=np.nonzero((BL[i0:]<=L)&(BH[i0:]>=L))[0]
    if len(hit): touched[d_]=i0+hit[0]
r2=[]
for i in hc[(hc>300)&(hc<N-300)]:
    a=BA[i]; p=BC[i]; dd=dayidx[i]
    cand=[(dd-k) for k in range(1,31) if dd-k>=0 and np.isfinite(pocs[dd-k])]
    hi,lo=BH[i+1:i+289].max(),BL[i+1:i+289].min()
    for typ,ks in (("naked POC",[k for k in cand if touched[k]>i]),("POC вчора",[dd-1] if dd-1 in cand else [])):
        if not ks: continue
        Ls=pocs[ks]; dist=np.abs(Ls-p)/a; ok=(dist>=0.5)&(dist<=4)
        if not ok.any(): continue
        L=Ls[ok][np.argmin(dist[ok])]; M_=2*p-L
        hL=(hi>=L) if L>p else (lo<=L); hM=(hi>=M_) if M_>p else (lo<=M_)
        r2.append(dict(typ=typ,d=abs(L-p)/a,hitL=hL,hitM=hM,tr=BT[i]<TE))
P2=pd.DataFrame(r2); P2["db"]=pd.cut(P2.d,[0.5,1,2,4],labels=["0.5-1 ATR","1-2","2-4"])
T2=P2.groupby(["typ","db","tr"],observed=True).agg(n=("hitL","size"),рівень=("hitL","mean"),дзеркало=("hitM","mean")); T2["різниця"]=T2.рівень-T2.дзеркало
print("\n== Part 2: naked POC — дотик за 24 год проти дзеркального рівня (tr=True → 2021-24)"); print(T2.round(3).to_string())
# Part 3 anchored
vh=v.copy(); vh["low"]=BL; vh["high"]=BH
H1h=pd.Series(BH,index=BT).resample("1h").max(); H1l=pd.Series(BL,index=BT).resample("1h").min()
hoursM=H1h.index
M=vp.hourly_from_bars(BT,BL,BH,VOL,hoursM).astype(np.float64); CUM=np.vstack([np.zeros(vp.NB),np.cumsum(M,0)]); del M
h4=pd.DataFrame({"h":pd.Series(BH,index=BT).resample("4h").max(),"l":pd.Series(BL,index=BT).resample("4h").min()}).dropna()
H4h,H4l=h4.h.to_numpy(),h4.l.to_numpy(); piv=np.full(len(h4),-1)   # at close of 4h bar k: start time (hour index) of latest confirmed pivot
last=-1
for k in range(4,len(h4)):
    j=k-2
    if H4h[j]==H4h[j-2:j+3].max() or H4l[j]==H4l[j-2:j+3].min(): last=j
    piv[k]=last
h4close=h4.index+pd.Timedelta("4h"); h4hour=np.searchsorted(hoursM.values,h4.index.values)
hcM=np.searchsorted(BT.values,(hoursM+pd.Timedelta("1h")).values)-1
r3=[]; ev3=[]
k4=0
for h in range(200,len(hoursM)-1):
    tclose=hoursM[h]+pd.Timedelta("1h")
    while k4+1<len(h4) and h4close[k4+1]<=tclose: k4+=1
    pj=piv[k4]
    if pj<0: continue
    ah=h4hour[pj]
    if h-ah<24: continue
    i=hcM[h]
    if i<300 or i>N-600: continue
    P=CUM[h+1]-CUM[ah]; s=gaussian_filter1d(P,1.5); mx=s.max()
    if mx<=0: continue
    a=BA[i]; p=BC[i]
    poc=vp.bprice(int(np.argmax(s))); d=abs(poc-p)/a
    hi,lo=BH[i+1:i+289].max(),BL[i+1:i+289].min()
    if 0.5<=d<=4:
        M_=2*p-poc; r3.append(dict(d=d,hitL=(hi>=poc) if poc>p else (lo<=poc),hitM=(hi>=M_) if M_>p else (lo<=M_),tr=BT[i]<TE))
    pk,_=find_peaks(s,prominence=0.05*mx)
    for a_,c_ in zip(pk[:-1],pk[1:]):
        m=a_+int(np.argmin(s[a_:c_+1]))
        if s[m]>0.7*min(s[a_],s[c_]): continue
        pl,pm,ph=vp.bprice(a_),vp.bprice(m),vp.bprice(c_)
        for j in range(i+1,min(i+13,N-600)):
            for dr in (1,-1):
                A,B=(pl,ph) if dr>0 else (ph,pl)
                if not ((BC[j-1]<pm<=BC[j]) if dr>0 else (BC[j-1]>pm>=BC[j])): continue
                came=(BL[max(j-144,0):j].min()<=A*(1+vp.STEP)) if dr>0 else (BH[max(j-144,0):j].max()>=A*(1-vp.STEP))
                if not came: continue
                ei=j+1; e=BO[ei]; dA=dr*(e-A); dB=dr*(B-e)
                if dA<0.3*BA[j] or dB<0.3*BA[j]: continue
                ev3.append(dict(i=j,ei=ei,d=dr,m=m,A=A,B=B,e=e,dA=dA,dB=dB,crowd=-np.sign(z6[j])*dr*min(abs(z6[j]),9)))
P3=pd.DataFrame(r3); P3["db"]=pd.cut(P3.d,[0.5,1,2,4],labels=["0.5-1 ATR","1-2","2-4"])
T3=P3.groupby(["db","tr"],observed=True).agg(n=("hitL","size"),POC=("hitL","mean"),дзеркало=("hitM","mean")); T3["різниця"]=T3.POC-T3.дзеркало
print("\n== Part 3a: POC профілю від свінгу H4 — дотик за 24 год проти дзеркала"); print(T3.round(3).to_string())
E=pd.DataFrame(ev3).sort_values("i"); keep=[]; lastk={}
for rr in E.itertuples():
    L=lastk.setdefault(rr.d,[]); L[:]=[(ii,bb) for ii,bb in L if rr.i-ii<288]
    if any(abs(bb-rr.m)<=2 for ii,bb in L): keep.append(False); continue
    L.append((rr.i,rr.m)); keep.append(True)
E=E[np.array(keep)].reset_index(drop=True); out=[]
for rr in E.itertuples():
    ei,d,A,B=rr.ei,rr.d,rr.A,rr.B; end=min(ei+576,N-1)
    hb_=(BH[ei:end]>=B) if d>0 else (BL[ei:end]<=B); ha=(BL[ei:end]<=A) if d>0 else (BH[ei:end]>=A)
    kb=np.argmax(hb_) if hb_.any() else 10**9; ka=np.argmax(ha) if ha.any() else 10**9
    if ka==kb==10**9: pnl=d*(BC[end-1]-rr.e); hit=0
    elif ka<=kb: pnl=-rr.dA; hit=0
    else: pnl=rr.dB; hit=1
    out.append(dict(hitB=hit,netR=(pnl-COST/1e4*rr.e)/rr.dA))
E=pd.concat([E,pd.DataFrame(out)],axis=1); E["p0"]=E.dA/(E.dA+E.dB); E["tr"]=BT[E.i.to_numpy()]<TE
print("\n== Part 3b: переходи HVN→LVN→HVN на профілі від свінгу")
for nm,m in (("усі",E.crowd>-99),("натовп проти руху ≥0.5",E.crowd>=0.5)):
    for sg,mm,mo in (("2021-24",E.tr,48),("2025-26",~E.tr,19.3)):
        x=E[m&mm]; dl=x.hitB-x.p0
        print(f"{nm:24s} {sg}: n/міс {len(x)/mo:.1f}  до B {x.hitB.mean():.3f}  нуль {x.p0.mean():.3f}  відхилення {dl.mean():+.3f} (z {dl.mean()/(dl.std()/np.sqrt(len(x))):.1f})  net {x.netR.mean():+.3f}R")
E.to_pickle("p3b.pkl")
