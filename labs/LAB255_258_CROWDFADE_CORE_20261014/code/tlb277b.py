exec(open("tlb277.py").read().split("\nrows=[]\nfor p in")[0])
LS,LV,TAB,pivs=lines(3)
for ctx,crowd in (("STRUCT","ANY"),("STRUCT+HTF","ANY"),("STRUCT+HTF","NOT_AGAINST")):
    t=run(3,ctx,0.1,"UP",crowd,LS,LV,TAB,pivs); c=COST/1e4*t.e/t.R; g_=t.r+c
    for sg,m in (("2021-24",t.tr),("2025-26",~t.tr)):
        print(ctx,crowd,sg,f"n={m.sum()} нетто {t.r[m].mean():+.2f}R  брутто {g_[m].mean():+.2f}R  витрати {c[m].mean():.2f}R  стоп {np.median((t.R/BA[t.i.to_numpy(int)])[m]):.2f} ATR  виграшних {(t.r[m]>0).mean():.0%}")
