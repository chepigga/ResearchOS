import numpy as np,pandas as pd
src=open("drop270.py").read().split("for k in (3,4,5):")[0]; exec(src)
for k in (3,4):
    ev=cross(F["dr12"],k,k/3); rows=[]
    for i,sd in ev:
        a=BA[i]; pre=sd*(BC[i]-BC[i-72])/a
        rows.append(dict(tr=BT[i]<TE,ctx="ціна до цього йшла ПРОТИ угоди (розворот)" if pre<-0.5 else ("ціна йшла В БІК угоди (продовження)" if pre>0.5 else "ціна стояла"),
                         h4=sd*(BC[i+48]-BC[i])/a,h12=sd*(BC[i+144]-BC[i])/a,h24=sd*(BC[i+288]-BC[i])/a,h48=sd*(BC[i+576]-BC[i])/a))
    D=pd.DataFrame(rows); D["seg"]=np.where(D.tr,"21-24","25-26")
    print(f"\n=== |зміна ratio за 1 год| >= {k} SD; угода = проти натовпу (ratio впав -> LONG, виріс -> SHORT); рух ціни за 6 год ДО події")
    g=D.groupby(["ctx","seg"]).agg(n=("h4","size"),h4=("h4","mean"),h12=("h12","mean"),h24=("h24","mean"),h48=("h48","mean"))
    g["n/міс"]=g.n/np.where(g.index.get_level_values(1)=="21-24",48,19.3)
    print(g.drop(columns="n").round(2).to_string())
