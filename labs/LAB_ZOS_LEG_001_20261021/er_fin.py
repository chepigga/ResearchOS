import pandas as pd,numpy as np
exec(open("regime2.py").read().split("rows=[dict(")[0])
def erm(n,thr): return (((c-c.shift(n)).abs()/c.diff().abs().rolling(n).sum())<thr).shift(1).reindex(T.day).fillna(False).astype(bool).to_numpy()
noF=(T.leg!="F").to_numpy()
for nm,mult in [("як зараз",np.ones(len(T))),("без F",noF*1.0),
                ("ER20<0.20 x0.5",np.where(erm(20,0.2),0.5,1)),("ER20<0.20 x0.5, без F",np.where(erm(20,0.2),0.5,1)*noF),
                ("ER30<0.20 x0.5",np.where(erm(30,0.2),0.5,1)),("ER30<0.20 x0.5, без F",np.where(erm(30,0.2),0.5,1)*noF)]:
    s=port(T.net*mult); net=T.net*mult
    print(f"{nm:24s} сума {s[0]:6d}  DD міс {s[1]:5d}  мінус-міс {s[2]}  жовт {s[3]:6d}  2022-24.06 {round(net[T.h=='H1'].sum()):6d}  2024.07-26 {round(net[T.h=='H2'].sum()):6d}")
