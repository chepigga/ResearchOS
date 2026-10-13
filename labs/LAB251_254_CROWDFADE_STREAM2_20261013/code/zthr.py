import os
os.environ["LAB_CACHE"]="/home/claude/lab251/cache_full.pkl"
import numpy as np, pandas as pd
import lab251 as L
from run_exec import sim
BT,BC,BA,N=L.BT,L.BC,L.BA,L.N; BZ=np.asarray(L.C["BZ"],float)
TE=pd.Timestamp("2025-01-01",tz="UTC"); seg=np.where(BT<TE,"TRAIN","OOS"); MO={"TRAIN":48,"OOS":19}
c=pd.Series(BC); a=pd.Series(BA)
f24=((c.shift(-288)-c)/a).to_numpy(); f48=((c.shift(-576)-c)/a).to_numpy()
az=np.abs(BZ)
def events(T, mode):
    """episode = |z|>=T until |z|<1 (re-arm). mode FRESH: signal at first bar >=T.
       UNWIND: after reaching >=T, signal at first bar where |z| <= peak-0.5 while still same sign (crowd starts exiting), within 72 bars."""
    out=[]; i=1
    while i<N-600:
        if az[i]>=T and az[i-1]<T and np.isfinite(BZ[i]):
            sg=np.sign(BZ[i]); j=i; pk=az[i]; sig=None
            if mode=="FRESH": sig=i
            else:
                while j<min(i+72,N-600):
                    if np.sign(BZ[j])!=sg: break
                    pk=max(pk,az[j])
                    if az[j]<=pk-0.5: sig=j; break
                    j+=1
            if sig is not None and BA[sig+1]>0:
                out.append(dict(source="Z",entry_time=BT[sig+1],entry_i=sig+1,side=int(-sg),atr=float(BA[sig+1]),pri=0,sig_i=sig))
            # re-arm only after |z|<1
            k=i
            while k<N-600 and az[k]>=1 and np.sign(BZ[k])==sg: k+=1
            i=max(k,i+1)
        else: i+=1
    return pd.DataFrame(out)
if __name__=="__main__":
    rows=[]
    for mode in ["FRESH","UNWIND"]:
        for T in [1.0,1.5,2.0,2.05,2.25,2.5,3.0]:
            ev=events(T,mode)
            if ev.empty: continue
            for sg in ["TRAIN","OOS"]:
                e=ev[(ev.entry_time<TE) if sg=="TRAIN" else (ev.entry_time>=TE)].reset_index(drop=True)
                si=e.sig_i.to_numpy(int); sd=e.side.to_numpy()
                d24=np.nanmean(sd*f24[si]); d48=np.nanmean(sd*f48[si])
                t,eq=sim(e,1.0,72,3.0,half_lock=True)
                if t.empty: continue
                dd=float(np.max(np.maximum.accumulate(eq)-eq))
                rows.append(dict(mode=mode,T=T,seg=sg,signals_mo=len(e)/MO[sg],trades_mo=len(t)/MO[sg],drift24=d24,drift48=d48,
                                 ev=t.net_r.mean(),r_mo=t.net_r.sum()/MO[sg],dd=dd,r_dd=t.net_r.sum()/dd if dd>0 else np.nan))
    R=pd.DataFrame(rows)
    pd.set_option("display.width",250)
    for mode in ["FRESH","UNWIND"]:
        print("=====",mode)
        print(R[R["mode"]==mode].pivot_table(index="T",columns="seg",values=["signals_mo","drift24","ev","r_mo","dd","r_dd"]).round(2).to_string())
    R.to_csv("out_oos/ZTHRESH.csv",index=False)
