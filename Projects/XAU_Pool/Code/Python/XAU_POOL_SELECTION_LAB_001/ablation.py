"""
АБЛЯЦІЯ: чи зводиться ефект до однієї фічі n_opposite?

Тест на OOS-1 + OOS-2 (2024-04 ... 2025-12), топ-4%/міс, той самий конвеєр.
  A. повна модель (36 фіч)          — еталон
  B. ТІЛЬКИ n_opposite
  C. БЕЗ n_opposite (35 фіч)
  D. лише блок співпадіння
  E. лише прапорці механік
  F. лише режимні фічі
  G. просте правило: n_opposite == 0
"""
import pandas as pd, numpy as np
from sklearn.linear_model import LogisticRegression

P=pd.read_parquet('/home/claude/pool_excess.parquet')
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

COOC=['n_bots','n_trend','n_ct','n_pat','n_vol','class_conflict',
      'n_timeframes','n_opposite','agreement_ratio']
REG=['atr_ratio','kaufman_er','slope','vr']
CTX=['spread_atr','hour','is_m5','is_m15','dir_f','s_ASIA','s_LONDON','s_NY','s_LATE']
FULL=MECHS+COOC+REG+CTX
P=P.dropna(subset=FULL+['excess']).reset_index(drop=True)
P['ym']=P.time.dt.to_period('M').astype(str)
TEST=[m for m in sorted(P.ym.unique()) if '2024-04'<=m<='2025-12']
ym=P.ym.to_numpy(); ex=P.excess.to_numpy(); y=(ex>0).astype(int)
base=ex[np.isin(ym,TEST)].mean()

def evaluate(feats):
    X=P[feats].to_numpy(np.float64); out=[]
    for m in TEST:
        tri=np.flatnonzero(ym<m); tei=np.flatnonzero(ym==m)
        if len(tri)<3000 or len(tei)<50: continue
        mu=X[tri].mean(0); sd=X[tri].std(0); sd[sd==0]=1
        mdl=LogisticRegression(C=0.5,max_iter=500).fit((X[tri]-mu)/sd,y[tri])
        p=mdl.predict_proba((X[tei]-mu)/sd)[:,1]
        k=max(1,int(round(len(tei)*0.04)))
        out.append(ex[tei][np.argsort(-p)[:k]])
    s=np.concatenate(out)
    return s.mean(), s.mean()-base, len(s)

print("="*78); print("АБЛЯЦІЯ на OOS-1+OOS-2"); print("="*78)
print(f"надлишок пулу: {base:+.4f}R\n")
print(f"{'варіант':<34}{'фіч':>5}{'рівень':>10}{'підйом':>10}{'% від повної':>14}")
print("-"*78)
sets=[("A. повна модель",FULL),
      ("B. ТІЛЬКИ n_opposite",['n_opposite']),
      ("C. БЕЗ n_opposite",[f for f in FULL if f!='n_opposite']),
      ("D. лише співпадіння",COOC),
      ("E. лише прапорці механік",MECHS),
      ("F. лише режимні",REG),
      ("G. співпадіння без n_opposite",[f for f in COOC if f!='n_opposite']),
      ("H. механіки + співпадіння",MECHS+COOC),
      ("I. без режимних",MECHS+COOC+CTX)]
ref=None
for nm,fs in sets:
    lvl,lift,n=evaluate(fs)
    if ref is None: ref=lift
    print(f"{nm:<34}{len(fs):>5}{lvl:>+10.4f}{lift:>+10.4f}{100*lift/ref:>13.0f}%")

# G — просте правило без моделі
print("\n" + "="*78); print("ПРОСТІ ПРАВИЛА БЕЗ МОДЕЛІ"); print("="*78)
T=P[np.isin(ym,TEST)]
for nm,mask in [("n_opposite == 0",T.n_opposite==0),
                ("n_opposite == 0 і n_ct >= 1",(T.n_opposite==0)&(T.n_ct>=1)),
                ("n_trend == 0",T.n_trend==0),
                ("n_ct >= 1",T.n_ct>=1),
                ("n_timeframes >= 2",T.n_timeframes>=2)]:
    s=T[mask]
    print(f"  {nm:<32} N={len(s):>7,} ({100*len(s)/len(T):4.1f}%)  надлишок {s.excess.mean():+.4f}R")

print("\n--- розподіл n_opposite і надлишок ---")
g=T.groupby('n_opposite').excess.agg(['size','mean'])
print(g[g['size']>=100].head(12).round(4).to_string())
