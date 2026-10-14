import numpy as np,pandas as pd
src=open("st264.py").read().split("\nrows=[]; st_rows=[]")[0]
exec(src)
for sens in (1.3,1.8):
    S=signals("1h",sens)
    for htf in (False,True):
        A=sim(S,htf,lambda s:True)
        for mode,f in [("усі",lambda d:d),("лише ЗА z24",lambda d:d[d.state2=="ЗА"]),("без ПРОТИ z24",lambda d:d[d.state2!="ПРОТИ"])]:
            t=f(A); r=f"H1 sens{sens} HTF{'on' if htf else 'off'} {mode:14s}"
            for seg,m,mo in [("21-24",t.tr,48),("25-26",~t.tr,19.3)]:
                s=summ(t[m],mo); r+=f" | {seg}: {s['n']:.1f}/міс EV {s['ev']:+.3f} PF {s['pf']:.2f} R/міс {s['Rmo']:+.2f} DD {s['dd']:.1f}R"
            print(r)
