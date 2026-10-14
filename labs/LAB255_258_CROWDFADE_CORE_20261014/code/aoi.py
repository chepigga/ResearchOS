import os,io,contextlib,numpy as np,pandas as pd
exec(open("afunnel.py").read().split("rows=[]")[0])   # loads LAB124 module m, b, BZ, BT (cwd=/home/claude/data)
os.chdir("/home/claude/lab251")
h=b.set_index("time").oi4h.resample("1h").last().dropna()
def thr_roll(days,q): x=h.rolling(days*24,min_periods=days*24//2).quantile(q).shift(1); return x.reindex(b.time,method="ffill").to_numpy()
OITH={"фікс. +0.87% (зараз)":np.full(len(b),m.OI70),"ковзний 90 дн q70":thr_roll(90,.7),"ковзний 180 дн q70":thr_roll(180,.7),"ковзний 365 дн q70":thr_roll(365,.7),"без OI-фільтра":np.full(len(b),-9.0)}
def cands(TH):
    out=[]
    for i in range(1,len(b)-600):
        if not(abs(BZ[i])>=1 and abs(BZ[i-1])<1):continue
        side=-1 if BZ[i]>0 else 1; trend=int(b.trend.iloc[i]); ext=float(b.extension.iloc[i]); oi=float(b.oi4h.iloc[i])
        if trend==0 or trend==side: continue
        if not(((side>0 and ext<0) or (side<0 and ext>0)) and abs(ext)>=m.EXT80): continue
        if not np.isfinite(TH[i]) or oi<TH[i]: continue
        ei,ti,br=m.swing3_entry(i,side)
        if ei is None: continue
        if m.phase(int(b.trend_age.iloc[i]),int(b.impulse_age.iloc[i])) not in ("CONT","REACCEL"): continue
        out.append(dict(entry_time=BT.iloc[ei],side=side,atr=float(m.BA[i])))
    return pd.DataFrame(out)
C={k:cands(v) for k,v in OITH.items()}
import pickle; pickle.dump(C,open("a_oi_cands.pkl","wb"))
for k,v in C.items(): print(k,len(v),v.groupby(v.entry_time.dt.year).size().to_dict())
