import pandas as pd,numpy as np
T=pd.read_pickle("/home/claude/v6/trades.pkl"); T=T[T.leg.isin(["Z","D","L"])].copy()
m15=pd.read_pickle("/home/claude/bk/m15.pkl"); h1=pd.read_pickle("/home/claude/bk/h1.pkl"); d1=pd.read_pickle("/home/claude/bk/d1.pkl")
def atr(b,n=14):
    c=b.close; return pd.concat([b.high-b.low,(b.high-c.shift()).abs(),(b.low-c.shift()).abs()],axis=1).max(axis=1).rolling(n).mean()
h1["atr"]=atr(h1); h1["e30"]=h1.close.ewm(span=30,adjust=False).mean()
H=h1.index.values; hh=h1.high.values; hl=h1.low.values; ha=h1.atr.values; he=h1.e30.values; hc=h1.close.values
s=np.where(T.side=="buy",1,-1); T["s"]=s
rows=[]
for r in T.itertuples():
    k=np.searchsorted(H,np.datetime64(r.et),side="right")-1   # поточний (незакритий) бар H1
    k1=k-1                                                     # останній закритий
    if k1<30: rows.append((np.nan,)*6); continue
    a=ha[k1]
    lo24=hl[k1-23:k1+1].min(); hi24=hh[k1-23:k1+1].max()
    ext=((r.ep-lo24) if r.s>0 else (hi24-r.ep))/a          # скільки ATR H1 ціна вже пройшла від 24-год екстремуму
    dema=r.s*(r.ep-he[k1])/a                                 # відстань від EMA30 H1 у бік угоди
    R=abs(r.ep-r.sl)
    # після виходу: чи пішла ціна на +2R від входу в бік угоди за 48 год
    k2=np.searchsorted(H,np.datetime64(r.xt)); seg=slice(k2,min(k2+48,len(H)))
    fav=(hh[seg].max()-r.ep) if r.s>0 else (r.ep-hl[seg].min())
    adv=(r.ep-hl[seg].min()) if r.s>0 else (hh[seg].max()-r.ep)
    later2R=fav>=2*R
    # до входу: рух за попередні 24 год у бік угоди (ATR) — запізнення
    pre=r.s*(r.ep-hc[k1-23])/a
    rows.append((ext,dema,pre,later2R,fav/R if R>0 else np.nan,a))
F=pd.DataFrame(rows,columns=["ext","dEMA","pre24","later2R","favR","atrH1"],index=T.index)
T=pd.concat([T,F],axis=1); T["h"]=np.where(T.et<"2024-06-01","A","B"); T.to_pickle("/home/claude/v6/tim.pkl")
