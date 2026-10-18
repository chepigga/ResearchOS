"""LAB282 (pre-registered): Market Profile day shapes P / b / D on BTC (UTC days 2021-2026, 5m volume, 0.05% bins).
Shape (known at day close): pos = (POC-low)/(high-low); up = share of day volume above the range midpoint.
  P: pos>=2/3 and up>=0.6 | b: pos<=1/3 and up<=0.4 | D: 0.35<=pos<=0.65 and 0.4<=up<=0.6 | other.
Next-day outcomes (ATR_D = 14-day mean daily range): r1 = (close_{D+1}-close_D)/ATR_D; range1/ATR_D;
  tail revisit: P -> next day trades into today's lower third; b -> upper third; break: next day trades beyond today's high / low.
Control: same-sized day move. Days bucketed by today's (close-open)/ATR_D quintile x sign; excess = outcome - mean of ALL days in the same bucket.
Both readings tested: P/b continuation (excess r1 in shape direction > 0) vs exhaustion (< 0)."""
import numpy as np,pandas as pd
exec(open("lab280.py").read().split("# ---------- Part 1")[0].replace('print("days",len(DAYS),flush=True)',''))
rows=[]
for d_,(i0,i1) in enumerate(zip(dstart,dend)):
    if i1-i0<280: continue
    k0,P=dprof(i0,i1); prices=np.exp(P5+(k0+np.arange(len(P))+0.5)*S5)
    hi,lo=BH[i0:i1].max(),BL[i0:i1].min(); poc=prices[np.argmax(P)]; mid=(hi+lo)/2
    rows.append(dict(d=d_,t=days[d_],o=BO[i0],c=BC[i1-1],h=hi,l=lo,pos=(poc-lo)/(hi-lo),up=P[prices>mid].sum()/P.sum()))
D=pd.DataFrame(rows).set_index("d")
D["rng"]=D.h-D.l; D["atr"]=D.rng.rolling(14).mean().shift(1)
D["shp"]=np.select([(D.pos>=2/3)&(D.up>=0.6),(D.pos<=1/3)&(D.up<=0.4),(D.pos.between(0.35,0.65))&(D.up.between(0.4,0.6))],["P","b","D"],"інше")
n=D.shift(-1); nxt=D.index+1
D["r1"]=(n.c-D.c)/D.atr; D["rng1"]=n.rng/D.atr
D["tailP"]=(n.l<=D.l+D.rng/3).astype(float); D["tailb"]=(n.h>=D.h-D.rng/3).astype(float)
D["brkH"]=(n.h>D.h).astype(float); D["brkL"]=(n.l<D.l).astype(float); D["brkAny"]=((n.h>D.h)|(n.l<D.l)).astype(float)
D["mv"]=(D.c-D.o)/D.atr
D=D.dropna(subset=["atr","r1"]); D=D[(D.t>="2021-01-15")&(D.t<"2026-08-01")]
D["seg"]=np.where(D.t<"2025-01-01","2021-24","2025-26")
D["bk"]=pd.qcut(D.mv,10,labels=False)
for col in ("r1","rng1","tailP","tailb","brkH","brkL","brkAny"):
    D[col+"_x"]=D[col]-D.groupby("bk")[col].transform("mean")
print("частка форм:",D.shp.value_counts(normalize=True).round(3).to_dict())
print("середній рух дня (ATR) за формою:",D.groupby("shp").mv.mean().round(2).to_dict())
def t(x): return x.mean()/(x.std()/np.sqrt(len(x))) if len(x)>2 else np.nan
out=[]
for (sg,sh),x in D.groupby(["seg","shp"]):
    sgn=1 if sh=="P" else (-1 if sh=="b" else 0)
    r=dict(період=sg,форма=sh,днів=len(x),r1=x.r1.mean())
    if sgn: r.update({"r1 у бік форми, надлишок":(sgn*x.r1_x).mean(),"t":t(sgn*x.r1_x),"повернення у хвіст":(x.tailP if sh=="P" else x.tailb).mean(),"хвіст надлишок":(x.tailP_x if sh=="P" else x.tailb_x).mean(),"t хвіст":t(x.tailP_x if sh=="P" else x.tailb_x)})
    r.update({"діапазон завтра":x.rng1.mean(),"діап. надлишок":x.rng1_x.mean(),"t діап":t(x.rng1_x),"пробій краю":x.brkAny.mean(),"пробій надлишок":x.brkAny_x.mean(),"t проб":t(x.brkAny_x)})
    out.append(r)
pd.set_option("display.width",300); print(pd.DataFrame(out).round(3).to_string(index=False))
D.to_pickle("lab282_days.pkl")
