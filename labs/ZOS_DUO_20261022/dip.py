import pandas as pd,numpy as np,itertools
h1=pd.read_pickle("h1.pkl"); m1=pd.read_pickle("m1.pkl")
M=m1[["open","high","low","close","spread"]].values; MT=m1.index.values
o,h,l,c=[h1[x].values for x in ("open","high","low","close")]; idx=h1.index; N=len(h1)
pos=np.searchsorted(MT,idx.values)
bear=c<o; lowclose=(c-l)/np.where(h>l,h-l,np.nan)<0.5
def run(entry,tp_pct,sl_pct,maxh,exit_bull):
    out=[]; i=2
    while i<N-2:
        if not entry[i]: i+=1; continue
        k=pos[i+1]
        if k>=len(M): break
        e=M[k,0]+M[k,4]/100; SL=e*sl_pct/100; TP=e*tp_pct/100; st=e-SL; tg=e+TP
        j=i+1; res=None
        while j<N and j<=i+maxh:
            k0=pos[j]; k1=pos[j+1] if j+1<N else len(M)
            for kk in range(k0,k1):
                if M[kk,2]<=st: res=-SL; break
                if M[kk,1]>=tg: res=TP; break
            if res is not None: break
            if exit_bull and c[j]>o[j]: res=c[j]-e; break      # вихід на закритті першого бичачого бару
            j+=1
        if res is None: j=min(j,N-1); res=c[j]-e
        out.append((idx[i+1],(res-0.1)/SL,j-i)); i=j+1
    return pd.DataFrame(out,columns=["t","R","bars"])
E={"будь-яка година":np.ones(N,bool),"попередній бар ведмежий":bear,"ведмежий і закриття в нижній половині":bear&lowclose}
rows=[];store={}
for (en,ent),(tp,sl),mh,eb in itertools.product(E.items(),((1.05,1.05),(0.5,1.05),(0.5,0.5),(1.05,0.5)),(4,24),(True,False)):
    T=run(ent,tp,sl,mh,eb); store[(en,tp,sl,mh,eb)]=T
    f=T[(T.t>="2023-02-01")&(T.t<"2023-03-01")]; j=T[(T.t>="2023-01-01")&(T.t<"2023-02-01")]
    rows.append((en,tp,sl,mh,eb,len(f),f.R.sum(),j.R.sum(),len(T),T.R.mean(),T.R[T.t<"2024-06-01"].mean(),T.R[T.t>="2024-06-01"].mean()))
O=pd.DataFrame(rows,columns=["вхід","TP%","SL%","макс год","вихід на бичачому","лют n","лют ΣR","січ ΣR","угод","R/уг","1-а пол","2-а пол"])
pd.to_pickle(store,"dip.pkl"); pd.set_option("display.width",230)
print(O.sort_values("лют ΣR",ascending=False).head(16).round(3).to_string(index=False))
print("\nНайкращі за всією історією:"); print(O.sort_values("R/уг",ascending=False).head(6).round(3).to_string(index=False))
