import os
os.environ["LAB_CACHE"]="/home/claude/lab251/cache_full.pkl"
import numpy as np, pandas as pd
import lab251 as L
BT,BC,BA,N=L.BT,L.BC,L.BA,L.N
r=pd.Series(np.load("ratio.npy"),index=BT)
TE=pd.Timestamp("2025-01-01",tz="UTC"); seg=np.where(BT<TE,"2021-24","2025-26")
c=pd.Series(BC); a=pd.Series(BA); f24=((c.shift(-288)-c)/a).to_numpy()
def zroll(w):
    m=r.rolling(w,min_periods=w).mean(); s=r.rolling(w,min_periods=w).std(ddof=0); return ((r-m)/s).to_numpy()
def zday():
    g=r.groupby(BT.floor("D")); m=g.transform(lambda x:x.expanding(24).mean()); s=g.transform(lambda x:x.expanding(24).std(ddof=0))
    return ((r-m)/s).to_numpy()
Z={"6 год (поточне)":zroll(72),"12 год":zroll(144),"24 год":zroll(288),"3 дні":zroll(864),"30 днів":zroll(8640),"від 00:00 UTC":zday()}
z6=Z["6 год (поточне)"]
# waves >=3 ATR
df=pd.DataFrame({"c":BC,"a":BA},index=BT); hh=df.resample("1h").agg({"c":"last","a":"last"}).dropna()
C=hh.c.to_numpy(); A=hh.a.to_numpy(); T=hh.index
piv=[0]; d=0; ei=0
for i in range(1,len(C)):
    if d>=0:
        if C[i]>C[ei]: ei=i
        elif C[ei]-C[i]>=3*A[ei]: piv.append(ei); d=-1; ei=i; continue
    if d<=0:
        if C[i]<C[ei]: ei=i
        elif C[i]-C[ei]>=3*A[ei]: piv.append(ei); d=1; ei=i
piv.append(ei)
W=[(a_,b_,int(np.sign(C[b_]-C[a_]))) for a_,b_ in zip(piv[:-1],piv[1:]) if b_>a_ and abs(C[b_]-C[a_])>=3*A[a_]]
pos=lambda t:int(np.searchsorted(BT.values,np.datetime64(t.tz_convert("UTC").tz_localize(None))))
WI=[(pos(T[a_]),pos(T[b_]),d_,"2021-24" if T[a_]<TE else "2025-26") for a_,b_,d_ in W]
MO={"2021-24":48,"2025-26":19.3}
rows=[]
if __name__=="__main__":
  pass
for name,z in (Z.items() if __name__=="__main__" else []):
    az=np.abs(z)
    print(name,"corr з z 6 год:",round(pd.Series(z).corr(pd.Series(z6)),2))
    for Tz in [1.0,2.0]:
        F=np.where((az>=Tz)&(np.r_[0,az[:-1]]<Tz)&np.isfinite(z))[0]
        for sg in ["2021-24","2025-26"]:
            lvl=np.where((az>=Tz)&(seg==sg)&np.isfinite(f24))[0][::6]
            drift=np.nanmean(-np.sign(z[lvl])*f24[lvl])
            Fs=F[seg[F]==sg]
            al=early=first=sw=sa=0; nw=0
            for i0,i1,d_,s_ in WI:
                if s_!=sg: continue
                nw+=1; third=i0+(i1-i0)//3
                f=F[(F>=i0)&(F<i1)]; sd=-np.sign(z[f])
                early+= ((f[sd==d_])<=third).any(); first+= (len(f)>0 and sd[0]==d_)
                sw+=(sd==d_).sum(); sa+=(sd==-d_).sum()
            rows.append(dict(window=name,T=Tz,seg=sg,signals_mo=len(Fs)/MO[sg],drift24=drift,
                in_first_third=early/nw,first_right=first/nw,precision=sw/max(sw+sa,1)))
if __name__=="__main__":
  R=pd.DataFrame(rows); pd.set_option("display.width",250)
  for Tz in [1.0,2.0]:
      print(f"\n===== поріг |z|>={Tz}")
      print(R[R["T"]==Tz].pivot_table(index="window",columns="seg",values=["signals_mo","drift24","in_first_third","first_right","precision"],sort=False).round(2).to_string())
  R.to_csv("out_oos/ZWINDOWS.csv",index=False)
  