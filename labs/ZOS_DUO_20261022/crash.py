import pandas as pd,numpy as np
d1=pd.read_pickle("d1.pkl"); h1=pd.read_pickle("h1.pkl")
d1=d1[d1.index.dayofweek<5]   # без недільних барів для подій
c=d1.close; tr=pd.concat([d1.high-d1.low,(d1.high-c.shift()).abs(),(d1.low-c.shift()).abs()],axis=1).max(axis=1); atr=tr.rolling(14).mean()
H=h1[["open","high","low","close","spread"]]
def events(dirn,k,look=10):
    ev=[]; last=-99; D=d1.index
    for i in range(30,len(d1)-1):
        if i-last<look: continue
        a=atr.iloc[i-1]
        if dirn<0:
            j0=d1.high.iloc[i-look+1:i+1].idxmax(); hi=d1.high.loc[j0]; lo=d1.low.loc[j0:D[i]].min()
            if hi-c.iloc[i]>=k*a and c.iloc[i]<=c.iloc[i-look+1:i+1].min(): ev.append((D[i],hi,lo,a)); last=i
        else:
            j0=d1.low.iloc[i-look+1:i+1].idxmin(); lo=d1.low.loc[j0]; hi=d1.high.loc[j0:D[i]].max()
            if c.iloc[i]-lo>=k*a and c.iloc[i]>=c.iloc[i-look+1:i+1].max(): ev.append((D[i],lo,hi,a)); last=i
    return ev
def trade(dirn,ev,f,slk,tpmode,wait=10,hold=10):
    out=[]
    for (d,ext,opp,a) in ev:
        start=d+pd.Timedelta(days=1); x=H[(H.index>=start)&(H.index<start+pd.Timedelta(days=wait*1.5))]
        # dirn<0: ext=swing high, opp=swing low (оновлюється до входу)
        low=opp; filled=None
        for t,r in x.iterrows():
            if dirn<0:
                if r.low<low: low=r.low
                lvl=low+f*(ext-low)
                if r.high>=lvl: filled=(t,lvl,low); break
            else:
                if r.high>low: low=r.high
                lvl=low-f*(low-ext)
                if r.low<=lvl: filled=(t,lvl,low); break
        if filled is None: continue
        t0,e,lw=filled; s=-1 if dirn<0 else 1
        sl=e+slk*a if s<0 else e-slk*a; R=abs(e-sl)
        tp=lw if tpmode=="екстремум" else e+s*2*R
        y=H[(H.index>t0)&(H.index<t0+pd.Timedelta(days=hold*1.4))]; res=None
        for t,r in y.iterrows():
            if (s<0 and r.high>=sl) or (s>0 and r.low<=sl): res=-R; xt=t; break
            if (s<0 and r.low<=tp) or (s>0 and r.high>=tp): res=abs(tp-e); xt=t; break
        if res is None: res=s*(y.close.iloc[-1]-e) if len(y) else 0; xt=y.index[-1] if len(y) else t0
        cost=x.spread.mean()/100+0.1+e*0.0002*max((xt-t0).days,0)   # спред + орієнтовний своп
        out.append((d,t0,s,(res-cost)/R,abs(tp-e)/R))
    return pd.DataFrame(out,columns=["подія","вхід","s","R","ціль_R"])
rows=[]; store={}
for dirn,nm in ((-1,"шорт після обвалу"),(1,"лонг після ралі")):
    for k in (2.5,3.0,4.0):
        ev=events(dirn,k)
        for f in (0.382,0.5,0.618):
            for slk in (1.0,1.5):
                for tpm in ("екстремум","2R"):
                    T=trade(dirn,ev,f,slk,tpm); store[(nm,k,f,slk,tpm)]=T
                    if len(T): rows.append((nm,k,len(ev),f,slk,tpm,len(T),T.R.mean(),T.R.sum(),(T.R>0).mean()))
O=pd.DataFrame(rows,columns=["тип","падіння ≥k·ATR","подій","відкат","SL ATR","ціль","угод","R/уг","ΣR","виграш"])
pd.to_pickle(store,"crash.pkl"); pd.set_option("display.width",200)
print(O.round(3).to_string(index=False))
