import pandas as pd,numpy as np
m15=pd.read_pickle("m15.pkl"); h1=pd.read_pickle("h1.pkl"); m1=pd.read_pickle("m1b.pkl")
def tr_(b): c=b.close; return pd.concat([b.high-b.low,(b.high-c.shift()).abs(),(b.low-c.shift()).abs()],axis=1).max(axis=1)
def adx(b,n=14):
    up=b.high.diff(); dn=-b.low.diff()
    pdm=np.where((up>dn)&(up>0),up,0.0); ndm=np.where((dn>up)&(dn>0),dn,0.0)
    a=2/(n+1)  # MT5 iADX: EMA-згладжування
    tr=tr_(b)
    pdi=100*pd.Series(pdm,b.index).ewm(alpha=a,adjust=False).mean()/tr.ewm(alpha=a,adjust=False).mean()
    ndi=100*pd.Series(ndm,b.index).ewm(alpha=a,adjust=False).mean()/tr.ewm(alpha=a,adjust=False).mean()
    dx=100*(pdi-ndi).abs()/(pdi+ndi); return dx.ewm(alpha=a,adjust=False).mean()
def build(sens=1.5,cons=True,htf=True,adx_thr=20.0):
    b=m15.copy(); o,h,l,c=b.open.values,b.high.values,b.low.values,b.close.values
    a10=tr_(b).rolling(10).mean().values
    N=len(b); st=np.zeros(N); d=np.ones(N,int); st[0]=c[0]
    for i in range(1,N):
        x=(o[i]+h[i]+l[i]+c[i])/4; ub=x+sens*a10[i]; lb=x-sens*a10[i]; p=st[i-1]
        if np.isnan(a10[i]): st[i]=c[i]; d[i]=d[i-1]; continue
        if d[i-1]==1:
            if not (lb>p or c[i-1]<p): lb=p
            if c[i]<lb: d[i]=-1; st[i]=ub
            else: d[i]=1; st[i]=lb
        else:
            if not (ub<p or c[i-1]>p): ub=p
            if c[i]>ub: d[i]=1; st[i]=lb
            else: d[i]=-1; st[i]=ub
    sig=np.zeros(N,int); sig[1:]=np.where((d[1:]>0)&(d[:-1]<0),1,np.where((d[1:]<0)&(d[:-1]>0),-1,0))
    b["raw"]=sig; b["adx"]=adx(b).values
    e1=h1.close.ewm(span=150,adjust=False).mean(); e2=h1.close.ewm(span=250,adjust=False).mean()
    hb=np.sign(e1-e2); hb.index=hb.index+pd.Timedelta(hours=1)
    b["htf"]=hb.reindex(b.index,method="ffill").values
    s=sig.copy()
    if cons: s=np.where(b.adx.values>adx_thr,s,0)
    if htf: s=np.where(s==b.htf.values,s,0)
    b["sig"]=s; b["atr14"]=tr_(b).rolling(14).mean(); return b
M=m1[["open","high","low","close"]].values; MT=m1.index.values
def simulate(b,slm=2.2,tps=(1,2,3),fri=21,close_opp=True,allow=None):
    idx=b.index; sig=b.sig.values; A=b.atr14.values; sp=b.spread.values; H=b.high.values; Lw=b.low.values
    pos=np.searchsorted(MT,idx.values); out=[]; N=len(b); i=0
    while i<N-1:
        s=sig[i]
        if s==0 or np.isnan(A[i]) or (allow is not None and not allow[i]): i+=1; continue
        t=idx[i+1]
        if t.weekday()==4 and t.hour>=fri: i+=1; continue
        k=pos[i+1]
        if k>=len(M): break
        e=M[k,0]; stp=(Lw[i]-slm*A[i]) if s>0 else (H[i]+slm*A[i]); R=abs(e-stp)
        if R<=0: i+=1; continue
        st=stp; rem=1.0; pnl=0.0; ph=0; cost=sp[i]/100+0.10; tp=[e+s*x*R for x in tps]
        j=i+1; done=False
        while j<N and not done:
            k0=pos[j]; k1=pos[j+1] if j+1<N else len(M); tj=idx[j]
            if tj.weekday()==4 and tj.hour>=fri: pnl+=rem*s*(M[k0,0]-e); done=True; break
            for kk in range(k0,k1):
                op,hh,ll,cl=M[kk]
                if (s>0 and ll<=st) or (s<0 and hh>=st):
                    f=min(op,st) if s>0 else max(op,st); pnl+=rem*s*(f-e); done=True; break
                while ph<3 and ((s>0 and hh>=tp[ph]) or (s<0 and ll<=tp[ph])):
                    if ph==2: pnl+=rem*s*(tp[2]-e); rem=0; done=True; break
                    q=rem*0.5; pnl+=q*s*(tp[ph]-e); rem-=q; st=(e+s*0.10) if ph==0 else tp[0]; ph+=1
                if done: break
            if done: break
            # opposite FILTERED signal closes (EA: ComputeSignal з фільтрами)
            if close_opp and sig[j]==-s:
                kn=pos[j+1] if j+1<N else len(M)-1; pnl+=rem*s*(M[min(kn,len(M)-1),0]-e); done=True; j+=1; break
            j+=1
        out.append((idx[i+1],s,(pnl-cost)/R,ph,idx[min(j,N-1)]))
        # same-direction signals while in position are skipped; opposite signal bar opens new trade
        i=j if (close_opp and j<N and sig[j-1]==-s) else max(j,i+1)
        if close_opp and sig[i-1]==-s and i-1>0: i=i-1
    return pd.DataFrame(out,columns=["t","s","R","ph","xt"])
