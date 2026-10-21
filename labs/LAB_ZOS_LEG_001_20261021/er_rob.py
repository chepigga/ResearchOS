import pandas as pd,numpy as np
exec(open("regime2.py").read().split("rows=[dict(")[0])
rows=[]
for n in (10,15,20,30):
    for thr in (0.15,0.20,0.25,0.30):
        er=((c-c.shift(n)).abs()/c.diff().abs().rolling(n).sum())<thr
        e=er.shift(1).reindex(T.day).fillna(False).astype(bool).to_numpy()
        s0=port(T.net*np.where(e,0,1)); s5=port(T.net*np.where(e,0.5,1))
        rows.append(dict(дні=n,поріг=thr,частка=round(e.mean(),2),R_в=round(T.net[e].mean()/270,3),R_поза=round(T.net[~e].mean()/270,3),
            H1_в=round(T.net[e&(T.h=="H1")].sum()),H2_в=round(T.net[e&(T.h=="H2")].sum()),
            x0_сума=s0[0],x0_DD=s0[1],x0_мінус=s0[2],x0_жовт=s0[3],x05_DD=s5[1],x05_мінус=s5[2]))
print("як зараз:",port(T.net)); pd.set_option("display.width",250); print(pd.DataFrame(rows).to_string(index=False))
# by leg for ER20<0.2
e=f["ER20"].reindex(T.day).fillna(False).to_numpy().astype(bool)
print(T.assign(e=e).groupby(["leg","e"]).net.agg(["sum","count"]).round(0).to_string())
