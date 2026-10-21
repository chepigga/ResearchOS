import pandas as pd,numpy as np
exec(open("poc.py").read().split("def profile")[0])
prof=pd.read_pickle("prof.pkl")
def sim(day,side,lvl,stop,tgt,bars):
    """limit at lvl; side=+1 long. returns R or None"""
    filled=False
    for t,o,h,l,cl,sp in bars:
        if not filled:
            if t.hour>=20: return None
            if (side>0 and l<=lvl) or (side<0 and h>=lvl):
                filled=True; e=lvl if not ((side>0 and o<lvl) or (side<0 and o>lvl)) else o
                cost=sp/100+0.10; risk=abs(e-stop)
                if risk<=0: return None
                if (side>0 and l<=stop) or (side<0 and h>=stop): return -1-cost/risk
            continue
        if (side>0 and l<=stop) or (side<0 and h>=stop): return -1-cost/risk
        if (side>0 and h>=tgt) or (side<0 and l<=tgt): return abs(tgt-e)/risk-cost/risk
        if t.hour>=22 or (t.hour==21 and t.minute>=45): return side*(cl-e)/risk-cost/risk
    return side*(cl-e)/risk-cost/risk if filled else None
rows=[]
for d in days:
    if d not in g5 or np.isnan(atr[d]): continue
    b=g5[d]; b=b[b.index.hour>=1]
    if len(b)<50: continue
    bars=list(zip(b.index,b.open,b.high,b.low,b.close,b.spread)); o0=b.open.iloc[0]; A=atr[d]
    for N in (1,5):
        poc,vah,val=prof[(N,d)]; w=vah-val
        for s in (0.15,0.25,0.4):
            S=s*A
            # VA fade -> target POC
            if o0<vah and vah-poc>S*0.5: rows.append((d,N,s,"VAH->POC шорт",sim(d,-1,vah,vah+S,poc,bars)))
            if o0>val and poc-val>S*0.5: rows.append((d,N,s,"VAL->POC лонг",sim(d,1,val,val-S,poc,bars)))
            # POC bounce, target 1.5R ; and placebo levels
            for nm,L in (("POC",poc),("плацебо POC+0.5VA",poc+0.5*w),("плацебо POC-0.5VA",poc-0.5*w)):
                if o0>L: rows.append((d,N,s,f"{nm} відбиття лонг",sim(d,1,L,L-S,L+1.5*S,bars)))
                if o0<L: rows.append((d,N,s,f"{nm} відбиття шорт",sim(d,-1,L,L+S,L-1.5*S,bars)))
T=pd.DataFrame(rows,columns=["d","N","s","st","R"]).dropna()
T["reg"]=np.where(er20.reindex(T.d).values<0.20,"без напрямку","тренд")
T["half"]=np.where(T.d<"2024-07-01","H1","H2"); T["oct"]=(T.d>="2026-10-01")
T.to_pickle("pocT.pkl")
