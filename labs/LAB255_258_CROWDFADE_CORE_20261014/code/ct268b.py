import io,contextlib,numpy as np,pandas as pd
EQ=pd.read_pickle("ct268_eq.pkl")
src=open("dtune.py").read().split("rows=[]")[0]; g={}
with contextlib.redirect_stdout(io.StringIO()): exec(compile(src,"dt","exec"),g)
BT,TE,AB=g["BT"],g["TE"],g["AB"]; T=pd.DatetimeIndex(BT)
def money(P):
    o=[]
    for m,mo in [(T<TE,48),(T>=TE,19.3)]:
        y=P[m]-P[m].iloc[0]; o+=[y.iloc[-1]/mo,float((y.cummax()-y).max())]
    k=7/max(o[1],o[3]); return f"%/міс {o[0]:.2f}/{o[2]:.2f} DD {o[1]:.2f}/{o[3]:.2f} -> ${o[0]*k*1000:.0f} / ${o[2]*k*1000:.0f}"
D0=EQ[("D2","NONE","-")]; S0=EQ[("S","NONE","-")]
for nm,D,S in [("ядро + S (як зараз)",D0,S0),
               ("D2: вихід коли натовп розвернувся (завжди)",EQ[("D2","CROWD","ALWAYS")],S0),
               ("D2: вихід коли натовп розвернувся (лише в плюсі ≥1R)",EQ[("D2","CROWD","PROFIT")],S0),
               ("S: вихід на перетині EMA9/20 H1",D0,EQ[("S","EMA9/20_H1","ALWAYS")]),
               ("обидва: D2 натовп (в плюсі) + S EMA9/20",EQ[("D2","CROWD","PROFIT")],EQ[("S","EMA9/20_H1","ALWAYS")]),
               ("обидва: D2 натовп (завжди) + S EMA9/20",EQ[("D2","CROWD","ALWAYS")],EQ[("S","EMA9/20_H1","ALWAYS")])]:
    print(f"{nm:55s}", money(AB+D*0.10+S*0.10))
