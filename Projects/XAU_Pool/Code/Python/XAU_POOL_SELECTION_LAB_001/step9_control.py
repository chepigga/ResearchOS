"""
XAU_POOL_SELECTION_LAB_001 | КРОК 9 — CONTROL 2026
2024-04-01 ... 2025-01-31.  ЧИТАЄТЬСЯ ОДИН РАЗ.

Нічого не змінюється: ті самі 36 фіч, та сама модель LogisticRegression(C=0.5),
та сама частка відбору 4%, той самий walk-forward (навчання на всіх
місяцях < тестового).

OOS-2 і CONTROL не торкаємось.
"""
import pandas as pd, numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

P=pd.read_parquet('/home/claude/pool_excess.parquet')
MECHS=[c for c in P.columns if c.startswith('f_')]
TREND=['f_T_PRICECHANNEL','f_T_LINREG','f_T_MACD_MOM','f_T_PSAR','f_T_ALLIGATOR',
       'f_T_ENVELOPE','f_C_PIVOT','f_T_SMA_STOCH']
CT=['f_C_BOLLINGER','f_C_WILLIAMS']; PAT=['f_P_PINBAR','f_P_3SOLDIER','f_P_TURNAROUND']
VOL=['f_V_ATR_EXP']
P['n_trend']=P[TREND].sum(axis=1); P['n_ct']=P[CT].sum(axis=1)
P['n_pat']=P[PAT].sum(axis=1); P['n_vol']=P[VOL].sum(axis=1)
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
P['y']=(P.excess>0).astype(int)

OOS1=[m for m in sorted(P.ym.unique()) if '2026-01'<=m<='2026-07']
print("="*74); print("КРОК 9 — CONTROL 2026"); print("="*74)
print(f"місяців: {len(OOS1)} | {OOS1[0]} ... {OOS1[-1]}")

P['p']=np.nan
for m in OOS1:
    tr=P[P.ym<m]; te=P.index[P.ym==m]
    if len(tr)<3000 or len(te)<50: continue
    sc=StandardScaler().fit(tr[FEATS])
    mdl=LogisticRegression(C=0.5,max_iter=3000).fit(sc.transform(tr[FEATS]),tr.y)
    P.loc[te,'p']=mdl.predict_proba(sc.transform(P.loc[te,FEATS]))[:,1]

W=P[P.p.notna()].copy()
print(f"кандидатів OOS-1: {len(W):,}")
print(f"надлишок пулу OOS-1: {W.excess.mean():+.4f}R")

sel=W.groupby('ym',group_keys=False)[W.columns].apply(
    lambda g:g.nlargest(max(1,int(round(len(g)*0.04))),'p')).reset_index(drop=True)
lift=sel.excess.mean()-W.excess.mean()

print("\n"+"="*74); print("РЕЗУЛЬТАТ OOS-1"); print("="*74)
print(f"відібрано:            {len(sel):,}")
print(f"надлишок відібраних:  {sel.excess.mean():+.4f}R")
print(f"надлишок пулу:        {W.excess.mean():+.4f}R")
print(f"ПІДЙОМ:               {lift:+.4f}R")
print(f"сира EV відібраних:   {sel.R.mean():+.4f}R | WR {100*(sel.R>0).mean():.1f}%")

print("\n--- по місяцях ---")
mo=sel.groupby('ym').excess.agg(['size','mean'])
print(mo.round(4).to_string())
print(f"місяців {len(mo)} | з плюсом {(mo['mean']>0).sum()} | медіана {mo['mean'].median():+.4f}")

print("\n--- монотонність за часткою ---")
for q in (0.01,0.02,0.04,0.10,0.20):
    s=W.groupby('ym',group_keys=False)[W.columns].apply(
        lambda g:g.nlargest(max(1,int(round(len(g)*q))),'p'))
    print(f"  топ {100*q:>5.1f}%  N={len(s):>6,}  надлишок {s.excess.mean():+.4f}R")

print("\n"+"="*74); print("GATES НА OOS-1"); print("="*74)
g1='PASS' if lift>=0.30 else 'FAIL'
g2='PASS' if sel.excess.mean()>=0.10 else 'FAIL'
g5='PASS' if len(sel)>=300 else 'FAIL'
print(f"GATE-1  підйом >= +0.30R : {lift:+.4f}   {g1}")
print(f"GATE-2  рівень >= +0.10R : {sel.excess.mean():+.4f}   {g2}")
print(f"GATE-5  N >= 300         : {len(sel):,}   {g5}")
print(f"\nдля порівняння IS: підйом +0.3591R, рівень +0.3294R")
W.to_parquet('/home/claude/control_scored.parquet',index=False)
