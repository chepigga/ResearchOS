"""Step 2 (pre-registered): condition edge on crowd (z6,z24 vs direction), OI change 6h/24h, taker share, 1h momentum, LVN depth.
Buckets = TRAIN terciles (crowd: fixed  >=+0.5 against-our-move / middle / <=-0.5). All 6 configs; a bucket counts only if
edge > 2 SE on TRAIN in the primary config (W336 lr0.7) AND same sign in >=4/6 configs. Then net EV and $/mo on both periods."""
import numpy as np,pandas as pd
E=pd.read_pickle("events.pkl"); E["seg"]=np.where(E.tr,"21","25")
feats=["crowd6","crowd24","oi6","oi24","taker","mom1","depth","dA_atr"]
rows=[]
for (W,lr),X in E.groupby(["W","lr"]):
    T=X[X.tr]
    for f in feats:
        if f.startswith("crowd"): cuts=[("проти руху ≤−0.5",X[f]<=-0.5),("нейтр.",(X[f]>-0.5)&(X[f]<0.5)),("за рух ≥+0.5",X[f]>=0.5)]
        else:
            q1,q2=T[f].quantile([1/3,2/3]); cuts=[("низ",X[f]<=q1),("сер",(X[f]>q1)&(X[f]<=q2)),("верх",X[f]>q2)]
        for nm,m in cuts:
            r=dict(W=W,lr=lr,feat=f,bucket=nm)
            for sg in ("21","25"):
                x=X[m&(X.seg==sg)]; dlt=x.hitB-x.p0
                r.update({f"n{sg}":len(x),f"edge{sg}":dlt.mean(),f"z{sg}":dlt.mean()/(dlt.std()/np.sqrt(max(len(x),2))),f"cont{sg}":x.netR_cont.mean(),f"fade{sg}":x.netR_fade.mean()})
            rows.append(r)
R=pd.DataFrame(rows); R.to_csv("step2.csv",index=False)
P=R[(R.W==336)&(R.lr==0.7)].copy()
cons=R.groupby(["feat","bucket"]).apply(lambda x:(np.sign(x.edge21)==np.sign(x.edge21.mean())).sum()).rename("same_sign_cfg")
P=P.merge(cons.reset_index(),on=["feat","bucket"])
pd.set_option("display.width",250); print(P.drop(columns=["W","lr"]).round(3).to_string(index=False))
print("\nкандидати (|z21|>2):"); print(R[R.z21.abs()>2].round(3).to_string(index=False))
