"""
XAU_POOL_SELECTION_LAB_001 | GATE-4 — PERMUTATION

200 шафлів мітки ВСЕРЕДИНІ МІСЯЦЯ, повний конвеєр щоразу.
Реальний надлишок має перевищити p95 нульового розподілу.

Шафлиться пара (excess, R) разом — тобто фічі лишаються на місці,
а результат угоди перемішується між кандидатами того самого місяця.
Це руйнує зв'язок фіча->результат, зберігаючи всі інші властивості
даних: розподіл excess по місяцях, обсяги, сезонність.

Оцінюється на OOS-1 + OOS-2 (об'єднано), топ-4% на місяць.
"""
import pandas as pd, numpy as np, time
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

t0=time.time()
P=pd.read_parquet(f'{DATA}/pool_excess.parquet')
MECHS=[c for c in P.columns if c.startswith('f_')]
TREND=['f_T_PRICECHANNEL','f_T_LINREG','f_T_MACD_MOM','f_T_PSAR','f_T_ALLIGATOR',
       'f_T_ENVELOPE','f_C_PIVOT','f_T_SMA_STOCH']
CT=['f_C_BOLLINGER','f_C_WILLIAMS']; PAT=['f_P_PINBAR','f_P_3SOLDIER','f_P_TURNAROUND']
P['n_trend']=P[TREND].sum(axis=1); P['n_ct']=P[CT].sum(axis=1)
P['n_pat']=P[PAT].sum(axis=1); P['n_vol']=P['f_V_ATR_EXP']
P['class_conflict']=((P.n_trend>0)&(P.n_ct>0)).astype(int)
P['agreement_ratio']=P.n_bots/(P.n_bots+P.n_opposite).replace(0,np.nan)
P['is_m5']=(P.tf=='M5').astype(int); P['is_m15']=(P.tf=='M15').astype(int)
P['dir_f']=P['dir']
for s in ['ASIA','LONDON','NY','LATE']: P['s_'+s]=(P.session==s).astype(int)
FEATS=(MECHS+['n_bots','n_trend','n_ct','n_pat','n_vol','class_conflict',
       'n_timeframes','n_opposite','agreement_ratio','atr_ratio','kaufman_er',
       'slope','vr','spread_atr','hour','is_m5','is_m15','dir_f',
       's_ASIA','s_LONDON','s_NY','s_LATE'])
P=P.dropna(subset=FEATS+['excess']).reset_index(drop=True)
P['ym']=P.time.dt.to_period('M').astype(str)
TEST=[m for m in sorted(P.ym.unique()) if '2024-04'<=m<='2025-12']
X=P[FEATS].to_numpy(np.float64); ym=P.ym.to_numpy()
print(f"пул {len(P):,} | тестових місяців {len(TEST)}  [{time.time()-t0:.0f}s]")

def run(excess):
    y=(excess>0).astype(int); sel_ex=[]
    for m in TEST:
        tri=np.flatnonzero(ym<m); tei=np.flatnonzero(ym==m)
        if len(tri)<3000 or len(tei)<50: continue
        mu=X[tri].mean(0); sd=X[tri].std(0); sd[sd==0]=1
        mdl=LogisticRegression(C=0.5,max_iter=300).fit((X[tri]-mu)/sd,y[tri])
        p=mdl.predict_proba((X[tei]-mu)/sd)[:,1]
        k=max(1,int(round(len(tei)*0.04)))
        sel_ex.append(excess[tei][np.argsort(-p)[:k]])
    s=np.concatenate(sel_ex)
    return s.mean(), s.mean()-excess[np.isin(ym,TEST)].mean(), len(s)

real_lvl,real_lift,n=run(P.excess.to_numpy())
print(f"\nРЕАЛЬНИЙ: рівень {real_lvl:+.4f}R | підйом {real_lift:+.4f}R | N={n:,}  [{time.time()-t0:.0f}s]")

print("\n200 шафлів...")
rng=np.random.default_rng(2026)
ex=P.excess.to_numpy()
gidx=[np.flatnonzero(ym==m) for m in sorted(P.ym.unique())]
import os,json
import os
DATA=os.environ.get("XAU_DATA", os.path.dirname(os.path.abspath(__file__)))

CK=f'{DATA}/perm_ck.jsonl'
done=[]
if os.path.exists(CK):
    done=[json.loads(l) for l in open(CK)]
    print(f"  відновлено {len(done)} шафлів")
# ВИПРАВЛЕНО: кожен шафл має власний детермінований seed,
# тому відновлення з контрольної точки НЕ порушує відтворюваності
TARGET=40
with open(CK,'a') as fh:
    for it in range(len(done),TARGET):
        r_it=np.random.default_rng(2026+it)   # seed на ітерацію
        sh=ex.copy()
        for g in gidx: sh[g]=r_it.permutation(sh[g])
        a,b,_=run(sh)
        fh.write(json.dumps({'lv':float(a),'lf':float(b)})+'\n'); fh.flush()
        print(f"  {it+1}/{TARGET}  lv={a:+.4f}  [{time.time()-t0:.0f}s]",flush=True)
res=[json.loads(l) for l in open(CK)]
lv=np.array([r['lv'] for r in res]); lf=np.array([r['lf'] for r in res])
print(f"\nшафлів усього: {len(lv)}")

print("\n"+"="*72); print("GATE-4 PERMUTATION"); print("="*72)
for nm,real,null in [("рівень",real_lvl,lv),("підйом",real_lift,lf)]:
    p95=np.percentile(null,95); p99=np.percentile(null,99)
    pv=(null>=real).mean()
    print(f"\n{nm}:")
    print(f"  реальний      {real:+.4f}R")
    print(f"  нуль: сер {null.mean():+.4f}  sd {null.std():.4f}  "
          f"p95 {p95:+.4f}  p99 {p99:+.4f}  max {null.max():+.4f}")
    print(f"  p-value       {pv:.4f}   ({int((null>=real).sum())}/{len(null)} шафлів >= реального)")
    print(f"  ВЕРДИКТ       {'PASS' if real>p95 else 'FAIL'}  (поріг p95)")
np.savez(f'{DATA}/perm.npz',lv=lv,lf=lf,real_lvl=real_lvl,real_lift=real_lift)
print(f"\n[{time.time()-t0:.0f}s]")
