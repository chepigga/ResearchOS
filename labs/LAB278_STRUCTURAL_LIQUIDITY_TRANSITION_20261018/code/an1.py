import numpy as np,pandas as pd
E=pd.read_pickle("events.pkl"); E["seg"]=np.where(E.tr,"2021-24","2025-26"); MO={"2021-24":48,"2025-26":19.3}
def se(x): return x.std()/np.sqrt(len(x))
rows=[]
for (W,lr,seg),x in E.groupby(["W","lr","seg"]):
    rows.append(dict(W=W,lr=lr,seg=seg,n_mo=len(x)/MO[seg],B=x.hitB.mean(),A=(x.res=="A").mean(),TO=(x.res=="TIMEOUT").mean(),
        null=x.p0.mean(),edge=x.hitB.mean()-x.p0.mean(),edge_se=se(x.hitB-x.p0),accel=x.accel.mean(),
        dA=x.dA_atr.median(),dB=x.dB_atr.median(),hB=x[x.res=="B"].hrs.median(),hA=x[x.res=="A"].hrs.median(),
        grossR=x.grossR.mean(),cont_net=x.netR_cont.mean(),fade_net=x.netR_fade.mean(),cost=x.costR.mean()))
R=pd.DataFrame(rows); pd.set_option("display.width",250); print(R.round(3).to_string(index=False))
