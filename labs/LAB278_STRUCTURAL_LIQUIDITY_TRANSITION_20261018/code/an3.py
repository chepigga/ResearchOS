"""Step 3 + control. Candidate (only one passing step2 rules): W336 lr0.7, crowd6>=+0.5 (crowd positioned AGAINST the move = CrowdFade compass WITH the move).
Control (does the LVN add anything?): same direction & crowd rule, same dA/dB geometry, but at random M5 bars that are NOT LVN crossings
(10 random times per event, within ±30 days, crowd6 condition re-checked at that bar). Trade: continuation, stop A, target B, 48h, 7.5bps."""
import numpy as np,pandas as pd
exec(open("step1.py").read().split("rows=[]\nfor W in")[0])
E=pd.read_pickle("events.pkl")
def fp(ei,d,e,dA,dB):
    A=e-d*dA; B=e+d*dB; end=min(ei+576,N-1)
    hb_=(BH[ei:end]>=B) if d>0 else (BL[ei:end]<=B); ha=(BL[ei:end]<=A) if d>0 else (BH[ei:end]>=A)
    kb=np.argmax(hb_) if hb_.any() else 10**9; ka=np.argmax(ha) if ha.any() else 10**9
    if ka==kb==10**9: return d*(BC[end-1]-e),0,end-1
    if ka<=kb: return -dA,0,ei+ka
    return dB,1,ei+kb
c6=lambda i,d:-np.sign(z6[i])*d*min(abs(z6[i]),9)
rng=np.random.default_rng(278)
res={}
for W,lr in [(336,0.7),(168,0.7),(720,0.7),(336,0.5)]:
    X=E[(E.W==W)&(E.lr==lr)&(E.crowd6>=0.5)]
    ctl=[]
    for r in X.itertuples():
        got=0; tries=0
        while got<10 and tries<200:
            tries+=1; i=int(r.i+rng.integers(-8640,8640))
            if i<300 or i>N-600 or not np.isfinite(z6[i]) or c6(i,r.d)<0.5: continue
            ei=i+1; e=BO[ei]; s=BA[i]/r.atr; pnl,hit,x=fp(ei,r.d,e,r.dA*s,r.dB*s)
            ctl.append(dict(tr=BT[i]<TE,hitB=hit,p0=r.p0,netR=(pnl-COST/1e4*e)/(r.dA*s))); got+=1
    C=pd.DataFrame(ctl)
    for sg,m,mc in (("2021-24",X.tr,C.tr),("2025-26",~X.tr,~C.tr)):
        x=X[m]; y=C[mc]
        print(f"W{W} lr{lr} {sg}: LVN-перехід n={len(x)} edge {(x.hitB-x.p0).mean():+.3f} net {x.netR_cont.mean():+.3f}R | контроль (випадковий час, той самий натовп і геометрія) n={len(y)} edge {(y.hitB-y.p0).mean():+.3f} net {y.netR.mean():+.3f}R")
    res[(W,lr)]=X
# money + overlap with D2 for primary
X=res[(336,0.7)].copy(); X["seg"]=np.where(X.tr,"21","25")
for sg,mo in (("21",48),("25",19.3)):
    x=X[X.seg==sg].sort_values("i"); cum=x.netR_cont.cumsum(); dd=(cum.cummax()-cum).max()
    print(f"{sg}: угод/міс {len(x)/mo:.1f}  EV {x.netR_cont.mean():+.3f}R  R/міс {x.netR_cont.sum()/mo:+.2f}  DD {dd:.1f}R  $ /міс при 0.10% {x.netR_cont.sum()/mo*100:.0f}")
D2=pd.read_csv("/home/claude/lab251/out_oos/LAB273_ALL_TRADES_v006.csv"); print(D2.columns.tolist()[:12])
