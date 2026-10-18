"""LAB270: sharp L/S ratio moves -> continuation or pullback? Event = |dr12| crosses k (ratio change over 1h in 6h-SD units), re-arm at k/3.
Sign convention: ratio DROP (crowd turns short) -> 'anti-crowd' side = LONG. Measure price move in that side over horizons, + price move BEFORE event."""
import numpy as np,pandas as pd
exec(open("zvel2.py").read().split("def evaluate")[0])
import lab251 as _L
BH,BL=_L.BH,_L.BL
H=[0.5,1,2,4,8,12,24,48]
def cross(x,thr,rearm):
    out=[];armed=True
    for i in range(400,N-600):
        v=x[i]
        if not np.isfinite(v): continue
        if abs(v)<rearm: armed=True; continue
        if armed and abs(v)>=thr and abs(x[i-1])<thr: out.append((i,-int(np.sign(v)))); armed=False
    return out
for k in (3,4,5):
    ev=cross(F["dr12"],k,k/3)
    rows=[]
    for i,sd in ev:
        a=BA[i]; r=dict(tr=BT[i]<TE,pre6h=sd*(BC[i]-BC[i-72])/a,pre1h=sd*(BC[i]-BC[i-12])/a)
        for h in H: r[f"{h}h"]=sd*(BC[i+int(h*12)]-BC[i])/a
        r["mae4h"]=min(0,min(sd*(BL[i+1:i+49]-BC[i]) if sd>0 else sd*(BH[i+1:i+49]-BC[i])))/a
        rows.append(r)
    D=pd.DataFrame(rows)
    print(f"\n=== різкий рух ratio: |зміна за 1 год| >= {k} SD ({len(D)} подій). Бік = проти натовпу (ratio впав -> LONG)")
    for tr,x in D.groupby("tr"):
        print(" 2021-24" if tr else " 2025-26", f"n/міс {len(x)/(48 if tr else 19.3):.1f}",
              "| рух ДО (у той самий бік): 6г",round(x.pre6h.mean(),2),"1г",round(x.pre1h.mean(),2))
        print("   середнє ПІСЛЯ:",x[[f"{h}h" for h in H]].mean().round(2).to_dict())
        print("   медіана ПІСЛЯ:",x[[f"{h}h" for h in H]].median().round(2).to_dict())
        print("   частка відкату ≥0.5 ATR проти за 4 год:",round((x.mae4h<=-0.5).mean(),2)," ≥1 ATR:",round((x.mae4h<=-1).mean(),2))
