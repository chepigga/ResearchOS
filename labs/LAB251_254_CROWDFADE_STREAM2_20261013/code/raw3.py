import os
os.environ["LAB_CACHE"]="/home/claude/lab251/cache_full.pkl"
import numpy as np, pandas as pd
import lab251 as L
BT,BC,BA,N=L.BT,L.BC,L.BA,L.N; BZ=np.asarray(L.C["BZ"],float); az=np.abs(BZ)
TE=pd.Timestamp("2025-01-01",tz="UTC")
df=pd.DataFrame({"c":BC,"a":BA},index=BT); hh=df.resample("1h").agg({"c":"last","a":"last"}).dropna()
C=hh.c.to_numpy(); A=hh.a.to_numpy(); T=hh.index
piv=[0]; d=0; ei=0
for i in range(1,len(C)):
    if d>=0:
        if C[i]>C[ei]: ei=i
        elif C[ei]-C[i]>=3*A[ei]: piv.append(ei); d=-1; ei=i; continue
    if d<=0:
        if C[i]<C[ei]: ei=i
        elif C[i]-C[ei]>=3*A[ei]: piv.append(ei); d=1; ei=i
piv.append(ei)
W=pd.DataFrame([(T[a],T[b],int(np.sign(C[b]-C[a])),abs(C[b]-C[a])/A[a]) for a,b in zip(piv[:-1],piv[1:]) if b>a],columns=["t0","t1","dir","size"])
W=W[W["size"]>=3]
pos=lambda t:int(np.searchsorted(BT.values,np.datetime64(t.tz_convert("UTC").tz_localize(None))))
for Tz in [1.0,2.0]:
    F=np.where((az>=Tz)&(np.r_[0,az[:-1]]<Tz))[0]
    rows=[]
    for w in W.itertuples():
        i0,i1=pos(w.t0),pos(w.t1); third=i0+(i1-i0)//3
        f=F[(F>=i0)&(F<i1)]; sd=-np.sign(BZ[f])
        al=f[sd==w.dir]; op=f[sd==-w.dir]
        rows.append(dict(seg="2021-24" if w.t0<TE else "2025-26",any_al=len(al)>0,early_al=(al<=third).any(),n_al=len(al),n_op=len(op),
                         first_is_al=(len(f)>0 and sd[0]==w.dir)))
    D=pd.DataFrame(rows)
    g=D.groupby("seg").agg(moves=("n_al","size"),any_aligned=("any_al","mean"),aligned_in_first_third=("early_al","mean"),
        first_signal_right=("first_is_al","mean"),sig_with=("n_al","mean"),sig_against=("n_op","mean"))
    g["precision"]=g.sig_with/(g.sig_with+g.sig_against)
    print(f"|z|>={Tz}\n",g.round(2).to_string())
