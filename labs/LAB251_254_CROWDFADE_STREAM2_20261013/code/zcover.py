import os
os.environ["LAB_CACHE"]="/home/claude/lab251/cache_full.pkl"
import numpy as np, pandas as pd
import lab251 as L
BT,BO,BH,BL,BC,BA,N=L.BT,L.BO,L.BH,L.BL,L.BC,L.BA,L.N; BZ=np.asarray(L.C["BZ"],float); az=np.abs(BZ)
TE=pd.Timestamp("2025-01-01",tz="UTC")
W=pd.read_csv("out_oos/WAVES.csv",parse_dates=["t0","t1"])
pos=lambda t: int(np.searchsorted(BT.values,np.datetime64(pd.Timestamp(t).tz_convert("UTC").tz_localize(None)),side="left"))
# 1) coverage of price movement by z-state (fade side) at M5 resolution, weighted by bar move in wave direction
state=np.where(az>=1,-np.sign(BZ),0)
mv=np.r_[0,np.diff(BC)]
agg={"за рухом":0.0,"проти руху":0.0,"нейтрально":0.0}; tot=0.0
segagg={}
for w in W.itertuples():
    i0,i1=pos(w.t0),pos(w.t1); d=w.dir
    m=d*mv[i0+1:i1+1]/BA[i0+1:i1+1]; s=state[i0:i1]   # state known at previous bar close
    sg="2021-24" if w.t0<TE else "2025-26"
    for k,msk in [("за рухом",s==d),("проти руху",s==-d),("нейтрально",s==0)]:
        segagg.setdefault(sg,{}).setdefault(k,0.0); segagg[sg][k]+=m[msk].sum()
        segagg[sg].setdefault(k+"_time",0); segagg[sg][k+"_time"]+=msk.sum()
for sg,v in segagg.items():
    T=sum(v[k] for k in ["за рухом","проти руху","нейтрально"]); TT=sum(v[k+"_time"] for k in ["за рухом","проти руху","нейтрально"])
    print(sg,"частка руху (ATR) коли z-стан:",{k:f"{v[k]/T:.0%}" for k in ["за рухом","проти руху","нейтрально"]},
          "| частка часу:",{k:f"{v[k+'_time']/TT:.0%}" for k in ["за рухом","проти руху","нейтрально"]})
# 2) per wave: fresh-crossing signals of |z|>=T
def fresh(T): return np.where((az>=T)&(np.r_[0,az[:-1]]<T))[0]
rows=[]
for T in [1.0,2.0,3.0]:
    F=fresh(T)
    for w in W.itertuples():
        i0,i1=pos(w.t0),pos(w.t1); d=w.dir
        inw=F[(F>=i0)&(F<i1-1)]
        sides=-np.sign(BZ[inw]); al=inw[sides==d]; op=inw[sides==-d]
        r=dict(T=T,seg="2021-24" if w.t0<TE else "2025-26",size=w.size_atr,n_align=len(al),n_opp=len(op))
        if len(al):
            s=al[0]; e=s+1; a=BA[e]; ent=BO[e]
            r["done_frac"]=d*(ent-w.p0)/(w.p1-w.p0)*d if w.p1!=w.p0 else np.nan
            r["done_frac"]=(ent-w.p0)/(w.p1-w.p0)
            r["remain_atr"]=d*(w.p1-ent)/a
            path_adv=(ent-BL[e:i1+1]).max()/a if d>0 else (BH[e:i1+1]-ent).max()/a
            # MAE before the wave reaches its end: adverse excursion until price makes new extreme in wave dir beyond entry+2ATR?
            fav=((BH[e:i1+1]-ent) if d>0 else (ent-BL[e:i1+1]))/a
            adv=((ent-BL[e:i1+1]) if d>0 else (BH[e:i1+1]-ent))/a
            hit2=np.argmax(fav>=2) if (fav>=2).any() else len(fav)
            r["mae_before_2R"]=adv[:hit2+1].max()
            r["hours_to_end"]=(i1-e)/12
        rows.append(r)
D=pd.DataFrame(rows)
def cat(r):
    if r.n_align==0: return "1 нема сигналу в бік руху"
    if r.done_frac>0.66: return "2 сигнал запізнився (>2/3 руху вже пройдено)"
    if r.mae_before_2R>=3: return "3 вчасно, але відкат ≥3 ATR до +2 ATR"
    if r.mae_before_2R>=1: return "4 вчасно, відкат 1–3 ATR (стоп 1 ATR вибиває)"
    return "5 вчасно і чисто (монетизується)"
D["cat"]=D.apply(cat,axis=1)
pd.set_option("display.width",250)
for T in [1.0,2.0,3.0]:
    d=D[D["T"]==T]
    print(f"\n===== |z|>={T}: хвилі за категоріями (частка хвиль)")
    print(pd.crosstab(d.cat,d.seg,normalize="columns").round(2))
    a=d[d.n_align>0]
    print("медіана: пройдено руху до сигналу",a.done_frac.median().round(2),"| лишилось ATR",a.remain_atr.median().round(1),
          "| сигналів у бік руху на хвилю",d.n_align.mean().round(1),"| проти руху",d.n_opp.mean().round(1))
D.to_csv("out_oos/ZCOVER.csv",index=False)
