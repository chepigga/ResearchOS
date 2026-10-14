"""LAB265 (pre-registered). Supertrend x crowd compass, deeper grid.
TF 1h/2h/4h; sens 1.3/1.8/2.5/3.0; HTF filter off/on (H1 EMA150 vs 250);
exits: AS = AlgoSignals (SL 2.2ATR14, 50%@1R->BE, 25%@2R->SL 1R, 25%@3R, opposite flip closes)
       RIDE = SL 2.2ATR14, no TP, exit on opposite flip (trend-following);
compass filters (applied post hoc, trades are independent since every flip closes the previous one):
       NONE | NO_AGAINST_z24_1 (skip if -sign(z24)==-side & |z24|>=1) | NO_AGAINST_z24_05 | ONLY_WITH_z24_1.
Selection: 2021-24 R/DD, prefer plateau (neighbours). 2025-26 reported."""
import numpy as np,pandas as pd,itertools
src=open("st264.py").read().split("\nrows=[]; st_rows=[]")[0]
exec(src)
def simX(sigs,htf,exitm):
    res=[]
    for n_,(si,ei,sd,dist) in enumerate(sigs):
        nxt=sigs[n_+1][1] if n_+1<len(sigs) else N-1
        if htf and HTF[si]!=sd: continue
        e=BO[ei]; R=dist
        if R<=0: continue
        c=COST/1e4*e/R; stp=e-sd*R; w=1.0; bank=0.0; stg=0; out=None
        for i in range(ei,min(nxt,N-1)+1):
            if i==nxt: out=bank+w*sd*(BO[i]-e)/R; break
            if (BL[i]<=stp) if sd>0 else (BH[i]>=stp): out=bank+w*sd*(stp-e)/R; break
            if exitm=="AS":
                fav=(BH[i]-e) if sd>0 else (e-BL[i])
                if stg==0 and fav>=R: bank+=0.5; w=0.5; stg=1; stp=e
                if stg==1 and fav>=2*R: bank+=0.5; w=0.25; stg=2; stp=e+sd*R
                if stg==2 and fav>=3*R: bank+=0.75; w=0; out=bank; break
        if out is None: out=bank+w*sd*(BC[min(nxt,N-1)]-e)/R
        z=z24[si]; cz=0 if not np.isfinite(z) else -np.sign(z)
        res.append(dict(si=si,tr=BT[si]<TE,side=sd,r=out-c,cz=cz,az=abs(z) if np.isfinite(z) else 0,h=(i-ei)/12))
    return pd.DataFrame(res)
F={"NONE":lambda d:d,
   "NO_AGAINST_1":lambda d:d[~((d.cz==-d.side)&(d.az>=1))],
   "NO_AGAINST_05":lambda d:d[~((d.cz==-d.side)&(d.az>=0.5))],
   "ONLY_WITH_1":lambda d:d[(d.cz==d.side)&(d.az>=1)]}
rows=[]; store={}
for tf in ("1h","2h","4h"):
    for sens in (1.3,1.8,2.5,3.0):
        S=signals(tf,sens)
        for htf in (False,True):
            for ex in ("AS","RIDE"):
                A=simX(S,htf,ex); store[(tf,sens,htf,ex)]=A
                for fn,f in F.items():
                    t=f(A); r=dict(tf=tf,sens=sens,htf=htf,exit=ex,filt=fn)
                    for seg,m,mo in [("21",t.tr,48),("25",~t.tr,19.3)]:
                        x=t[m]; s=summ(x,mo)
                        r.update({f"n{seg}":s["n"],f"ev{seg}":s["ev"],f"pf{seg}":s["pf"],f"Rmo{seg}":s["Rmo"],f"dd{seg}":s["dd"],f"rdd{seg}":s["rdd"],f"hold{seg}":x.h.mean() if len(x) else np.nan})
                    rows.append(r)
        print(tf,sens,flush=True)
R=pd.DataFrame(rows); R.to_csv("out_oos/LAB265_ST_GRID.csv",index=False)
pd.to_pickle(store,"st265_store.pkl")
pd.set_option("display.width",300)
# per filter: how many configs positive in both periods
print("\n== частка конфігурацій з EV>0 (2021-24 / 2025-26 / обидва), середній EV")
for (ex,fn),x in R.groupby(["exit","filt"]):
    print(f"{ex:4s} {fn:14s} {(x.ev21>0).mean():.0%} / {(x.ev25>0).mean():.0%} / {((x.ev21>0)&(x.ev25>0)).mean():.0%}   EV {x.ev21.mean():+.3f} / {x.ev25.mean():+.3f}")
print("\n== за ТФ (усі сенс./HTF), фільтр NO_AGAINST_1, середній EV і R/DD")
print(R[R.filt=="NO_AGAINST_1"].groupby(["exit","tf"])[["ev21","ev25","rdd21","rdd25","n21"]].mean().round(3).to_string())
c=["tf","sens","htf","exit","filt","n21","ev21","pf21","Rmo21","rdd21","hold21","n25","ev25","pf25","Rmo25","rdd25"]
print("\n== топ-15 за R/DD 2021-24")
print(R.sort_values("rdd21",ascending=False)[c].head(15).round(2).to_string(index=False))
