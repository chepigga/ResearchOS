import os
os.environ["LAB_CACHE"]="/home/claude/lab251/cache_full.pkl"
import numpy as np, pandas as pd
import lab251 as L
BT,BO,BC,BA,N=L.BT,L.BO,L.BC,L.BA,L.N; BZ=np.asarray(L.C["BZ"],float)
c=pd.Series(BC); a=pd.Series(BA)
past6=((c-c.shift(72))/a).to_numpy(); fut24=((c.shift(-288)-c)/a).to_numpy(); fut48=((c.shift(-576)-c)/a).to_numpy()
TE=pd.Timestamp("2025-01-01",tz="UTC"); seg=np.where(BT<TE,"2021-24","2025-26")
m=np.isfinite(fut48)&np.isfinite(past6)&(np.abs(BZ)>=1)&(np.abs(past6)>=0.5)
idx=np.arange(N)[m][::6]
zs=np.sign(BZ[idx]); ms=np.sign(past6[idx]); side=-zs
typ=np.where(zs==-ms,"ECHO: натовп проти руху (купує падіння)","CHASE: натовп за рухом")
D=pd.DataFrame(dict(typ=typ,seg=seg[idx],f24=side*fut24[idx],f48=side*fut48[idx],withmove=(side==ms)))
print(D.groupby(["typ"]).size()/len(D))
print(D.groupby(["typ","seg"]).agg(n=("f24","size"),fut24=("f24","mean"),fut48=("f48","mean")).round(3))
# engines
raw=L.C["raw"][7.5]
e=raw.entry_i.to_numpy(int); s=raw.side.to_numpy(int)
sig_i=e-1
z_e=BZ[sig_i]; p6=past6[sig_i]
raw=raw.assign(z=z_e,past6_side=s*p6,crowd=np.where(np.sign(z_e)==s,"натовп з нами","натовп проти нас"))
raw["move_before"]=np.where(raw.past6_side>0.5,"рух уже в наш бік",np.where(raw.past6_side<-0.5,"рух проти нас","боковик"))
print(raw.groupby(["source","move_before"]).size().unstack(fill_value=0))
print(raw.groupby("source")[["past6_side"]].median().round(2))
