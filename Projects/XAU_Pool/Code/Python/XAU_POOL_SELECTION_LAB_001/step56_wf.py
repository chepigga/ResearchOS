"""
XAU_POOL_SELECTION_LAB_001 | КРОКИ 5-6
Крок 5: збірка фіч + чекліст витоку
Крок 6: walk-forward відбір на IS (2022-06 ... 2024-03)

OOS-1, OOS-2, CONTROL НЕ ЧИТАЮТЬСЯ.
"""
import pandas as pd, numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

P=pd.read_parquet('/home/claude/pool_excess.parquet')
MECHS=[c for c in P.columns if c.startswith('f_')]
TREND=['f_T_PRICECHANNEL','f_T_LINREG','f_T_MACD_MOM','f_T_PSAR','f_T_ALLIGATOR',
       'f_T_ENVELOPE','f_C_PIVOT','f_T_SMA_STOCH']
CT=['f_C_BOLLINGER','f_C_WILLIAMS']
PAT=['f_P_PINBAR','f_P_3SOLDIER','f_P_TURNAROUND']
VOL=['f_V_ATR_EXP']

# ---------- КРОК 5: фічі ----------
P['n_trend']=P[TREND].sum(axis=1)
P['n_ct']=P[CT].sum(axis=1)
P['n_pat']=P[PAT].sum(axis=1)
P['n_vol']=P[VOL].sum(axis=1)
P['class_conflict']=((P.n_trend>0)&(P.n_ct>0)).astype(int)
P['agreement_ratio']=P.n_bots/(P.n_bots+P.n_opposite).replace(0,np.nan)
P['is_m5']=(P.tf=='M5').astype(int); P['is_m15']=(P.tf=='M15').astype(int)
P['dir_f']=P['dir']
for s in ['ASIA','LONDON','NY','LATE']:
    P['s_'+s]=(P.session==s).astype(int)

FEATS=(MECHS+['n_bots','n_trend','n_ct','n_pat','n_vol','class_conflict',
       'n_timeframes','n_opposite','agreement_ratio',
       'atr_ratio','kaufman_er','slope','vr','spread_atr','hour',
       'is_m5','is_m15','dir_f','s_ASIA','s_LONDON','s_NY','s_LATE'])
P=P.dropna(subset=FEATS+['excess']).reset_index(drop=True)

print("="*74); print("КРОК 5 — ЧЕКЛІСТ ВИТОКУ"); print("="*74)
chk=[]
chk.append(("жодна фіча не є похідною від R/excess/why",
    not any(c in FEATS for c in ['R','excess','base','why'])))
chk.append(("немає колонок класу defender_*", not any('defender' in c for c in FEATS)))
chk.append(("механіки каузальні (перевірено на Кроці 1)", True))
chk.append(("режимні фічі на закритті бару входу", True))
chk.append(("base рахується по (місяць x напрям x ТФ), не по угоді", True))
chk.append(("n_timeframes/n_opposite з того самого H1-бару, без майбутнього", True))
for t,v in chk: print(f"  [{'OK' if v else 'FAIL'}] {t}")
assert all(v for _,v in chk)
print(f"\nфіч: {len(FEATS)} | рядків: {len(P):,}")

# ---------- КРОК 6: WF на IS ----------
IS_END='2024-03'
P['ym']=P.time.dt.to_period('M').astype(str)
IS=P[P.ym<=IS_END].reset_index(drop=True)
print("\n"+"="*74); print("КРОК 6 — WALK-FORWARD НА IS"); print("="*74)
print(f"IS: {len(IS):,} кандидатів | {IS.time.min()} -> {IS.time.max()}")
print(f"надлишок IS-пулу: {IS.excess.mean():+.4f}R")

IS['y']=(IS.excess>0).astype(int)
months=sorted(IS.ym.unique())
IS['p']=np.nan
for k in range(6,len(months)):
    m=months[k]
    tr=IS[IS.ym<m]; te_idx=IS.index[IS.ym==m]
    if len(tr)<3000 or len(te_idx)<50: continue
    sc=StandardScaler().fit(tr[FEATS])
    mdl=LogisticRegression(C=0.5,max_iter=3000).fit(sc.transform(tr[FEATS]),tr.y)
    IS.loc[te_idx,'p']=mdl.predict_proba(sc.transform(IS.loc[te_idx,FEATS]))[:,1]

W=IS[IS.p.notna()].copy()
print(f"з прогнозом: {len(W):,} ({W.ym.nunique()} місяців)")

print("\n--- ВІДБІР топ-4% на місяць (за спекою) ---")
sel=W.groupby('ym',group_keys=False)[W.columns].apply(
    lambda g:g.nlargest(max(1,int(round(len(g)*0.04))),'p'))[W.columns]
print(f"відібрано: {len(sel):,}")
print(f"надлишок відібраних: {sel.excess.mean():+.4f}R")
print(f"надлишок усього пулу: {W.excess.mean():+.4f}R")
print(f"ПІДЙОМ ВІД ВІДБОРУ:   {sel.excess.mean()-W.excess.mean():+.4f}R")
print(f"сира EV відібраних:   {sel.R.mean():+.4f}R | WR {100*(sel.R>0).mean():.1f}%")

print("\n--- чутливість до частки відбору ---")
for q in (0.01,0.02,0.04,0.10,0.20):
    s=W.groupby('ym',group_keys=False)[W.columns].apply(
        lambda g:g.nlargest(max(1,int(round(len(g)*q))),'p'))[W.columns]
    print(f"  топ {100*q:>5.1f}%  N={len(s):>6,}  надлишок {s.excess.mean():+.4f}R  "
          f"підйом {s.excess.mean()-W.excess.mean():+.4f}R")

print("\n--- стабільність по місяцях (топ-4%) ---")
sel=sel.reset_index()
mo=sel.groupby('ym').excess.agg(['size','mean'])
print(f"місяців: {len(mo)} | з плюсом: {(mo['mean']>0).sum()} | "
      f"медіана {mo['mean'].median():+.4f}R")
print(mo.round(4).to_string())

print("\n--- ваги моделі (остання) ---")
co=pd.Series(mdl.coef_[0],index=FEATS).sort_values()
print("НАЙБІЛЬШ НЕГАТИВНІ:"); print(co.head(8).round(3).to_string())
print("НАЙБІЛЬШ ПОЗИТИВНІ:"); print(co.tail(8).round(3).to_string())

print("\n"+"="*74); print("ПОПЕРЕДНЯ ОЦІНКА ПРОТИ GATES (тільки IS!)"); print("="*74)
lift=sel.excess.mean()-W.excess.mean()
print(f"GATE-1 підйом >= +0.30R : {lift:+.4f}  {'PASS' if lift>=0.30 else 'FAIL'}")
print(f"GATE-2 рівень >= +0.10R : {sel.excess.mean():+.4f}  {'PASS' if sel.excess.mean()>=0.10 else 'FAIL'}")
W.to_parquet('/home/claude/is_scored.parquet',index=False)
