import pandas as pd,numpy as np
m1=pd.read_pickle("m1.pkl"); h1=pd.read_pickle("h1.pkl")
M=m1[["open","high","low","close","spread"]].values; MT=m1.index.values
d1=pd.read_pickle("d1.pkl"); c=d1.close; e50=c.ewm(span=50,adjust=False).mean()
tr=pd.concat([d1.high-d1.low,(d1.high-c.shift()).abs(),(d1.low-c.shift()).abs()],axis=1).max(axis=1); atrd=tr.rolling(14).mean()
slope=((e50-e50.shift(3))/atrd); bias=np.where((c>e50)&(slope>=0.03),1,np.where((c<e50)&(slope<=-0.03),-1,0))
bias=pd.Series(bias,index=d1.index).shift(1)
def run(sl_mode,slv,tpv,d1buy=True):
    out=[]; H=h1.index; pos_until=np.datetime64("1970-01-01")
    for k in range(1,len(h1)-1):
        t0=H[k]; t1=H[k+1]
        if np.datetime64(t0)<pos_until: continue
        ph,pl=h1.high.iloc[k-1],h1.low.iloc[k-1]
        bp=ph+0.05; sp=pl-0.05
        if sl_mode=="usd": SL,TP=slv,tpv
        else: a=atrd.shift(1).reindex([t0.normalize()],method="ffill").iloc[0]; SL,TP=slv*a,tpv*a
        bz=bias.reindex([t0.normalize()],method="ffill").iloc[0]
        allowB=(not d1buy) or bz in (0,1)
        i0=np.searchsorted(MT,np.datetime64(t0)); i1=np.searchsorted(MT,np.datetime64(t1))
        side=None
        for i in range(i0,i1):
            o,h,l,cl,spd=M[i]
            if allowB and h+spd/100>=bp: side=1; e=bp; break
            if l<=sp: side=-1; e=sp; break
        if side is None: continue
        st=e-side*SL; tg=e+side*TP; res=None
        for j in range(i,min(i+60*24*5,len(M))):
            o,h,l,cl,spd=M[j]
            if j>i and ((side>0 and l<=st) or (side<0 and h+spd/100>=st)): res=-SL; break
            if (side>0 and h>=tg) or (side<0 and l+spd/100<=tg): res=TP; break
        if res is None: res=side*(M[j,3]-e)
        cost=M[i,4]/100+0.1
        out.append((pd.Timestamp(MT[i]),side,(res-cost)/SL,SL)); pos_until=MT[j]
    return pd.DataFrame(out,columns=["t","s","R","SL"])
R={}
R["$40/$74 (як у тесті)"]=run("usd",40,74)
R["$37/$97 (заморож. гео)"]=run("usd",37,97)
R["1 ATR_D1 / 2 ATR_D1"]=run("atr",1.0,2.0)
pd.to_pickle(R,"h1oco.pkl")
